import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException
from config import ALLOWED_IMAGE_TYPES, MAX_FILE_SIZE, UPLOAD_DIR, redis_client

# 图片检查函数
def validate_image(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid image type")
    content = file.file.read()
    if len(content) > MAX_FILR_SIZE:
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