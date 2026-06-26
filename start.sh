#!/bin/bash
set -e

echo "📦 准备数据库..."

mkdir -p /app/data

# 如果数据库不存在，从镜像内复制
if [ ! -f /app/data/gaokao.db ]; then
    if [ -f /app/data/gaokao.db ]; then
        echo "  数据库已在镜像内"
    else
        echo "  警告：镜像内无数据库文件"
    fi
fi

# 确保使用的是镜像内的数据库（Render 无持久卷时）
export DATABASE_PATH=/app/data/gaokao.db
echo "✅ 数据库路径: $DATABASE_PATH"

# 验证数据库
python3 -c "
import sqlite3, os
db = os.environ.get('DATABASE_PATH')
conn = sqlite3.connect(db)
c = conn.cursor()
for t in ['schools','majors','provinces']:
    try:
        cnt = c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
        print(f'  {t}: {cnt}条')
    except: print(f'  {t}: 表不存在')
conn.close()
print('✅ 数据库就绪')
"

export FLASK_ENV=production
export PYTHONUNBUFFERED=1

echo "🚀 启动服务 (端口: ${PORT:-5000})"
exec gunicorn app:app -b 0.0.0.0:${PORT:-5000} -w 2 --timeout 120 --access-logfile -
