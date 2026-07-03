import bcrypt
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Generator
from passlib.context import CryptContext
from jose import jwt, JWTError
import sqlite3
import os
from typing import Generator, Optional
from datetime import datetime, timedelta

app = FastAPI()

DB_FILE = os.path.join(os.path.dirname(__file__), "blog.db")
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()
    print("数据库初始化完成")

init_db()
def get_db_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), hashed_password.encode('utf-8')
    )
def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        password.encode('utf-8'), bcrypt.gensalt()
    ).decode('utf-8')
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
def get_current_user(token: str = Depends(oauth2_scheme), conn: sqlite3.Connection = Depends(get_db_conn)):
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
    row = conn.execute(
        "SELECT id, username FROM users WHERE username = ?",(username,)
    ).fetchone()
    if row is None:
        raise credentials_exception
    return dict(row)

class Post(BaseModel):
    title: str
    content: str
class UserRegister(BaseModel):
    username: str
    password: str
class Token(BaseModel):
    access_token: str
    token_type: str

@app.post("/register")
def register(user: UserRegister, conn = Depends(get_db_conn)):
    existing = conn.execute(
        "SELECT id FROM users WHERE username = ?",(user.username,)
    ).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed = get_password_hash(user.password)
    conn.execute(
        "INSERT INTO users (username, hashed_password) VALUES (?, ?)",
        (user.username, hashed)
    )
    conn.commit()
    return {"message": "User registered successfully", "username": user.username}

@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), conn = Depends(get_db_conn)):
    row = conn.execute(
        "SELECT username, hashed_password FROM users WHERE username = ?",(form_data.username,)
    ).fetchone()
    if not row or not verify_password(form_data.password, row["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data = {"sub": row["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
@app.post("/posts")
def create_post(post: Post, conn = Depends(get_db_conn), current_user = Depends(get_current_user)):
    cursor = conn.execute(
        "INSERT INTO posts (title, content) VALUES (?, ?)",
        (post.title, post.content)
    )
    conn.commit()
    post_id = cursor.lastrowid
    return {"id": post_id, "title": post.title, "content": post.content, "author": current_user["username"]}

@app.get("/posts")
def get_post(conn = Depends(get_db_conn)):
    rows = conn.execute("SELECT * FROM posts").fetchall()
    return [dict(row) for row in rows]
@app.get("/posts/{post_id}")
def get_post(post_id: int,conn = Depends(get_db_conn)):
    row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return dict(row)

@app.put("/posts/{post_id}")
def put_post(post_id: int, post: Post, conn = Depends(get_db_conn),  current_user = Depends(get_current_user)):
    cursor = conn.execute("UPDATE posts SET title = ?, content = ? WHERE id = ?", (post.title, post.content, post_id))
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"massage": "updated", "id": post_id, "by" : current_user["username"]}

@app.delete("/posts/{post_id}")
def delete_post(post_id: int, conn = Depends(get_db_conn),  current_user = Depends(get_current_user)):
    cursor = conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"message": "deleted", "id": post_id, "by" : current_user["username"]}