from fastapi import APIRouter, Depends
from database import get_db_conn

router = APIRouter(prefix="/categories", tags=["categories"])

# 获取文章分类标签
@router.get("/categories")
def get_categories(db = Depends(get_db_conn)):
    conn, cursor = db
    cursor.execute("SELECT id, name FROM categories ORDER BY id ")

    return cursor.fetchall()

@router.post("/files/", deprecated=True)
async def creat_file(file: Annotated[bytes | None, File()] = None):
    if not file:
        return {"message": "No file set"}

    return {"file_size": len(file)}


@router.post("/uploaadfile/", deprecated=True)
async def creat_upload_file(file: UploadFile | None = None):
    if not file:
        return {"message": "No file set"}

    return {"filename": file.filename}