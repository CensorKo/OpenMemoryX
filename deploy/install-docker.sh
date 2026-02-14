#!/bin/bash
# MemoryX Docker 服务器部署脚本
# 在 31.65 和 31.66 上分别执行

set -e

echo "=========================================="
echo "MemoryX Docker 服务器部署"
echo "=========================================="

SERVER_IP=$(hostname -I | awk '{print $1}')
SERVER_TYPE=${1:-"alpha"}

echo "服务器 IP: $SERVER_IP"
echo "部署类型: $SERVER_TYPE"
echo ""

# ==================== 1. 安装 Docker ====================
echo "[1/6] 安装 Docker..."

if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER 2>/dev/null || true
    echo "✅ Docker 已安装"
else
    echo "✅ Docker 已存在: $(docker --version)"
fi

# 创建目录
sudo mkdir -p /data/memoryx/{static,backups,deploy/scripts}
sudo mkdir -p /var/log/memoryx
sudo mkdir -p /etc/memoryx

echo "✅ 目录结构创建完成"
echo ""

# ==================== 2. 部署代码 ====================
echo "[2/6] 部署代码和脚本..."

if [ ! -d "/data/memoryx/repo" ]; then
    sudo git clone https://github.com/t0ken-ai/MemoryX.git /data/memoryx/repo
    echo "✅ 代码克隆完成"
else
    cd /data/memoryx/repo
    sudo git pull origin main
    echo "✅ 代码更新完成"
fi

# 复制部署脚本
sudo cp /data/memoryx/repo/deploy/scripts/deploy-docker.sh /data/memoryx/deploy/scripts/
sudo cp /data/memoryx/repo/deploy/scripts/webhook_server.py /data/memoryx/deploy/scripts/
sudo chmod +x /data/memoryx/deploy/scripts/*.sh

echo "✅ 部署脚本准备完成"
echo ""

# ==================== 3. Nginx ====================
echo "[3/6] 配置 Nginx..."

if [ ! -f "/etc/nginx/sites-available/memoryx" ]; then
    sudo cp /data/memoryx/repo/deploy/nginx/memoryx-internal.conf /etc/nginx/sites-available/memoryx
    sudo ln -sf /etc/nginx/sites-available/memoryx /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
    echo "✅ Nginx 配置已添加"
else
    echo "✅ Nginx 配置已存在"
fi

sudo nginx -t && echo "✅ Nginx 配置检查通过"
echo ""

# ==================== 4. 环境变量 ====================
echo "[4/6] 配置环境变量..."

if [ ! -f "/etc/memoryx/api.env" ]; then
    sudo tee /etc/memoryx/api.env << EOF
DATABASE_URL=sqlite:///./memoryx.db
SECRET_KEY=$(openssl rand -hex 32)
REDIS_URL=redis://localhost:6379/0
OLLAMA_HOST=http://192.168.31.65:11434
EOF
    echo "✅ 环境变量文件已创建"
    echo "⚠️  请编辑 /etc/memoryx/api.env 配置正确的数据库"
else
    echo "✅ 环境变量文件已存在"
fi

echo ""
echo "⚠️  请配置 webhook token:"
echo "   sudo vim /etc/systemd/system/memoryx-webhook.service"
echo "   修改: Environment=\"DEPLOY_TOKEN=your-secret-token\""
echo ""

# ==================== 5. Systemd ====================
echo "[5/6] 配置 Systemd 服务..."

sudo cp /data/memoryx/repo/deploy/systemd/memoryx-api-docker.service /etc/systemd/system/memoryx-api.service
sudo cp /data/memoryx/repo/deploy/systemd/memoryx-webhook.service /etc/systemd/system/

echo "✅ Systemd 服务配置完成"
echo ""

# ==================== 6. 开机启动 ====================
echo "[6/6] 配置开机启动..."

sudo systemctl daemon-reload
sudo systemctl enable memoryx-api memoryx-webhook nginx

echo "✅ 开机启动配置完成"
echo ""

# ==================== 完成 ====================
echo "=========================================="
echo "📋 部署清单完成 ($SERVER_TYPE)"
echo "=========================================="
echo ""
echo "服务器: $SERVER_IP"
echo ""
echo "待办事项:"
echo "  [ ] 配置 webhook token"
echo "      sudo vim /etc/systemd/system/memoryx-webhook.service"
echo "      修改: Environment=\"DEPLOY_TOKEN=your-secret-token\""
echo ""
echo "  [ ] 编辑数据库配置"
echo "      sudo vim /etc/memoryx/api.env"
echo ""
echo "  [ ] 准备静态文件"
echo "      sudo cp -r /data/memoryx/repo/static/* /data/memoryx/static/"
echo ""
echo "  [ ] 启动服务"
echo "      sudo systemctl start memoryx-webhook memoryx-api"
echo ""
echo "  [ ] 验证部署"
echo "      curl http://localhost:8000/health"
echo "      curl http://localhost:9000/"
echo ""
echo "GitHub Secrets 配置:"
echo "  DEPLOY_WEBHOOK_URL: https://t0ken.ai/deploy"
echo "  DEPLOY_TOKEN: <与服务器配置一致>"
echo ""
echo "Docker 镜像: ghcr.io/t0ken-ai/memoryx-api:latest"
echo ""
