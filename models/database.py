"""数据库连接管理"""
import sqlite3
import os
from config import DATABASE_PATH, BASE_DIR

_conn = None


def get_db():
    """获取数据库连接（单例）"""
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        _conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
    return _conn


def init_db():
    """初始化数据库表结构"""
    db = get_db()
    schema_path = os.path.join(BASE_DIR, "models", "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        db.executescript(f.read())
    db.commit()
    print("✅ 数据库初始化完成")


def query(sql, params=(), one=False):
    """执行查询"""
    db = get_db()
    cur = db.execute(sql, params)
    if one:
        return cur.fetchone()
    return cur.fetchall()


def execute(sql, params=()):
    """执行写操作"""
    db = get_db()
    cur = db.execute(sql, params)
    db.commit()
    return cur.lastrowid


def executemany(sql, params_list):
    """批量执行写操作"""
    db = get_db()
    cur = db.executemany(sql, params_list)
    db.commit()
    return cur.rowcount
