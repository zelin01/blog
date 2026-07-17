# 个人博客后端
基于 FastAPI + MySQL 的 RESTful API 服务， 支持用户认证和文章 CRUD。
## 技术栈
- **框架**：FastAPI
- **数据库**：MySQL
- **认证**：JWT + bcrypt
- **部署**：uvicorn

## 功能特性
- 用户注册/登录（密码 bcrypt 哈希）
- JWT Token 认证
- 文章增删查改
- 权限控制（只能修改自己的文章）
- 依赖注入管理数据库连接

## 快速开始
~~~bash
# 1.创建虚拟环境
python -m venv venv
source venv/bin/activate

# 2.安装依赖
pip install -r requirements.txt

# 3.运行服务
uvicorn main:app --reload
~~~ 
