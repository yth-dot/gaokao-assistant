#!/bin/bash
set -e
export DATABASE_PATH=/app/data/gaokao.db
export FLASK_ENV=production
echo "🚀 启动服务 (端口: ${PORT:-5000})"
exec gunicorn app:app -b 0.0.0.0:${PORT:-5000} -w 2 --timeout 120
