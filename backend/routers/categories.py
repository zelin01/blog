from fastapi import APIRouter, Depends
from database import get_db_conn

router = APIRouter(prefix="/categories", tags=["categories"])

# 获取文章分类标签
@router.get("/categories")
def get_categories(db = Depends(get_db_conn)):
    conn, cursor = db
    cursor.execute("SELECT id, name FROM categories ORDER BY id ")

    return cursor.fetchall()
