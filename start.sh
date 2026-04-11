#!/bin/bash
# 启动脚本 - MVP Ingress
# 需要先安装依赖: pip install -r requirements.txt

set -e

echo "=== Feishu RPA Commerce Agent - MVP Ingress ==="

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "Error: .env 文件不存在，请先复制 .env.example 并配置"
    exit 1
fi

# 检查 Python 环境
echo "检查 Python 版本..."
python3 --version

# 检查依赖
echo "检查依赖包..."
python3 -c "import fastapi, celery, sqlalchemy, lark_oapi" 2>/dev/null || {
    echo "Error: 依赖包未安装，请运行: pip install -r requirements.txt"
    exit 1
}

echo ""
echo "=== 启动说明 ==="
echo ""
echo "请按顺序启动以下服务 (每个命令需要开一个新的终端):"
echo ""
echo "1. FastAPI 服务:"
echo "   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "2. Celery Worker:"
echo "   celery -A app.workers.celery_app worker --loglevel=info"
echo ""
echo "3. 飞书长连接监听器:"
echo "   python -m app.services.feishu.runner"
echo ""
echo "健康检查: http://localhost:8000/api/v1/health"