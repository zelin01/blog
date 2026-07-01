from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
import os

app = FastAPI()

DB_FILE = os.path.join(os.path.dirname(__file__), "blog.db")

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
    conn.commit()
    conn.close()
    print("数据库初始化完成")

init_db()

class Post(BaseModel):
    title: str
    content: str

@app.post("/posts")
def create_post(post: Post):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO posts (title, content) VALUES (?, ?)",
        (post.title, post.content)
    )
    conn.commit()
    post_id = cursor.lastrowid
    conn.close()
    return {"id": post_id, "title": post.title, "content": post.content}

@app.get("/posts")
def get_posts():
    conn = get_db()
    rows = conn.execute("SELECT * FROM posts").fetchall()
    conn.close()
    return [dict(row) for row in rows]