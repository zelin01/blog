import os
import uuid
import shutil
from asyncio import wait
import bcrypt
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import FileResponse
from multipart import file_path
from pydantic import BaseModel
from jose import jwt, JWTError
from typing import Optional, Annotated
from datetime import datetime, timedelta
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import mysql.connector
from mysql.connector import pooling, cursor
from contextlib import contextmanager
import redis
import json
from pydantic_core.core_schema import field_after_validator_function

#创建FastAPI应用
app = FastAPI()

#添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#引入REDIS缓存数据库
redis_client = redis.Redis(
    host = 'localhost',
    port = 6379,
    db = 0,
    decode_responses = True
)

 #创建上传目录
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# 引入静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"} # 允许上传文件格式
MAX_FILE_SIZE = 5 * 1024 * 1024 # 最大文件大小 5MB

# 数据库配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "bloguser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "060427")
DB_NAME = os.getenv("DB_NAME", "blog_db")

# JWT认证配置
SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-only")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE", "30"))

# OAuth2 密码模式
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# MySQL数据库连接池
db_pool = pooling.MySQLConnectionPool(
    pool_name="blog_pool",
    pool_size=5,
    pool_reset_session=True,
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME,
    charset='utf8mb4',
    collation='utf8mb4_unicode_ci'
)

# 创建数据库函数
def create_database_if_not_exists():
    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor()
    #创建数据库，设置字符集
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    conn.commit()
    cursor.close()
    conn.close()

# contextmanager装饰器用于创建数据库连接上下文管理器
@contextmanager
def get_db():
    conn = db_pool.get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        yield conn, cursor
    finally:
        cursor.close()
        conn.close()


def init_db():
    create_database_if_not_exists()
    with get_db() as (conn, cursor): # 进入with块，获取数据库连接和游标
        #创建用户表
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS users
                       (
                           id INT AUTO_INCREMENT PRIMARY KEY,
                           username VARCHAR (255) UNIQUE NOT NULL,
                           hashed_password VARCHAR(255) NOT NULL,
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                       """)
        #创建文章表
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS posts
                       (
                           id INT AUTO_INCREMENT PRIMARY KEY,
                           title VARCHAR (255) NOT NULL,
                           content TEXT NOT NULL,
                           user_id INT NOT NULL,
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                           FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE) 
                           ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                       """)
        cursor.execute(""" 
                        CREATE TABLE IF NOT EXISTS attachments (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        post_id INT NOT NULL,
                        user_id INT NOT NULL,
                        original_name VARCHAR (255) NOT NULL,
                        stored_name VARCHAR (255) NOT NULL UNIQUE,
                        file_path VARCHAR (500) NOT NULL,
                        file_size INT NOT NULL,
                        content_type VARCHAR (100) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        INDEX idx_post_id (post_id))
                        ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                        """)
        cursor.execute("""
                    CREATE TABLE IF NOT EXISTS categories (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR (50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_name (name))
                    ENGINE = innoDB DEFAULT CHARSET=utf8mb4
        """)
        cursor.execute("""
                       SELECT COUNT(*) as cnt
                       FROM information_schema.COLUMNS
                       WHERE TABLE_SCHEMA = %s
                       AND TABLE_NAME = 'posts'
                       AND COLUMN_NAME = 'category_id'
                       """, (DB_NAME,))
        if cursor.fetchone()["cnt"] == 0:
            cursor.execute("""
                           ALTER TABLE posts
                           ADD COLUMN category_id INT DEFAULT NULL,
                           ADD CONSTRAINT fk_post_category
                           FOREIGN KEY (category_id) REFERENCES categories(id)
                           ON DELETE SET NULL
                           """)
        cursor.execute("""
                       INSERT IGNORE INTO categories (name)
                       VALUES ('技术'), ('生活'), ('随笔')
                       """)
        conn.commit()
    print("数据库初始化完成")

#应用启动时自动初始化数据库
init_db()

#
def get_db_conn():
    conn = db_pool.get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        yield conn, cursor
    finally:
        cursor.close()
        conn.close()

#密码处理工具函数
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

#JWT Token 工具函数
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

#用户认证依赖
def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db_conn)):
    #认证失败时统一相应
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    #查询数据库验证用户是否存在
    conn, cursor = db
    cursor.execute("SELECT id, username FROM users WHERE username = %s", (username,))
    row = cursor.fetchone()
    if row is None:
        raise credentials_exception
    return row

