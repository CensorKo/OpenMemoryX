#!/usr/bin/env python3
"""
Generate OpenAPI specification for MemoryX API.
Run from the api directory: python generate_openapi.py

This script generates OpenAPI docs without requiring database connection.
"""

import json
import os
import sys

# Set dummy environment variables before importing app
os.environ["DATABASE_URL"] = "sqlite:///./dummy.db"
os.environ["QDRANT_HOST"] = "localhost"
os.environ["QDRANT_PORT"] = "6333"
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock database engine before importing
from unittest.mock import patch, MagicMock

# Mock the database module to avoid actual connections
sys.modules['app.core.database'] = MagicMock()
sys.modules['sqlalchemy'] = MagicMock()
sys.modules['sqlalchemy.orm'] = MagicMock()

# Now import the app - it will use mocked database
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers directly
from app.routers import auth, api_keys, memories, projects, stats
from app.routers import conversations
from app.routers.otp import router as otp_router
from app.routers.firebase_auth import router as firebase_router
from app.routers.agent_autoregister import router as agent_router
from app.routers.agent_claim import router as claim_router

# Create app without database initialization
app = FastAPI(
    title="MemoryX",
    description="MemoryX - Free Cognitive Memory API with Queue",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(auth.router, prefix="/api")
app.include_router(api_keys.router, prefix="/api")
app.include_router(memories.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(otp_router, prefix="/api")
app.include_router(firebase_router, prefix="/api")
app.include_router(agent_router, prefix="/api")
app.include_router(claim_router, prefix="/api")


def generate_openapi():
    """Generate OpenAPI JSON file"""
    openapi_schema = app.openapi()
    
    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "openapi.json")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    
    print(f"OpenAPI schema generated: {output_path}")
    print(f"Title: {openapi_schema.get('info', {}).get('title')}")
    print(f"Version: {openapi_schema.get('info', {}).get('version')}")
    print(f"Paths: {len(openapi_schema.get('paths', {}))}")


if __name__ == "__main__":
    generate_openapi()
