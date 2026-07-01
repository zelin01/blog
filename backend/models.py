from typing import Optional
from pydantic import BaseModel

class BlogPost(BaseModel):
    id: Optional[int] = None
    title: str
    content: str
    author: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
