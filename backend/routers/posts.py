from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pathlib import Path
import json
from database import get_db_conn
from auth import get_current_user
from schemas import Post
from utils import clear_post_cache
from config import redis_client

router = APIRouter(prefix="/posts", tags=["posts"])


# 文章相关接口
@router.post("/posts")
def create_post(post: Post, db=Depends(get_db_conn), current_user=Depends(get_current_user)):
    conn, cursor = db

    if post.category_id is not None:
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
@router.get("/posts")
def get_posts(category_id: Optional[int] = None,db=Depends(get_db_conn)):
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
@router.get("/posts/{post_id}")
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
@router.put("/posts/{post_id}")
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

    if post.category_id is not None:
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
@router.delete("/posts/{post_id}")
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
