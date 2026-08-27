import os
from pathlib import Path
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
redis_client = redis.Redis(
   host=REDIS_HOST,
   port=REDIS_PORT,
   db=0,
   decode_responses=True
)

# 创建上传目录
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}  # 允许上传文件格式
MAX_FILE_SIZE = 5 * 1024 * 1024  # 最大文件大小 5MB

# JWT认证配置
SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-only")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE", "30"))

# 数据库配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "bloguser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "060427")
DB_NAME = os.getenv("DB_NAME", "blog_db")

