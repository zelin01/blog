from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pathlib import Path
import shutil
import json
from database import get_db_conn
from auth import get_current_user
from utils import validate_image, generate_unique_filename, clear_post_cache
from config import UPLOAD_DIR, redis_client

router = APIRouter(tags=["attachments"])

# 上传图片
@router.post("/post/{post_id}/upload")
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
@router.get("/post/{post_id}/attachments")
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
@router.delete("/attachments/{attachment_id}")
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
@router.get("/attachments/{attachment_id}")
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