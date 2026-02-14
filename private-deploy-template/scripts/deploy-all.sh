#!/bin/bash
# 部署到所有服务器

set -e

echo "=========================================="
echo "MemoryX Deploy to All Servers"
echo "=========================================="
echo ""

# 部署到生产环境 (31.65)
echo "🚀 Deploying to Production (31.65)..."
./deploy.sh 192.168.31.65 || {
    echo "❌ Production deployment failed"
    exit 1
}

echo ""
echo "✅ Production deployed"
echo ""

# 部署到测试环境 (31.66)
echo "🧪 Deploying to Test (31.66)..."
./deploy.sh 192.168.31.66 || {
    echo "❌ Test deployment failed"
    exit 1
}

echo ""
echo "✅ Test deployed"
echo ""

echo "=========================================="
echo "✅ All deployments completed!"
echo "=========================================="
echo ""
echo "Verify:"
echo "  Production: curl http://192.168.31.65:8000/health"
echo "  Test:       curl http://192.168.31.66:8000/health"
echo "  Public:     curl https://t0ken.ai/api/health"
echo ""
