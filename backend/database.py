from datetime import datetime
from typing import List, Dict, Optional
from .models import BlogPost


class BlogDatabase:
    def __init__(self):
        self.posts = []
        self.post_id_counter = 1
        self.init_sample_data()

    def init_sample_data(self):
        """初始化示例数据"""
        if not self.posts:
            sample_posts = [
                BlogPost(
                    id=1,
                    title="欢迎来到我的博客",
                    content="这是我的第一篇博客文章，欢迎阅读！",
                    author="管理员",
                    created_at="2024-01-01 10:00:00",
                    updated_at="2024-01-01 10:00:00"
                ),
                BlogPost(
                    id=2,
                    title="NiceGUI 3.X 新特性介绍",
                    content="NiceGUI 3.X 带来了很多令人兴奋的新特性...",
                    author="技术达人",
                    created_at="2024-01-02 14:30:00",
                    updated_at="2024-01-02 14:30:00"
                ),
                BlogPost(
                    id=3,
                    title="Python Web开发趋势",
                    content="近年来，Python在Web开发领域发展迅速...",
                    author="Python爱好者",
                    created_at="2024-01-03 09:15:00",
                    updated_at="2024-01-03 09:15:00"
                )
            ]

            for post in sample_posts:
                self.posts.append(post.dict())
            self.post_id_counter = 4

    def get_all_posts(self) -> List[Dict]:
        """获取所有文章"""
        return self.posts

    def get_post(self, post_id: int) -> Optional[Dict]:
        """根据ID获取文章"""
        for post in self.posts:
            if post["id"] == post_id:
                return post
        return None

    def create_post(self, post_data: Dict) -> Dict:
        """创建新文章"""
        post = BlogPost(**post_data)
        post.id = self.post_id_counter
        post.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        post.updated_at = post.created_at

        post_dict = post.dict()
        self.posts.append(post_dict)
        self.post_id_counter += 1
        return post_dict

    def update_post(self, post_id: int, post_data: Dict) -> Optional[Dict]:
        """更新文章"""
        for i, existing_post in enumerate(self.posts):
            if existing_post["id"] == post_id:
                post_data["id"] = post_id
                post_data["created_at"] = existing_post["created_at"]
                post_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                self.posts[i] = post_data
                return post_data
        return None

    def delete_post(self, post_id: int) -> bool:
        """删除文章"""
        for i, post in enumerate(self.posts):
            if post["id"] == post_id:
                self.posts.pop(i)
                return True
        return False
