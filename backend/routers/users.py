from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from database import get_db_conn
from auth import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from schemas import UserRegister, Token

router = APIRouter(tags=["users"])
@router.post("/register")
def register(user: UserRegister, db=Depends(get_db_conn)):
    conn, cursor = db
    # 检查用户是否已存在
    cursor.execute("SELECT id FROM users WHERE username = %s", (user.username,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Username already registered")

    # 密码哈希后存入数据库
    hashed = get_password_hash(user.password)
    cursor.execute(
        "INSERT INTO users (username, hashed_password) VALUES (%s, %s)",
        (user.username, hashed)
    )
    conn.commit()
    return {"message": "User registered successfully", "username": user.username}

# 用户登录接口
@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db_conn)):
    conn, cursor = db

    #查询用户
    cursor.execute(
        "SELECT username, hashed_password FROM users WHERE username = %s",
        (form_data.username,)
    )
    row = cursor.fetchone()

    #验证用户和密码
    if not row or not verify_password(form_data.password, row["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    # 生成 JWT Token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": row["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
