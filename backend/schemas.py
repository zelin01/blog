from typing import Optional
from pydantic import BaseModel

#pydantic 数据模型
#用于请求参数校验和响应列化
class Post(BaseModel):
    title: str
    content: str
    category_id: Optional[int] = None


class UserRegister(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
