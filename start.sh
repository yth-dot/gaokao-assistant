#!/bin/bash
set -e

echo "📦 准备数据库..."

# Railway 持久卷挂载在 /data，首次启动从镜像复制数据
if [ ! -f /data/gaokao.db ]; then
    echo "  首次启动，复制初始数据..."
    mkdir -p /data
    cp /app/data/gaokao.db /data/gaokao.db 2>/dev/null || true
fi

export DATABASE_PATH=/data/gaokao.db
echo "✅ 数据库路径: $DATABASE_PATH"

# 导入 gunicorn
pip install gunicorn -q 2>/dev/null || true

echo "🚀 启动服务 (端口: ${PORT:-5000})"
exec gunicorn app:app -b 0.0.0.0:${PORT:-5000} -w 2 --timeout 120 --access-logfile -
