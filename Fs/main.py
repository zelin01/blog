from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Generator
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

def get_db_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()

class Post(BaseModel):
    title: str
    content: str

@app.post("/posts")
def create_post(post: Post, conn = Depends(get_db_conn)):
    cursor = conn.execute(
        "INSERT INTO posts (title, content) VALUES (?, ?)",
        (post.title, post.content)
    )
    conn.commit()
    post_id = cursor.lastrowid
    return {"id": post_id, "title": post.title, "content": post.content}

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
def put_post(post_id: int, post: Post, conn = Depends(get_db_conn)):
    cursor = conn.execute("UPDATE posts SET title = ?, content = ? WHERE id = ?", (post.title, post.content, post_id))
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"massage": "updated", "id": post_id}

@app.delete("/posts/{post_id}")
def delete_post(post_id: int, conn = Depends(get_db_conn)):
    cursor = conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"message": "deleted", "id": post_id}