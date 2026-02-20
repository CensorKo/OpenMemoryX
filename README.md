# MemoryX

Cognitive Memory API with AI-powered classification and vector search.

## Architecture

This project integrates the core AI capabilities from OpenMemoryX into a unified FastAPI architecture:

### Core Components

- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy**: Database ORM for user/project management
- **Celery + Redis**: Asynchronous task processing
- **Qdrant**: Vector database for memory storage and semantic search
- **Neo4j**: Graph database for entity relationships
- **Ollama/vLLM**: LLM for memory classification and embeddings

### Memory Core Features (from OpenMemoryX)

Located in `api/app/services/memory_core/`:

- **classification.py**: LLM-powered cognitive sector classification
  - Episodic: Events, conversations, experiences
  - Semantic: Facts, knowledge, user preferences
  - Procedural: Steps, processes, how-to guides
  - Emotional: Feelings, satisfaction, complaints
  - Reflective: Insights, patterns, recommendations

- **graph_memory_service.py**: Core memory operations with hybrid approach
  - Project-based organization
  - Vector similarity search
  - Graph-based entity relationships
  - Temporal knowledge graph

- **scoring.py**: Composite scoring algorithm for result ranking

- **temporal_kg.py**: Temporal knowledge graph for time-based queries

## API Endpoints

### Authentication
- `POST /api/register` - User registration
- `POST /api/login` - User login
- `GET /api/me` - Get current user

### API Keys
- `GET /api/api_keys` - List API keys
- `POST /api/api_keys` - Create API key
- `DELETE /api/api_keys/{id}` - Delete API key

### Memories
- `POST /api/v1/memories` - Create memory (with AI classification)
- `POST /api/v1/memories/batch` - Batch create memories
- `GET /api/v1/memories/task/{task_id}` - Get async task status
- `POST /api/v1/memories/search` - Vector similarity search
- `POST /api/v1/memories/graph/search` - Graph-based search
- `GET /api/v1/quota` - Get quota status

### Conversations
- `POST /api/v1/conversations/flush` - Flush conversation buffer
- `POST /api/v1/conversations/realtime` - Real-time conversation processing

### Projects
- `GET /api/projects` - List projects
- `POST /api/projects` - Create project
- `GET /api/projects/{id}` - Get project
- `PUT /api/projects/{id}` - Update project
- `DELETE /api/projects/{id}` - Delete project

### Agent Management
- `POST /api/agents/auto-register` - Auto-register agent
- `GET /api/agents/machine-stats` - Get machine statistics
- `POST /api/agents/claim/initiate` - Initiate claim
- `GET /api/agents/claim/status/{code}` - Check claim status
- `POST /api/agents/claim/verify` - Verify claim
- `POST /api/agents/claim/complete` - Complete claim

### Health
- `GET /api/health` - Health check
- `GET /api/health/detailed` - Detailed health check

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/memoryx

# Redis/Valkey
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key

# LLM Service
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5-14b
EMBED_MODEL=bge-m3

# Qdrant (vector store)
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Neo4j (graph store)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

## Deployment

### Docker Build

```bash
docker build -f Dockerfile.api -t memoryx-api:latest .
```

### Docker Run

```bash
docker run -d \
  --name memoryx-api \
  -p 8000:8000 \
  --env-file /etc/memoryx/api.env \
  memoryx-api:latest
```

### With Celery Worker

```bash
docker run -d \
  --name memoryx-celery \
  --env-file /etc/memoryx/api.env \
  memoryx-api:latest \
  python -m celery -A app.core.celery_config worker --loglevel=info
```

## Development

### Local Setup

```bash
cd api
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## SDK & Plugins

### Python SDK

```bash
pip install t0ken-memoryx
```

```python
from memoryx import connect_memory
memory = connect_memory()
memory.add("User prefers dark mode")
results = memory.search("user preferences")
```

### OpenClaw Plugin

```bash
npm install @t0ken.ai/memoryx-openclaw-plugin
```

Model Downloads (CDN):
- INT8 Model (122MB, recommended): https://static.t0ken.ai/models/model_int8.onnx
- FP32 Model (489MB): https://static.t0ken.ai/models/model.onnx

## License

MIT
