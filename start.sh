#!/bin/bash
export DATABASE_PATH=/app/data/gaokao.db
export FLASK_ENV=production
echo "🚀 启动"
python3 app.py
