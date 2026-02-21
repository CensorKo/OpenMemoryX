# MemoryX

**Give your AI a long-term memory.**

MemoryX is a cognitive memory system that enables AI agents to remember user preferences, past conversations, and important facts across sessions.

## Why MemoryX?

**Problem**: AI assistants forget everything after each conversation. You have to repeat your preferences every time.

**Solution**: MemoryX gives your AI persistent, searchable memory that works across all your conversations.

### Features

- **Semantic Search** - Find relevant memories by meaning, not just keywords
- **Auto Classification** - Memories are automatically categorized (preferences, facts, plans, etc.)
- **Entity Relationships** - Understands connections between people, places, and things
- **Privacy First** - Self-host or use our cloud. Your data stays yours.
- **Multi-Agent Support** - Each agent has isolated memory, no cross-contamination

## Quick Start with OpenClaw

### 1. Install the Plugin

```bash
openclaw plugins install @t0ken.ai/memoryx-openclaw-plugin
```

### 2. Configure

Edit `~/.openclaw/openclaw.json`:

```json
{
  "plugins": {
    "slots": {
      "memory": "memoryx-openclaw-plugin"
    },
    "entries": {
      "memoryx-openclaw-plugin": {
        "enabled": true
      },
      "memory-core": {
        "enabled": false
      }
    }
  }
}
```

### 3. Restart Gateway

```bash
openclaw gateway restart
```

### 4. Start Chatting

Your AI now remembers! Try:

- "Remember that I prefer dark mode"
- "What do you know about my work?"
- "My birthday is next Tuesday, remind me"

## How It Works

### Automatic Memory Capture

Every conversation is automatically analyzed and important information is stored:

```
You: "I work at Google in Mountain View"
AI:  [Stores: User works at Google, User is located in Mountain View]
```

### Smart Recall

Before each response, relevant memories are injected as context:

```
You: "What's my work schedule?"
AI:  [Recalls: User works at Google, User mentioned 9-5 schedule]
     "Based on what you told me, you work 9-5 at Google..."
```

### LLM-Powered Tools

The AI can actively manage memories:

| Tool | What It Does |
|------|--------------|
| `memoryx_recall` | Search for specific memories |
| `memoryx_store` | Save important information |
| `memoryx_list` | Show all stored memories |
| `memoryx_forget` | Delete a memory |

## Self-Hosted Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  memoryx-api:
    image: ghcr.io/t0ken-ai/memoryx-api:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://memoryx:password@postgres:5432/memoryx
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_HOST=qdrant
      - NEO4J_URI=bolt://neo4j:7687
    depends_on: [postgres, redis, qdrant, neo4j]

  memoryx-celery:
    image: ghcr.io/t0ken-ai/memoryx-api:latest
    command: celery -A app.core.celery_config worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://memoryx:password@postgres:5432/memoryx
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_HOST=qdrant
      - NEO4J_URI=bolt://neo4j:7687
    depends_on: [postgres, redis]

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: memoryx
      POSTGRES_PASSWORD: password
      POSTGRES_DB: memoryx

  redis:
    image: redis:7-alpine

  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]

  neo4j:
    image: neo4j:5-community
    ports: ["7474:7474", "7687:7687"]
    environment:
      NEO4J_AUTH: neo4j/password
```

### Configure for Self-Hosted

```json
{
  "plugins": {
    "entries": {
      "memoryx-openclaw-plugin": {
        "enabled": true,
        "config": {
          "apiBaseUrl": "http://your-server:8000/api"
        }
      }
    }
  }
}
```

## API Reference

### Cloud API

Base URL: `https://t0ken.ai/api`

| Endpoint | Description |
|----------|-------------|
| `POST /v1/memories` | Store a memory |
| `POST /v1/memories/search` | Search memories |
| `GET /v1/memories` | List all memories |
| `DELETE /v1/memories/{id}` | Delete a memory |
| `POST /v1/conversations/flush` | Process conversation |

### Authentication

All requests require an API key:

```bash
curl -X POST https://t0ken.ai/api/v1/memories \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"content": "User prefers dark mode"}'
```

## Pricing

| Plan | Memories/Month | Price |
|------|----------------|-------|
| Free | 100 | $0 |
| Pro | Unlimited | $9/mo |

Self-hosted is free and unlimited.

## Links

- **Website**: [t0ken.ai](https://t0ken.ai)
- **Documentation**: [docs.t0ken.ai](https://docs.t0ken.ai)
- **GitHub**: [github.com/t0ken-ai/MemoryX](https://github.com/t0ken-ai/MemoryX)
- **Discord**: [Join our community](https://discord.gg/t0ken)

## License

MIT
