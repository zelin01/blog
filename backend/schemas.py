from typing import Optional
from pydantic import BaseModel
from fastapi import Query

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

class PaginationParams:
    def __init__(
            self,
            skip: int = Query(0, ge = 0, description="跳过的条数"),
            limit: int = Query(10, ge = 1, le = 100, description="每页条数，最大100")
    ):
        self.skip = skip
        self.limit = limit