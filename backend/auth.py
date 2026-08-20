from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import jwt, JWTError
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from database import get_db_conn

# OAuth2 密码模式
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

#JWT Token 工具函数
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

#用户认证依赖
def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db_conn)):
    #认证失败时统一相应
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

    #查询数据库验证用户是否存在
    conn, cursor = db
    cursor.execute("SELECT id, username FROM users WHERE username = %s", (username,))
    row = cursor.fetchone()
    if row is None:
        raise credentials_exception
    return row
