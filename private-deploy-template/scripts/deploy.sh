#!/bin/bash
# 安全部署 MemoryX 到指定服务器
# 用法: ./deploy.sh <IP>
# 示例: ./deploy.sh 192.168.31.65

set -e

SERVER_IP=${1:-"192.168.31.65"}
SSH_USER=${2:-"deploy"}

echo "=========================================="
echo "MemoryX Safe Deployment"
echo "=========================================="
echo "Target: $SERVER_IP"
echo "Time: $(date)"
echo "=========================================="
echo ""

# 检查 SSH
echo "[1/5] Checking SSH connection..."
ssh -o ConnectTimeout=5 $SSH_USER@$SERVER_IP "echo 'Connected'" || {
    echo "❌ SSH failed"
    exit 1
}

# 复制并执行部署脚本
echo "[2/5] Copying deployment script..."
scp ../deploy/scripts/deploy-safe.sh $SSH_USER@$SERVER_IP:/tmp/
ssh $SSH_USER@$SERVER_IP "chmod +x /tmp/deploy-safe.sh"

# 执行部署
echo "[3/5] Executing deployment..."
ssh $SSH_USER@$SERVER_IP "sudo /tmp/deploy-safe.sh" || {
    echo "❌ Deployment failed"
    exit 1
}

# 健康检查
echo "[4/5] Health check..."
sleep 5
HEALTH=$(ssh $SSH_USER@$SERVER_IP "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health" 2>/dev/null || echo "failed")

if [ "$HEALTH" = "200" ]; then
    echo "✅ Health check passed"
else
    echo "⚠️  Health check returned: $HEALTH"
fi

# 清理
echo "[5/5] Cleanup..."
ssh $SSH_USER@$SERVER_IP "rm -f /tmp/deploy-safe.sh"

echo ""
echo "=========================================="
echo "✅ Deployment completed!"
echo "=========================================="
echo ""
echo "Verify:"
echo "  curl http://$SERVER_IP:8000/health"
echo "  curl http://$SERVER_IP/"
echo ""
