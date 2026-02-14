#!/bin/bash
# MemoryX 服务器部署清单
# 在 31.65 和 31.66 上分别执行

set -e

echo "=========================================="
echo "MemoryX 服务器部署脚本"
echo "=========================================="

# 配置
SERVER_IP=$(hostname -I | awk '{print $1}')
SERVER_TYPE=${1:-"alpha"}  # release 或 alpha

echo "服务器: $SERVER_IP"
echo "类型: $SERVER_TYPE"
echo ""

# ==================== 1. 基础环境 ====================
echo "[1/7] 创建用户和目录..."

if ! id -u memoryx &>/dev/null; then
    sudo useradd -r -s /bin/false memoryx
    echo "✅ 用户 memoryx 已创建"
else
    echo "✅ 用户 memoryx 已存在"
fi

sudo mkdir -p /data/memoryx/{api,static,backups,deploy/scripts}
sudo mkdir -p /var/log/memoryx
sudo mkdir -p /etc/memoryx
sudo chown -R memoryx:memoryx /data/memoryx /var/log/memoryx

echo "✅ 目录创建完成"
echo ""

# ==================== 2. 代码部署 ====================
echo "[2/7] 部署代码..."

if [ ! -d "/data/memoryx/repo" ]; then
    sudo -u memoryx git clone https://github.com/t0ken-ai/MemoryX.git /data/memoryx/repo
    echo "✅ 代码克隆完成"
else
    cd /data/memoryx/repo
    sudo -u memoryx git pull origin main
    echo "✅ 代码更新完成"
fi

# 复制部署脚本
sudo cp /data/memoryx/repo/deploy/scripts/*.sh /data/memoryx/deploy/scripts/
sudo cp /data/memoryx/repo/deploy/scripts/*.py /data/memoryx/deploy/scripts/
sudo chmod +x /data/memoryx/deploy/scripts/*.sh
sudo chown -R memoryx:memoryx /data/memoryx/deploy

echo "✅ 部署脚本准备完成"
echo ""

# ==================== 3. Python 依赖 ====================
echo "[3/7] 安装 Python 依赖..."

cd /data/memoryx/repo/api
pip install -r requirements.txt -q

echo "✅ Python 依赖安装完成"
echo ""

# ==================== 4. Nginx 配置 ====================
echo "[4/7] 配置 Nginx..."

if [ ! -f "/etc/nginx/sites-available/memoryx" ]; then
    sudo cp /data/memoryx/repo/deploy/nginx/memoryx.conf /etc/nginx/sites-available/memoryx
    sudo ln -sf /etc/nginx/sites-available/memoryx /etc/nginx/sites-enabled/
    echo "✅ Nginx 配置已添加"
else
    echo "✅ Nginx 配置已存在"
fi

sudo nginx -t && echo "✅ Nginx 配置检查通过"
echo ""

# ==================== 5. Systemd 服务 ====================
echo "[5/7] 配置 Systemd 服务..."

# 复制服务文件
sudo cp /data/memoryx/repo/deploy/systemd/memoryx-api.service /etc/systemd/system/
sudo cp /data/memoryx/repo/deploy/systemd/memoryx-webhook.service /etc/systemd/system/

# 创建环境变量文件（如果不存在）
if [ ! -f "/etc/memoryx/api.env" ]; then
    sudo tee /etc/memoryx/api.env << EOF
DATABASE_URL=sqlite:///./memoryx.db
SECRET_KEY=$(openssl rand -hex 32)
REDIS_URL=redis://localhost:6379/0
OLLAMA_HOST=http://192.168.31.65:11434
EOF
    echo "✅ 环境变量文件已创建"
    echo "⚠️  请编辑 /etc/memoryx/api.env 配置正确的数据库连接"
else
    echo "✅ 环境变量文件已存在"
fi

# 提示配置 webhook token
echo ""
echo "⚠️  请手动编辑 webhook token:"
echo "   sudo vim /etc/systemd/system/memoryx-webhook.service"
echo "   修改 Environment=\"DEPLOY_TOKEN=your-secret-token\""
echo ""

echo "✅ Systemd 服务配置完成"
echo ""

# ==================== 6. 开机启动 ====================
echo "[6/7] 配置开机启动..."

sudo systemctl daemon-reload
sudo systemctl enable memoryx-api memoryx-webhook nginx

echo "✅ 开机启动配置完成"
echo ""

# ==================== 7. 启动服务 ====================
echo "[7/7] 启动服务..."

sudo systemctl restart nginx
echo "✅ Nginx 已启动"

echo ""
echo "⚠️  请先配置 webhook token，然后启动服务:"
echo "   sudo systemctl start memoryx-webhook"
echo "   sudo systemctl start memoryx-api"
echo ""

# ==================== 完成 ====================
echo "=========================================="
echo "📋 部署清单完成"
echo "=========================================="
echo ""
echo "待办事项:"
echo "  [ ] 编辑 webhook token: sudo vim /etc/systemd/system/memoryx-webhook.service"
echo "  [ ] 编辑数据库配置: sudo vim /etc/memoryx/api.env"
echo "  [ ] 启动服务: sudo systemctl start memoryx-webhook memoryx-api"
echo "  [ ] 检查状态: sudo systemctl status memoryx-api memoryx-webhook"
echo "  [ ] 测试访问: curl http://localhost:8000/health"
echo ""
echo "GitHub Secrets 需要配置:"
echo "  DEPLOY_WEBHOOK_URL: https://t0ken.ai/deploy"
echo "  DEPLOY_TOKEN: <与服务器上配置的一致>"
echo ""
