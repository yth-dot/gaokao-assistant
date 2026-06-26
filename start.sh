#!/bin/bash
export DATABASE_PATH=/app/data/gaokao.db
echo "🚀 启动"
cd /app && python3 app.py
