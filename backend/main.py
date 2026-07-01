from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import uvicorn

from .models import BlogPost
from .database import BlogDatabase

# 创建 FastAPI 应用
app = FastAPI(
    title="博客系统 API",
    description="一个简单的博客系统后端",
    version="1.0.0"
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化数据库
db = BlogDatabase()

# API 路由
@app.get("/")
async def root():
    return {
        "message": "欢迎访问博客系统 API",
        "docs": "/docs",
        "endpoints": {
            "获取所有文章": "GET /api/posts",
            "获取单篇文章": "GET /api/posts/{id}",
            "创建文章": "POST /api/posts",
            "更新文章": "PUT /api/posts/{id}",
            "删除文章": "DELETE /api/posts/{id}"
        }
    }

@app.get("/api/posts", response_model=List[BlogPost])
async def get_all_posts():
    """获取所有博客文章"""
    return db.get_all_posts()

@app.get("/api/posts/{post_id}", response_model=BlogPost)
async def get_post(post_id: int):
    """根据ID获取博客文章"""
    post = db.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="文章不存在")
    return post

@app.post("/api/posts", response_model=BlogPost)
async def create_post(post: BlogPost):
    """创建新博客文章"""
    return db.create_post(post.dict())

@app.put("/api/posts/{post_id}", response_model=BlogPost)
async def update_post(post_id: int, post: BlogPost):
    """更新博客文章"""
    updated = db.update_post(post_id, post.dict())
    if not updated:
        raise HTTPException(status_code=404, detail="文章不存在")
    return updated

@app.delete("/api/posts/{post_id}")
async def delete_post(post_id: int):
    """删除博客文章"""
    if db.delete_post(post_id):
        return {"message": "文章删除成功"}
    raise HTTPException(status_code=404, detail="文章不存在")

# 健康检查端点
@app.get("/health")
async def health_check():
    return {"status": "healthy", "posts_count": len(db.get_all_posts())}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
