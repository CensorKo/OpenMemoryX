# AgentsOnly - MemoryX 私有部署配置

⚠️ **私有仓库 - 包含敏感信息**

此仓库包含 MemoryX 的内部部署配置和敏感信息，**不要公开**。

---

## 📁 目录结构

```
AgentsOnly/
├── inventory/           # 服务器清单
├── environments/        # 环境变量（加密）
├── playbooks/          # 部署剧本
└── docs/               # 内部文档
```

---

## 🖥️ 服务器清单

### 生产环境 (31.65)
```
IP: 192.168.31.65
Hostname: memoryx-prod
Role: Production
Services:
  - Docker API (ghcr.io/t0ken-ai/memoryx-api)
  - Nginx (:80)
  - Webhook (:9000)
External Access:
  - https://t0ken.ai/api/* -> 192.168.31.65:8000
  - https://t0ken.ai/portal -> 192.168.31.65:80
```

### 测试环境 (31.66)
```
IP: 192.168.31.66
Hostname: memoryx-test
Role: Staging/Alpha
Services:
  - Docker API (ghcr.io/t0ken-ai/memoryx-api)
  - Nginx (:80)
  - Webhook (:9000)
External Access:
  - https://alpha.t0ken.ai/* -> 192.168.31.66 (optional)
```

---

## 🔐 环境变量模板

### 31.65 生产环境 (`environments/prod.env`)
```bash
# 数据库（已有，不修改）
DATABASE_URL=postgresql://memoryx:YOUR_DB_PASSWORD@localhost:5432/memoryx

# Redis（已有，不修改）
REDIS_URL=redis://localhost:6379/0

# 安全密钥（生成后填入）
SECRET_KEY=GENERATE_WITH: openssl rand -hex 32

# Ollama（已有服务，不修改）
OLLAMA_HOST=http://192.168.31.65:11434

# 其他配置
APP_NAME=MemoryX Production
DEBUG=false
```

### 31.66 测试环境 (`environments/test.env`)
```bash
# 可以使用 SQLite 简化
DATABASE_URL=sqlite:///./memoryx.db

# Redis（如有）
REDIS_URL=redis://localhost:6379/0

# 安全密钥
SECRET_KEY=GENERATE_WITH: openssl rand -hex 32

# 共享 Ollama
OLLAMA_HOST=http://192.168.31.65:11434

# 其他配置
APP_NAME=MemoryX Test
DEBUG=true
```

---

## 🔑 GitHub Secrets 清单

### 公开仓库 (MemoryX) 需要配置
```
DEPLOY_WEBHOOK_URL=https://t0ken.ai/deploy
DEPLOY_TOKEN=GENERATE_RANDOM_TOKEN
NPM_TOKEN=npm_xxxxxxxx
PYPI_API_TOKEN=pypi-xxxxxxxx
```

### 服务器上的 Webhook Token
```bash
# 31.65 / 31.66 上配置 /etc/systemd/system/memoryx-webhook.service
Environment="DEPLOY_TOKEN=same_as_github_secret"
```

---

## 🚀 快速部署

### 初始化服务器（首次）
```bash
# 在 31.65 上
./scripts/init-server.sh 192.168.31.65 production

# 在 31.66 上
./scripts/init-server.sh 192.168.31.66 test
```

### 安全部署（不碰数据库）
```bash
# 自动部署到两台服务器
./scripts/deploy-all.sh

# 或单独部署
./scripts/deploy.sh 192.168.31.65
./scripts/deploy.sh 192.168.31.66
```

---

## 🔒 安全注意事项

1. **永远不要提交真实密码**到任何仓库
2. **使用环境变量**或加密工具（如 ansible-vault, sops）
3. **定期轮换密钥**：DEPLOY_TOKEN, SECRET_KEY 等
4. **限制 IP 访问**：公网 nginx 已配置 GitHub IP 白名单
5. **备份敏感数据**：定期备份数据库和配置文件

---

## 📞 联系方式

- 运维问题：联系 DevOps 团队
- 部署失败：检查 `/var/log/memoryx/` 日志
- 紧急情况：手动回滚到上一版本

---

*Last updated: 2026-02-15*
