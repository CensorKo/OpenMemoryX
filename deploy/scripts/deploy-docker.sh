#!/bin/bash
# MemoryX Docker 部署脚本
# 用法: ./deploy.sh [release|alpha]

set -e

DEPLOY_TYPE=${1:-alpha}
LOG_FILE="/var/log/memoryx/deploy.log"
DEPLOY_DIR="/data/memoryx"
BACKUP_DIR="/data/memoryx/backups"
IMAGE="ghcr.io/t0ken-ai/memoryx-api:latest"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a $LOG_FILE
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a $LOG_FILE
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a $LOG_FILE
}

# 创建目录
mkdir -p $DEPLOY_DIR $BACKUP_DIR /var/log/memoryx

# 备份当前版本
backup_current() {
    log "Creating backup..."
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    docker save $IMAGE > "$BACKUP_DIR/image_$TIMESTAMP.tar" 2>/dev/null || true
    
    # 保留最近5个备份
    ls -t $BACKUP_DIR/image_*.tar 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
    log "Backup created"
}

# 拉取最新镜像
pull_image() {
    log "Pulling latest image: $IMAGE"
    docker pull $IMAGE
    log "Image pulled successfully"
}

# 更新静态文件
update_static() {
    log "Updating static files..."
    
    # 克隆或更新代码
    if [ -d "$DEPLOY_DIR/repo" ]; then
        cd $DEPLOY_DIR/repo
        git fetch origin
        git reset --hard origin/main
    else
        git clone https://github.com/t0ken-ai/MemoryX.git $DEPLOY_DIR/repo
    fi
    
    # 复制静态文件
    rm -rf $DEPLOY_DIR/static
    cp -r $DEPLOY_DIR/repo/static $DEPLOY_DIR/
    
    log "Static files updated"
}

# 重启容器
restart_container() {
    log "Restarting container..."
    
    # 使用 systemd 重启
    sudo systemctl restart memoryx-api
    
    log "Container restarted"
}

# 健康检查
health_check() {
    log "Running health check..."
    
    sleep 10
    
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        log "✅ Health check passed"
    else
        error "❌ Health check failed"
    fi
}

# 主流程
main() {
    log "=========================================="
    log "Starting Docker deployment: $DEPLOY_TYPE"
    log "=========================================="
    
    backup_current
    pull_image
    update_static
    restart_container
    health_check
    
    log "=========================================="
    log "✅ Docker deployment completed!"
    log "=========================================="
}

main
