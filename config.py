"""配置文件"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# DeepSeek API — 从环境变量读取，不要写死在代码里
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL_FAST = os.environ.get("DEEPSEEK_MODEL_FAST", "deepseek-v4-flash")
DEEPSEEK_MODEL_PRO = os.environ.get("DEEPSEEK_MODEL_PRO", "deepseek-v4-pro")

# 数据库 — 优先使用环境变量（Railway 持久卷）
DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "data", "gaokao.db"))

# Flask
SECRET_KEY = "gaokao-assistant-secret-key-change-in-production"
DEBUG = True