# 图片检查函数
def validate_image(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid image type")
    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too big")
    file.file.seek(0)
    return content

# 创建图片唯一名称
def generate_unique_filename(original_name: str) -> None:
    ext = Path(original_name).suffix
    return f"{uuid.uuid4().hex}{ext}"

# 清理redis缓存
def clear_post_cache(post_id: int):
    redis_client.delete("posts/{post_id}")
    redis_client.delete("posts:list")
    redis_client.delete(f"attachments:post:{post_id}")

#pydantic 数据模型
#用于请求参数校验和响应列化
class Post(BaseModel):
    title: str
    content: str
    category_id: Optional[int] = None


class UserRegister(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str

#用户注册接口
@app.post("/register")
def register(user: UserRegister, db=Depends(get_db_conn)):
    conn, cursor = db
    # 检查用户是否已存在
    cursor.execute("SELECT id FROM users WHERE username = %s", (user.username,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Username already registered")

    # 密码哈希后存入数据库
    hashed = get_password_hash(user.password)
    cursor.execute(
        "INSERT INTO users (username, hashed_password) VALUES (%s, %s)",
        (user.username, hashed)
    )
    conn.commit()
    return {"message": "User registered successfully", "username": user.username}

# 用户登录接口
@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db_conn)):
    conn, cursor = db

    #查询用户
    cursor.execute(
        "SELECT username, hashed_password FROM users WHERE username = %s",
        (form_data.username,)
    )
    row = cursor.fetchone()

    #验证用户和密码
    if not row or not verify_password(form_data.password, row["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    # 生成 JWT Token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": row["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# 文章相关接口
@app.post("/posts")
def create_post(post: Post, db=Depends(get_db_conn), current_user=Depends(get_current_user)):
    conn, cursor = db

    if post.category_id:
        cursor.execute("SELECT id FROM categories WHERE id = %s", (post.category_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=400, detail="Category does not exist")

    #插入文章， user_id 为当前登录用户
    cursor.execute(
        "INSERT INTO posts (title, content, user_id, category_id) VALUES (%s, %s, %s, %s)",
        (post.title, post.content, current_user["id"], post.category_id)
    )
    conn.commit()
    post_id = cursor.lastrowid
    # 清除文章列表缓存（因为新增了文章）
    redis_client.delete("posts:list")
    return {"message": "created", "id": post_id}

# 拉取文章列表，支持按分类过滤
@app.get("/posts")
def get_posts(category_id: optional[int] = None,db=Depends(get_db_conn)):
    cache_key = f"posts:list:cat:{category_id}" if category_id else "posts:list"
    # 尝试从redis 缓存获取
    cached = redis_client.get("posts:list")
    if cached:
        return json.loads(cached)
    conn, cursor = db

    #缓存未命中，查询数据库
    if category_id:
        cursor.execute("""
                       SELECT p.*, u.username as author, c.name as category_name
                       FROM posts p
                       JOIN users u ON p.user_id = u.id
                       LEFT JOIN categories c ON p.category_id = c.id
                       WHERE p.category_id = %s
                       ORDER BY p.created_at DESC
                       """, (category_id,))
    else:
        cursor.execute("""
                       SELECT p.*, u.username as author, c.name as category_name
                       FROM posts p
                       JOIN users u ON p.user_id = u.id
                       LEFT JOIN categories c ON p.category_id = c.id
                       ORDER BY p.created_at DESC
                       """)
    rows = cursor.fetchall()

    #写入 Redis 缓存， 设置5 分钟过期时间
    redis_client.setex("posts:list",300, json.dumps(rows, default=str))
    return rows

#获取单篇文章
@app.get("/posts/{post_id}")
def get_post(post_id: int, db=Depends(get_db_conn)):
    cache_key = f"post:{post_id}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    conn, cursor = db

    cursor.execute("""
                   SELECT p.*, u.username as author, c.name as category_name
                   FROM posts p
                   JOIN users u ON p.user_id = u.id
                   LEFT  JOIN categories c ON p.category_id = c.id
                   WHERE p.id = %s
                   """, (post_id,))
    row = cursor.fetchall()

    if row is None:
        raise HTTPException(status_code=404, detail="Post not found")

    redis_client.setex(cache_key, 600, json.dumps(row, default=str))
    return row


# 更新文章
@app.put("/posts/{post_id}")
def update_post(post_id: int, post: Post, db=Depends(get_db_conn), current_user=Depends(get_current_user)):
    redis_client.delete(f"post:{post_id}")
    redis_client.delete("posts:list")
    conn, cursor = db

    cursor.execute("SELECT user_id, category_id  FROM posts WHERE id = %s", (post_id,))
    row = cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if row["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to edit this post")

    if post.category_id:
        cursor.execute("SELECT id FROM categories WHERE id = %s", (post.category_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=400, detail="Category not found")

    cursor.execute(
        "UPDATE posts SET title = %s, content = %s, category_id = %s WHERE id = %s",
        (post.title, post.content, post.category_id, post_id)
    )
    conn.commit()

    clear_post_cache(post_id)
    redis_client.delete(f"posts:list:cat:{row['category_id']}")
    redis_client.delete(f"posts:list:cat:{post.category_id}")

    return {"message": "updated", "id": post_id}

# 删除文章
@app.delete("/posts/{post_id}")
def delete_post(post_id: int, db=Depends(get_db_conn), current_user=Depends(get_current_user)):
    redis_client.delete(f"post:{post_id}")
    redis_client.delete("posts:list")
    conn, cursor = db

    # 查询文章并验证权限
    cursor.execute("SELECT user_id FROM posts WHERE id = %s", (post_id,))
    row = cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if row["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")

    cursor.execute("SELECT file_path FROM attachments WHERE post_id = %s", (post_id,))
    for att in cursor.fetchall():
        try:
            path = Path(att["file_path"])
            if path.exists():
                path.unlink()
        except Exception:
            pass

    cursor.execute("DELETE FROM posts WHERE id = %s", (post_id,))
    conn.commit()

    clear_post_cache(post_id)
    return {"message": "deleted", "id": post_id}

# 上传图片
@app.post("/post/{post_id}/upload")
async def upload_image(
        post_id: int,
        file: UploadFile = File(..., description="Upload image"),
        db = Depends(get_db_conn),
        current_user=Depends(get_current_user)
        ):
    conn, cursor = db

    cursor.execute(f"SELECT * FROM posts WHERE id = %s", (post_id,))
    post = cursor.fetchone()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if post["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to upload this post")
    validate_image(file)
    stored_name = generate_unique_filename(file.filename)
    file_path = UPLOAD_DIR / stored_name

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    cursor.execute("""
                   INSERT INTO attachments (
                    post_id, user_id, original_name,stored_name, file_path, file_size, content_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s
                    )""",
                   (
                    post_id,
                    current_user["id"],
                    file.filename,
                    stored_name,
                    str(file_path),
                    file_path.stat().st_size,
                    file.content_type
                    ))

    conn.commit()
    attchment_id = cursor.lastrowid

    clear_post_cache(post_id)
    return{
        "message": "Image uploaded successfully",
        "attchment_id": attchment_id,
        "filename": file.filename,
        "url": f"/uploads/{stored_name}",  # 通过静态文件服务访问
        "size": file_path.stat().st_size
    }

# 获取文章的所有附件
@app.get("/post/{post_id}/attachments")
def get_post_attchments(post_id: int, db=Depends(get_db_conn)):
    cache_key = f"attachments:post:{post_id}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    conn, cursor = db
    cursor.execute("""
                   SELECT id, original_name, stored_name, file_size, content_type, created_at
                   FROM attachments
                   WHERE post_id = %s
                   ORDER BY created_at ASC
                   """, (post_id,))
    rows = cursor.fetchall()

    # 拼接完整访问 URL
    for row in rows:
        row["url"] = f"/uploads/{row['stored_name']}"

    redis_client.setex(cache_key, 300, json.dumps(rows, default=str))

    return rows

# 删除上传图片
@app.delete("/attachments/{attachment_id}")
def delete_attachment(
    attachment_id: int,
    db=Depends(get_db_conn),
    current_user=Depends(get_current_user)
):
    """
    删除指定图片
    - 图片上传者或文章作者均可删除
    """
    conn, cursor = db

    # 查询图片信息
    cursor.execute("""
        SELECT a.*, p.user_id as post_owner_id
        FROM attachments a
        JOIN posts p ON a.post_id = p.id
        WHERE a.id = %s
    """, (attachment_id,))
    att = cursor.fetchone()

    if att is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    if att["user_id"] != current_user["id"] and att["post_owner_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this attachment")

    try:
        file_path = Path(att["file_path"])
        if file_path.exists():
            file_path.unlink()  # 删除文件
            print(f"[INFO] Deleted file: {file_path}")
        else:
            print(f"[WARN] File not found, skipping: {file_path}")
    except Exception as e:
        # 文件删不掉不影响数据库操作，记录日志即可
        print(f"[ERROR] Failed to delete file: {e}")

    # 删除数据库记录
    cursor.execute("DELETE FROM attachments WHERE id = %s", (attachment_id,))
    conn.commit()

    # 清理缓存
    clear_post_cache(att["post_id"])

    return {"message": "Attachment deleted", "id": attachment_id}

# 获取图片
@app.get("/attachments/{attachment_id}")
def get_attachment_file(attachment_id: int, db=Depends(get_db_conn)):
    """通过 attachment_id 直接访问原图"""
    conn, cursor = db
    cursor.execute("SELECT file_path, original_name, content_type FROM attachments WHERE id = %s", (attachment_id,))
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Attachment not found")

    return FileResponse(
        path=row["file_path"],
        filename=row["original_name"],
        media_type=row["content_type"]
    )

# 获取文章分类标签
@app.get("/categories")
def get_categories(db = Depends(get_db_conn)):
    conn, cursor = db
    cursor.execute("SELECT id, name FROM categories ORDER BY id ")

    return cursor.fetchall()

@app.post("/files/", deprecated=True)
async def creat_file(file: Annotated[bytes | None, File()] = None):
    if not file:
        return {"message": "No file set"}

    return {"file_size": len(file)}


@app.post("/uploaadfile/", deprecated=True)
async def creat_upload_file(file: UploadFile | None = None):
    if not file:
        return {"message": "No file set"}

    return {"filename": file.filename}