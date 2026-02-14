#!/bin/bash
# MemoryX 安全部署脚本 - 只更新应用，不碰数据库和 Ollama
# 在 31.65 和 31.66 上执行

set -e

SERVER_IP=$(hostname -I | awk '{print $1}')
SERVER_TYPE=${1:-"alpha"}
LOG_FILE="/var/log/memoryx/deploy-safe.log"
DEPLOY_DIR="/data/memoryx"
IMAGE="ghcr.io/t0ken-ai/memoryx-api:latest"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a $LOG_FILE
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a $LOG_FILE
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a $LOG_FILE
    exit 1
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a $LOG_FILE
}

# 创建日志目录
sudo mkdir -p /var/log/memoryx

echo "=========================================="
echo "MemoryX 安全部署脚本"
echo "=========================================="
echo "服务器: $SERVER_IP"
echo "类型: $SERVER_TYPE"
echo ""

# ==================== 1. 检查依赖服务 ====================
info "[1/6] 检查依赖服务..."

# 检查 Docker
docker --version > /dev/null 2>&1 || error "Docker 未安装"
log "✅ Docker 已安装"

# 检查 nginx
nginx -v > /dev/null 2>&1 || error "Nginx 未安装"
log "✅ Nginx 已安装"

# 检查目录
sudo mkdir -p $DEPLOY_DIR/{static,backups,deploy/scripts}
log "✅ 目录结构检查完成"

# ==================== 2. 拉取最新代码 ====================
info "[2/6] 拉取最新代码..."

if [ -d "$DEPLOY_DIR/repo" ]; then
    cd $DEPLOY_DIR/repo
    sudo git fetch origin
    sudo git reset --hard origin/main
    log "✅ 代码已更新到最新"
else
    sudo git clone https://github.com/t0ken-ai/MemoryX.git $DEPLOY_DIR/repo
    log "✅ 代码已克隆"
fi

# ==================== 3. 更新静态文件 ====================
info "[3/6] 更新静态文件..."

# 备份旧静态文件
if [ -d "$DEPLOY_DIR/static" ]; then
    BACKUP_TIME=$(date +%Y%m%d_%H%M%S)
    sudo tar -czf "$DEPLOY_DIR/backups/static_$BACKUP_TIME.tar.gz" -C $DEPLOY_DIR static > /dev/null 2>&1 || true
    log "✅ 旧静态文件已备份"
fi

# 更新静态文件
sudo rm -rf $DEPLOY_DIR/static
sudo cp -r $DEPLOY_DIR/repo/static $DEPLOY_DIR/
sudo chown -R $(whoami):$(whoami) $DEPLOY_DIR/static
log "✅ 静态文件已更新"

# ==================== 4. 拉取 Docker 镜像 ====================
info "[4/6] 拉取 Docker 镜像..."

# 备份旧镜像
docker inspect $IMAGE > /dev/null 2>&1 && {
    BACKUP_TAG="backup_$(date +%Y%m%d_%H%M%S)"
    docker tag $IMAGE ${IMAGE%:*}:$BACKUP_TAG > /dev/null 2>&1 || true
    log "✅ 旧镜像已备份为 $BACKUP_TAG"
}

# 拉取新镜像
if docker pull $IMAGE; then
    log "✅ 新镜像已拉取: $IMAGE"
else
    warn "⚠️ 镜像拉取失败，使用现有镜像"
fi

# ==================== 5. 重启容器 ====================
info "[5/6] 重启应用容器..."

# 检查旧容器
OLD_CONTAINER=$(docker ps -q -f name=memoryx-api)
if [ -n "$OLD_CONTAINER" ]; then
    log "停止旧容器: $OLD_CONTAINER"
    docker stop memoryx-api > /dev/null 2>&1 || true
    docker rm memoryx-api > /dev/null 2>&1 || true
fi

# 启动新容器
if docker run -d \
    --name memoryx-api \
    --restart=unless-stopped \
    -p 127.0.0.1:8000:8000 \
    -v $DEPLOY_DIR/static:/app/static:ro \
    -v /etc/memoryx/api.env:/app/.env:ro \
    --env-file /etc/memoryx/api.env \
    $IMAGE; then
    log "✅ 新容器已启动"
else
    error "❌ 容器启动失败"
fi

# ==================== 6. 更新 Webhook 服务 ====================
info "[6/6] 更新 Webhook 服务..."

# 复制最新 webhook 脚本
sudo cp $DEPLOY_DIR/repo/deploy/scripts/webhook_server.py $DEPLOY_DIR/deploy/scripts/
sudo chmod +x $DEPLOY_DIR/deploy/scripts/webhook_server.py
log "✅ Webhook 脚本已更新"

# 重载 systemd 配置
sudo systemctl daemon-reload

# 重启 webhook 服务
if sudo systemctl restart memoryx-webhook; then
    log "✅ Webhook 服务已重启"
else
    warn "⚠️ Webhook 服务重启失败，请手动检查"
fi

# 重载 nginx
if sudo nginx -t &> /dev/null && sudo systemctl reload nginx; then
    log "✅ Nginx 已重载"
else
    warn "⚠️ Nginx 重载失败"
fi

# ==================== 健康检查 ====================
info "健康检查..."
sleep 5

HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "failed")

if [ "$HEALTH_STATUS" = "200" ]; then
    log "✅ API 健康检查通过 (HTTP 200)"
else
    error "❌ API 健康检查失败 (HTTP $HEALTH_STATUS)"
fi

WEBHOOK_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9000/ 2>/dev/null || echo "failed")
if [ "$WEBHOOK_STATUS" = "200" ]; then
    log "✅ Webhook 服务正常 (HTTP 200)"
else
    warn "⚠️ Webhook 服务异常 (HTTP $WEBHOOK_STATUS)"
fi

# ==================== 完成 ====================
echo ""
echo "=========================================="
echo "✅ 安全部署完成!"
echo "=========================================="
echo ""
echo "服务器: $SERVER_IP ($SERVER_TYPE)"
echo "时间: $(date)"
echo ""
echo "已更新:"
echo "  ✅ Docker 镜像 (ghcr.io/t0ken-ai/memoryx-api:latest)"
echo "  ✅ 静态文件 (/data/memoryx/static)"
echo "  ✅ API 容器"
echo "  ✅ Webhook 服务"
echo "  ✅ Nginx 配置"
echo ""
echo "未触碰:"
echo "  ⏭️  Ollama (192.168.31.65:11434)"
echo "  ⏭️  PostgreSQL"
echo "  ⏭️  Redis"
echo "  ⏭️  系统服务"
echo ""
echo "验证命令:"
echo "  curl http://localhost:8000/health"
echo "  curl http://localhost:9000/"
echo "  curl http://localhost/"
echo ""
