import os
import bcrypt
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import jwt, JWTError
from typing import Optional
from datetime import datetime, timedelta
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import mysql.connector
from mysql.connector import pooling
from contextlib import contextmanager
import redis
import json

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

#引入静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

#数据库配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "bloguser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "060427")
DB_NAME = os.getenv("DB_NAME", "blog_db")

#JWT认证配置
SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-only")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE", "30"))

#OAuth2 密码模式
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

#MySQL数据库连接池
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
    with get_db() as (conn, cursor):
        #创建用户表
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS users
                       (
                           id INT AUTO_INCREMENT PRIMARY KEY,
                           username VARCHAR (255) UNIQUE NOT NULL,
                           hashed_password VARCHAR(255) NOT NULL,
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                       """)
        # 创建文章表
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS posts
                       (
                           id INT AUTO_INCREMENT PRIMARY KEY,
                           title VARCHAR (255) NOT NULL,
                           content TEXT NOT NULL,
                           user_id INT NOT NULL,
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                           FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                       """)
        conn.commit()
    print("数据库初始化完成")

#应用启动时自动初始化数据库
init_db()

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

#pydantic 数据模型
#用于请求参数校验和响应列化
class Post(BaseModel):
    title: str
    content: str


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

    #插入文章， user_id 为当前登录用户
    cursor.execute(
        "INSERT INTO posts (title, content, user_id) VALUES (%s, %s, %s)",
        (post.title, post.content, current_user["id"])
    )
    conn.commit()
    post_id = cursor.lastrowid

    # 清除文章列表缓存（因为新增了文章）
    redis_client.delete("posts:list")
    return {"message": "created", "id": post_id}

@app.get("/posts")
def get_posts(db=Depends(get_db_conn)):

    # 尝试从redis 缓存获取
    cached = redis_client.get("posts:list")
    if cached:
        return json.loads(cached)
    conn, cursor = db

    #缓存未命中，查询数据库
    cursor.execute("""
                   SELECT p.*, u.username as author
                   FROM posts p
                   JOIN users u ON p.user_id = u.id
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
                   SELECT p.*, u.username as author
                   FROM posts p
                            JOIN users u ON p.user_id = u.id
                   WHERE p.id = %s
                   """, (post_id,))
    row = cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Post not found")
    redis_client.setex(cache_key, 600, json.dumps(rows, default=str))
    return row


# 更新文章
@app.put("/posts/{post_id}")
def update_post(post_id: int, post: Post, db=Depends(get_db_conn), current_user=Depends(get_current_user)):
    conn, cursor = db
    redis_client.delete(f"post:{post_id}")
    redis_client.delete("posts:list")

    cursor.execute("SELECT user_id FROM posts WHERE id = %s", (post_id,))
    row = cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if row["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to edit this post")

    cursor.execute(
        "UPDATE posts SET title = %s, content = %s WHERE id = %s",
        (post.title, post.content, post_id)
    )
    conn.commit()
    return {"message": "updated", "id": post_id}

# 删除文章
@app.delete("/posts/{post_id}")
def delete_post(post_id: int, db=Depends(get_db_conn), current_user=Depends(get_current_user)):
    conn, cursor = db
    redis_client.delete(f"post:{post_id}")
    redis_client.delete("posts:list")

    # 查询文章并验证权限
    cursor.execute("SELECT user_id FROM posts WHERE id = %s", (post_id,))
    row = cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if row["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")

    cursor.execute("DELETE FROM posts WHERE id = %s", (post_id,))
    conn.commit()
    return {"message": "deleted", "id": post_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)