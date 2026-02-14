#!/bin/bash
# 初始化 MemoryX 服务器（首次部署）
# 用法: ./init-server.sh <IP> <environment>
# 示例: ./init-server.sh 192.168.31.65 production

set -e

SERVER_IP=${1:-"192.168.31.65"}
ENV_TYPE=${2:-"production"}
SSH_USER=${3:-"deploy"}

echo "=========================================="
echo "MemoryX Server Initialization"
echo "=========================================="
echo "Server: $SERVER_IP"
echo "Environment: $ENV_TYPE"
echo "=========================================="
echo ""

# 检查 SSH 连接
echo "[1/8] Testing SSH connection..."
ssh -o ConnectTimeout=5 $SSH_USER@$SERVER_IP "echo 'SSH OK'" || {
    echo "❌ SSH connection failed"
    exit 1
}
echo "✅ SSH connection OK"

# 复制环境变量文件
echo "[2/8] Copying environment file..."
ENV_FILE="environments/${ENV_TYPE}.env"
if [ -f "$ENV_FILE" ]; then
    scp $ENV_FILE $SSH_USER@$SERVER_IP:/tmp/api.env
    ssh $SSH_USER@$SERVER_IP "sudo mkdir -p /etc/memoryx && sudo mv /tmp/api.env /etc/memoryx/api.env"
    echo "✅ Environment file copied"
else
    echo "⚠️  Environment file not found: $ENV_FILE"
    echo "Please create it from template"
fi

# 安装 Docker
echo "[3/8] Installing Docker..."
ssh $SSH_USER@$SERVER_IP '
    if ! command -v docker &>/dev/null; then
        curl -fsSL https://get.docker.com | sh
        sudo usermod -aG docker $USER
        echo "✅ Docker installed"
    else
        echo "✅ Docker already installed"
    fi
'

# 安装 Nginx
echo "[4/8] Installing Nginx..."
ssh $SSH_USER@$SERVER_IP '
    if ! command -v nginx &>/dev/null; then
        sudo apt-get update
        sudo apt-get install -y nginx
        echo "✅ Nginx installed"
    else
        echo "✅ Nginx already installed"
    fi
'

# 创建目录结构
echo "[5/8] Creating directory structure..."
ssh $SSH_USER@$SERVER_IP '
    sudo mkdir -p /data/memoryx/{static,backups,deploy/scripts}
    sudo mkdir -p /var/log/memoryx
    sudo mkdir -p /etc/memoryx
    echo "✅ Directories created"
'

# 克隆代码仓库
echo "[6/8] Cloning repository..."
ssh $SSH_USER@$SERVER_IP '
    if [ ! -d "/data/memoryx/repo" ]; then
        sudo git clone https://github.com/t0ken-ai/MemoryX.git /data/memoryx/repo
        echo "✅ Repository cloned"
    else
        cd /data/memoryx/repo
        sudo git pull origin main
        echo "✅ Repository updated"
    fi
'

# 配置 Nginx（内网）
echo "[7/8] Configuring Nginx..."
ssh $SSH_USER@$SERVER_IP '
    sudo curl -o /etc/nginx/sites-available/memoryx \
        https://raw.githubusercontent.com/t0ken-ai/MemoryX/main/deploy/nginx/memoryx-internal.conf
    sudo ln -sf /etc/nginx/sites-available/memoryx /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
    sudo nginx -t && sudo systemctl reload nginx
    echo "✅ Nginx configured"
'

# 配置 Systemd 服务
echo "[8/8] Configuring Systemd services..."
ssh $SSH_USER@$SERVER_IP '
    # 下载服务文件
    sudo curl -o /etc/systemd/system/memoryx-api.service \
        https://raw.githubusercontent.com/t0ken-ai/MemoryX/main/deploy/systemd/memoryx-api-docker.service
    sudo curl -o /etc/systemd/system/memoryx-webhook.service \
        https://raw.githubusercontent.com/t0ken-ai/MemoryX/main/deploy/systemd/memoryx-webhook.service
    
    # 提示配置 token
    echo "⚠️  Please edit webhook token:"
    echo "   sudo vim /etc/systemd/system/memoryx-webhook.service"
    echo "   Modify: Environment=\"DEPLOY_TOKEN=your-secret-token\""
    
    sudo systemctl daemon-reload
    sudo systemctl enable memoryx-api memoryx-webhook nginx
    echo "✅ Systemd services configured"
'

echo ""
echo "=========================================="
echo "✅ Server initialization completed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Configure DEPLOY_TOKEN in systemd service"
echo "  2. Run initial deployment: ./deploy.sh $SERVER_IP"
echo "  3. Verify: curl http://$SERVER_IP:8000/health"
echo ""
