import mysql.connector
from mysql.connector import pooling
from contextlib import contextmanager
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

# MySQL数据库连接池
db_pool = pooling.MySQLConnectionPool(
    pool_name="blog_pool",
    pool_size=5,
    pool_reset_session=True,
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME,
    charset='utf8mb4',
    collation='utf8mb4_unicode_ci'
)

# contextmanager装饰器用于创建数据库连接上下文管理器
@contextmanager
def get_db():
    conn = db_pool.get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        yield conn, cursor
    finally:
        cursor.close()
        conn.close()

def get_db_conn():
    conn = db_pool.get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        yield conn, cursor
    finally:
        cursor.close()
        conn.close()

# 创建数据库函数
def create_database_if_not_exists():
    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor()
    #创建数据库，设置字符集
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    conn.commit()
    cursor.close()
    conn.close()

def init_db():
    create_database_if_not_exists()
    with get_db() as (conn, cursor): # 进入with块，获取数据库连接和游标
        #创建用户表
        cursor.execute("""
                        CREATE TABLE IF NOT EXISTS users
                       (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR (255) UNIQUE NOT NULL,
                        hashed_password VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                       """)
        #创建文章表
        cursor.execute("""
                        CREATE TABLE IF NOT EXISTS posts
                       (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        title VARCHAR (255) NOT NULL,
                        content TEXT NOT NULL,
                        user_id INT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE) 
                        ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                       """)
        cursor.execute(""" 
                        CREATE TABLE IF NOT EXISTS attachments (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        post_id INT NOT NULL,
                        user_id INT NOT NULL,
                        original_name VARCHAR (255) NOT NULL,
                        stored_name VARCHAR (255) NOT NULL UNIQUE,
                        file_path VARCHAR (500) NOT NULL,
                        file_size INT NOT NULL,
                        content_type VARCHAR (100) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        INDEX idx_post_id (post_id))
                        ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                        """)
        cursor.execute("""
                        CREATE TABLE IF NOT EXISTS categories (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR (50) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE KEY uk_name (name))
                        ENGINE = innoDB DEFAULT CHARSET=utf8mb4
                        """)
        cursor.execute("""
                       SELECT COUNT(*) as cnt
                       FROM information_schema.COLUMNS
                       WHERE TABLE_SCHEMA = %s
                       AND TABLE_NAME = 'posts'
                       AND COLUMN_NAME = 'category_id'
                       """, (DB_NAME,))
        if cursor.fetchone()["cnt"] == 0:
            cursor.execute("""
                           ALTER TABLE posts
                           ADD COLUMN category_id INT DEFAULT NULL,
                           ADD CONSTRAINT fk_post_category
                           FOREIGN KEY (category_id) REFERENCES categories(id)
                           ON DELETE SET NULL
                           """)
        cursor.execute("""
                        INSERT IGNORE INTO categories (name)
                        VALUES ('技术'), ('生活'), ('随笔')
                       """)
        conn.commit()
    print("数据库初始化完成")
