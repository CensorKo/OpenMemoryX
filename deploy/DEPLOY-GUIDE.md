# MemoryX 安全部署指南

## 🚀 快速部署（不碰数据库和 Ollama）

### 方法 1: GitHub Actions 自动部署（推荐）

```bash
# 触发后会自动部署，不更新数据库和 Ollama
```

### 方法 2: 服务器本地执行（手动）

在 **31.65** 和 **31.66** 上分别执行：

```bash
# 1. 下载安全部署脚本
curl -o deploy-safe.sh \
  https://raw.githubusercontent.com/t0ken-ai/MemoryX/main/deploy/scripts/deploy-safe.sh
chmod +x deploy-safe.sh

# 2. 执行部署（release 或 alpha）
sudo ./deploy-safe.sh release   # 31.65 生产环境
sudo ./deploy-safe.sh alpha     # 31.66 测试环境
```

## ✅ 安全部署包括

| 组件 | 操作 | 说明 |
|------|------|------|
| **Docker 镜像** | 拉取最新 | `ghcr.io/t0ken-ai/memoryx-api:latest` |
| **静态文件** | 更新 | `/data/memoryx/static` |
| **API 容器** | 重启 | 使用新镜像 |
| **Webhook** | 重启 | 更新脚本 |
| **Nginx** | 重载 | 配置更新 |

## ⏭️ 不会触碰的组件

| 组件 | 地址 | 说明 |
|------|------|------|
| **Ollama** | 192.168.31.65:11434 | AI 模型服务 |
| **PostgreSQL** | localhost:5432 | 主数据库 |
| **Redis** | localhost:6379 | 缓存和队列 |
| **系统服务** | - | 操作系统级别 |

## 🔧 首次部署步骤

### 1. 准备服务器（31.65 / 31.66）

```bash
# 创建目录
sudo mkdir -p /data/memoryx/{static,backups,deploy/scripts}
sudo mkdir -p /etc/memoryx
sudo mkdir -p /var/log/memoryx

# 克隆代码
sudo git clone https://github.com/t0ken-ai/MemoryX.git /data/memoryx/repo
```

### 2. 配置环境变量

```bash
sudo vim /etc/memoryx/api.env
```

内容示例：
```env
DATABASE_URL=postgresql://memoryx:password@localhost:5432/memoryx
SECRET_KEY=your-secret-key-here
REDIS_URL=redis://localhost:6379/0
OLLAMA_HOST=http://192.168.31.65:11434
```

### 3. 安装 Docker 和 Nginx

```bash
# Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Nginx
sudo apt-get update
sudo apt-get install -y nginx
```

### 4. 配置 Nginx（内网）

```bash
sudo curl -o /etc/nginx/sites-available/memoryx \
  https://raw.githubusercontent.com/t0ken-ai/MemoryX/main/deploy/nginx/memoryx-internal.conf

sudo ln -sf /etc/nginx/sites-available/memoryx /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

### 5. 配置 Webhook 服务

```bash
# 复制服务文件
sudo curl -o /etc/systemd/system/memoryx-webhook.service \
  https://raw.githubusercontent.com/t0ken-ai/MemoryX/main/deploy/systemd/memoryx-webhook.service

# 编辑 token
sudo vim /etc/systemd/system/memoryx-webhook.service
# 修改: Environment="DEPLOY_TOKEN=your-secret-token"

sudo systemctl daemon-reload
sudo systemctl enable memoryx-webhook
```

### 6. 首次执行安全部署

```bash
sudo ./deploy-safe.sh release  # 或 alpha
```

## 🔒 安全配置检查

### 公网 Nginx（GitHub IP 限制）

```bash
# 检查配置
sudo nginx -t

# 查看 GitHub IP 限制是否生效
cat /etc/nginx/sites-available/t0ken | grep -A 50 "geo \$github_ip"
```

### 验证部署

```bash
# 内网检查
curl http://localhost:8000/health
curl http://localhost:9000/
curl http://localhost/

# 公网检查
curl https://t0ken.ai/api/health
curl https://t0ken.ai/
curl https://t0ken.ai/portal
```

## 🚨 故障排查

### 容器启动失败

```bash
# 查看日志
docker logs memoryx-api

# 检查环境变量
cat /etc/memoryx/api.env

# 手动启动测试
docker run --rm -it \
  -v /data/memoryx/static:/app/static:ro \
  -v /etc/memoryx/api.env:/app/.env:ro \
  ghcr.io/t0ken-ai/memoryx-api:latest
```

### 静态文件未更新

```bash
# 检查文件
ls -la /data/memoryx/static/

# 手动复制
sudo cp -r /data/memoryx/repo/static/* /data/memoryx/static/
```

### Webhook 未触发

```bash
# 检查服务状态
sudo systemctl status memoryx-webhook

# 查看日志
sudo journalctl -u memoryx-webhook -f

# 手动测试
curl -X POST "http://localhost:9000/"
```

## 📋 回滚

如果部署失败，快速回滚：

```bash
# 1. 停止新容器
docker stop memoryx-api
docker rm memoryx-api

# 2. 使用备份镜像
docker run -d \
  --name memoryx-api \
  --restart=unless-stopped \
  -p 127.0.0.1:8000:8000 \
  -v /data/memoryx/static:/app/static:ro \
  -v /etc/memoryx/api.env:/app/.env:ro \
  ghcr.io/t0ken-ai/memoryx-api:backup_xxx  # 使用备份标签

# 3. 恢复静态文件
cd /data/memoryx/backups
tar -xzf static_xxx.tar.gz -C /data/memoryx/
```

## 📝 更新日志

查看部署历史：

```bash
# 部署日志
cat /var/log/memoryx/deploy-safe.log

# Webhook 日志
cat /var/log/memoryx/webhook.log

# Nginx 日志
cat /var/log/nginx/memoryx-access.log
```
