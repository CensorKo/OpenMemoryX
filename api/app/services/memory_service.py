"""
Memory Service Module - Vector Storage and Retrieval
记忆服务模块 - 向量存储与检索
"""
import os
import uuid
import json
import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, asdict

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, 
    Filter, FieldCondition, MatchValue, MatchKeyword,
    Range, ScoredPoint
)

from app.services.classification import (
    ClassificationResult, classify_memory, quick_classify,
    MemoryCategory, MemoryImportance
)
from app.services.scoring import calculate_memory_score, ScoringFactors

logger = logging.getLogger(__name__)

# 集合配置
COLLECTION_NAME = "memories"
VECTOR_SIZE = 1536  # OpenAI text-embedding-3-small 维度


@dataclass
class Memory:
    """记忆数据模型"""
    id: str
    user_id: str
    content: str
    project_id: str = "default"
    category: str = "other"
    subcategory: Optional[str] = None
    importance: int = 3
    tags: List[str] = None
    summary: Optional[str] = None
    entities: List[Dict] = None
    metadata: Dict = None
    created_at: str = None
    updated_at: str = None
    score: float = 0.0
    vector_id: Optional[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.entities is None:
            self.entities = []
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.updated_at is None:
            self.updated_at = self.created_at
        if self.vector_id is None:
            self.vector_id = self.id


@dataclass
class SearchResult:
    """搜索结果模型"""
    memory: Memory
    score: float
    vector_score: float
    semantic_score: float
    temporal_score: float
    category_score: float


class EmbeddingService:
    """向量嵌入服务"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        self.timeout = 30.0
    
    async def get_embedding(self, text: str) -> List[float]:
        """获取文本的向量嵌入"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "input": text[:8000],  # 限制输入长度
                "model": self.model
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["embedding"]
                
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            # 返回零向量作为回退
            return [0.0] * VECTOR_SIZE
    
    def get_embedding_sync(self, text: str) -> List[float]:
        """同步获取向量嵌入"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "input": text[:8000],
                "model": self.model
            }
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/embeddings",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["embedding"]
                
        except Exception as e:
            logger.error(f"Failed to get embedding sync: {e}")
            return [0.0] * VECTOR_SIZE


class MemoryService:
    """记忆服务主类 - 管理向量存储和检索"""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, qdrant_url: Optional[str] = None, api_key: Optional[str] = None):
        if self._initialized:
            return
            
        self.qdrant_url = qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.qdrant_api_key = api_key or os.getenv("QDRANT_API_KEY")
        
        # 初始化Qdrant客户端
        if self.qdrant_api_key:
            self.client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key)
        else:
            self.client = QdrantClient(url=self.qdrant_url)
        
        # 初始化嵌入服务
        self.embedding_service = EmbeddingService()
        
        # 确保集合存在
        self._ensure_collection()
        
        self._initialized = True
        logger.info(f"MemoryService initialized with Qdrant at {self.qdrant_url}")
    
    def _ensure_collection(self):
        """确保记忆集合存在"""
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if COLLECTION_NAME not in collection_names:
                self.client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=VECTOR_SIZE,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {COLLECTION_NAME}")
                
                # 创建有用的索引
                self._create_indexes()
                
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")
            raise
    
    def _create_indexes(self):
        """创建字段索引以优化查询"""
        try:
            # 为用户ID创建索引
            self.client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="user_id",
                field_type="keyword"
            )
            
            # 为项目ID创建索引
            self.client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="project_id",
                field_type="keyword"
            )
            
            # 为分类创建索引
            self.client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="category",
                field_type="keyword"
            )
            
            # 为创建时间创建索引
            self.client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="created_at",
                field_type="datetime"
            )
            
            logger.info("Created payload indexes")
        except Exception as e:
            logger.warning(f"Index creation may have failed (could already exist): {e}")
    
    async def create_memory(
        self, 
        user_id: str, 
        content: str, 
        project_id: str = "default",
        metadata: Optional[Dict] = None,
        auto_classify: bool = True
    ) -> Memory:
        """
        创建新记忆
        
        Args:
            user_id: 用户ID
            content: 记忆内容
            project_id: 项目ID
            metadata: 附加元数据
            auto_classify: 是否自动分类
            
        Returns:
            Memory: 创建的记忆对象
        """
        memory_id = str(uuid.uuid4())
        
        # 自动分类
        classification = None
        if auto_classify:
            try:
                classification = await classify_memory(content)
            except Exception as e:
                logger.warning(f"Auto-classification failed: {e}")
                classification = quick_classify(content)
        else:
            classification = quick_classify(content)
        
        # 计算记忆分数
        scoring_factors = ScoringFactors(
            importance=classification.importance.value,
            recency=1.0,  # 新记忆
            category_boost=self._get_category_boost(classification.category),
            user_interaction=1.0
        )
        memory_score = calculate_memory_score(scoring_factors)
        
        # 创建记忆对象
        memory = Memory(
            id=memory_id,
            user_id=user_id,
            content=content,
            project_id=project_id,
            category=classification.category.value,
            subcategory=classification.subcategory,
            importance=classification.importance.value,
            tags=classification.tags,
            summary=classification.summary,
            entities=classification.entities,
            metadata=metadata or {},
            score=memory_score
        )
        
        # 获取向量嵌入
        embedding = await self.embedding_service.get_embedding(content)
        
        # 存储到Qdrant
        point = PointStruct(
            id=memory.vector_id,
            vector=embedding,
            payload=self._memory_to_payload(memory)
        )
        
        self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=[point]
        )
        
        logger.info(f"Created memory {memory_id} for user {user_id}")
        return memory
    
    def create_memory_sync(
        self,
        user_id: str,
        content: str,
        project_id: str = "default",
        metadata: Optional[Dict] = None
    ) -> Memory:
        """同步创建记忆（用于Celery任务）"""
        memory_id = str(uuid.uuid4())
        
        # 使用规则分类（同步）
        classification = quick_classify(content)
        
        # 计算分数
        scoring_factors = ScoringFactors(
            importance=classification.importance.value,
            recency=1.0,
            category_boost=self._get_category_boost(classification.category),
            user_interaction=1.0
        )
        memory_score = calculate_memory_score(scoring_factors)
        
        memory = Memory(
            id=memory_id,
            user_id=user_id,
            content=content,
            project_id=project_id,
            category=classification.category.value,
            subcategory=classification.subcategory,
            importance=classification.importance.value,
            tags=classification.tags,
            summary=classification.summary,
            entities=classification.entities,
            metadata=metadata or {},
            score=memory_score
        )
        
        # 同步获取嵌入
        embedding = self.embedding_service.get_embedding_sync(content)
        
        point = PointStruct(
            id=memory.vector_id,
            vector=embedding,
            payload=self._memory_to_payload(memory)
        )
        
        self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=[point]
        )
        
        logger.info(f"Created memory sync {memory_id}")
        return memory
    
    async def search_memories(
        self,
        user_id: str,
        query: str,
        project_id: Optional[str] = None,
        limit: int = 10,
        category: Optional[str] = None,
        min_score: float = 0.0
    ) -> List[SearchResult]:
        """
        搜索记忆
        
        Args:
            user_id: 用户ID
            query: 搜索查询
            project_id: 可选的项目过滤
            limit: 返回结果数量
            category: 可选的分类过滤
            min_score: 最小分数阈值
            
        Returns:
            List[SearchResult]: 搜索结果列表
        """
        # 获取查询向量
        query_vector = await self.embedding_service.get_embedding(query)
        
        # 构建过滤条件
        must_conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=user_id))
        ]
        
        if project_id:
            must_conditions.append(
                FieldCondition(key="project_id", match=MatchValue(value=project_id))
            )
        
        if category:
            must_conditions.append(
                FieldCondition(key="category", match=MatchValue(value=category))
            )
        
        search_filter = Filter(must=must_conditions)
        
        # 执行向量搜索
        results = self.client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            query_filter=search_filter,
            limit=limit * 2,  # 获取更多用于重排序
            score_threshold=0.3  # 基础相似度阈值
        )
        
        # 计算综合分数并重排序
        search_results = []
        query_lower = query.lower()
        
        for scored_point in results:
            memory = self._payload_to_memory(scored_point.payload, scored_point.id)
            
            # 计算各种分数
            vector_score = scored_point.score
            semantic_score = self._calculate_semantic_score(memory, query_lower)
            temporal_score = self._calculate_temporal_score(memory)
            category_score = self._calculate_category_score(memory, query_lower)
            
            # 综合分数（可调整权重）
            final_score = (
                vector_score * 0.5 +
                semantic_score * 0.2 +
                temporal_score * 0.15 +
                category_score * 0.15
            )
            
            if final_score >= min_score:
                search_results.append(SearchResult(
                    memory=memory,
                    score=final_score,
                    vector_score=vector_score,
                    semantic_score=semantic_score,
                    temporal_score=temporal_score,
                    category_score=category_score
                ))
        
        # 按分数排序并限制结果
        search_results.sort(key=lambda x: x.score, reverse=True)
        return search_results[:limit]
    
    def get_memories(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        category: Optional[str] = None
    ) -> Tuple[List[Memory], int]:
        """
        获取用户记忆列表
        
        Returns:
            Tuple[List[Memory], int]: (记忆列表, 总数)
        """
        must_conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=user_id))
        ]
        
        if project_id:
            must_conditions.append(
                FieldCondition(key="project_id", match=MatchValue(value=project_id))
            )
        
        if category:
            must_conditions.append(
                FieldCondition(key="category", match=MatchValue(value=category))
            )
        
        scroll_filter = Filter(must=must_conditions)
        
        # 获取总数
        count_result = self.client.count(
            collection_name=COLLECTION_NAME,
            count_filter=scroll_filter
        )
        total = count_result.count
        
        # 分页获取
        results = self.client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=scroll_filter,
            limit=limit,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        
        memories = [
            self._payload_to_memory(point.payload, point.id)
            for point in results[0]
        ]
        
        return memories, total
    
    def get_memory(self, memory_id: str, user_id: str) -> Optional[Memory]:
        """获取单个记忆"""
        try:
            result = self.client.retrieve(
                collection_name=COLLECTION_NAME,
                ids=[memory_id],
                with_payload=True,
                with_vectors=False
            )
            
            if not result:
                return None
            
            point = result[0]
            memory = self._payload_to_memory(point.payload, point.id)
            
            # 验证用户所有权
            if memory.user_id != user_id:
                return None
            
            return memory
            
        except Exception as e:
            logger.error(f"Failed to get memory {memory_id}: {e}")
            return None
    
    def update_memory(
        self,
        memory_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Memory]:
        """更新记忆"""
        memory = self.get_memory(memory_id, user_id)
        if not memory:
            return None
        
        # 应用更新
        if "content" in updates:
            memory.content = updates["content"]
            # 重新获取嵌入
            embedding = self.embedding_service.get_embedding_sync(memory.content)
        else:
            embedding = None
        
        if "metadata" in updates:
            memory.metadata.update(updates["metadata"])
        
        if "project_id" in updates:
            memory.project_id = updates["project_id"]
        
        memory.updated_at = datetime.utcnow().isoformat()
        
        # 更新到Qdrant
        if embedding is not None:
            point = PointStruct(
                id=memory.vector_id,
                vector=embedding,
                payload=self._memory_to_payload(memory)
            )
        else:
            # 仅更新payload
            self.client.set_payload(
                collection_name=COLLECTION_NAME,
                payload=self._memory_to_payload(memory),
                points=[memory.vector_id]
            )
            return memory
        
        self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=[point]
        )
        
        logger.info(f"Updated memory {memory_id}")
        return memory
    
    def delete_memory(self, memory_id: str, user_id: str) -> bool:
        """删除记忆"""
        memory = self.get_memory(memory_id, user_id)
        if not memory:
            return False
        
        try:
            self.client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=[memory_id]
            )
            logger.info(f"Deleted memory {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False
    
    def delete_user_memories(self, user_id: str, project_id: Optional[str] = None) -> int:
        """
        删除用户的所有记忆
        
        Returns:
            int: 删除的记忆数量
        """
        must_conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=user_id))
        ]
        
        if project_id:
            must_conditions.append(
                FieldCondition(key="project_id", match=MatchValue(value=project_id))
            )
        
        delete_filter = Filter(must=must_conditions)
        
        # 获取要删除的数量
        count_result = self.client.count(
            collection_name=COLLECTION_NAME,
            count_filter=delete_filter
        )
        
        # 执行删除
        self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=delete_filter
        )
        
        logger.info(f"Deleted {count_result.count} memories for user {user_id}")
        return count_result.count
    
    def _memory_to_payload(self, memory: Memory) -> Dict:
        """将记忆对象转换为Qdrant payload"""
        return {
            "id": memory.id,
            "user_id": memory.user_id,
            "content": memory.content,
            "project_id": memory.project_id,
            "category": memory.category,
            "subcategory": memory.subcategory,
            "importance": memory.importance,
            "tags": memory.tags,
            "summary": memory.summary,
            "entities": memory.entities,
            "metadata": memory.metadata,
            "created_at": memory.created_at,
            "updated_at": memory.updated_at,
            "score": memory.score
        }
    
    def _payload_to_memory(self, payload: Dict, vector_id: str) -> Memory:
        """将Qdrant payload转换为记忆对象"""
        return Memory(
            id=payload.get("id", vector_id),
            user_id=payload["user_id"],
            content=payload["content"],
            project_id=payload.get("project_id", "default"),
            category=payload.get("category", "other"),
            subcategory=payload.get("subcategory"),
            importance=payload.get("importance", 3),
            tags=payload.get("tags", []),
            summary=payload.get("summary"),
            entities=payload.get("entities", []),
            metadata=payload.get("metadata", {}),
            created_at=payload.get("created_at"),
            updated_at=payload.get("updated_at"),
            score=payload.get("score", 0.0),
            vector_id=vector_id
        )
    
    def _get_category_boost(self, category: MemoryCategory) -> float:
        """获取分类权重加成"""
        boosts = {
            MemoryCategory.FACT: 1.0,
            MemoryCategory.PREFERENCE: 1.2,
            MemoryCategory.EVENT: 1.1,
            MemoryCategory.PERSON: 1.3,
            MemoryCategory.TASK: 1.4,
            MemoryCategory.GOAL: 1.3,
            MemoryCategory.EMOTION: 1.0,
            MemoryCategory.KNOWLEDGE: 1.1,
            MemoryCategory.RELATIONSHIP: 1.2,
            MemoryCategory.HABIT: 0.9,
            MemoryCategory.OTHER: 0.8
        }
        return boosts.get(category, 1.0)
    
    def _calculate_semantic_score(self, memory: Memory, query: str) -> float:
        """计算语义匹配分数"""
        score = 0.0
        
        # 检查标签匹配
        for tag in memory.tags:
            if tag.lower() in query:
                score += 0.3
        
        # 检查摘要匹配
        if memory.summary and memory.summary.lower() in query:
            score += 0.2
        
        # 检查实体匹配
        for entity in memory.entities:
            entity_name = entity.get("name", "").lower()
            if entity_name and entity_name in query:
                score += 0.25
        
        # 检查分类匹配
        if memory.category.lower() in query:
            score += 0.15
        
        return min(score, 1.0)
    
    def _calculate_temporal_score(self, memory: Memory) -> float:
        """计算时间相关性分数（越新分数越高）"""
        try:
            created = datetime.fromisoformat(memory.created_at.replace('Z', '+00:00'))
            now = datetime.utcnow()
            days_diff = (now - created).days
            
            # 使用指数衰减
            import math
            score = math.exp(-days_diff / 30.0)  # 30天半衰期
            return min(max(score, 0.1), 1.0)
        except:
            return 0.5
    
    def _calculate_category_score(self, memory: Memory, query: str) -> float:
        """计算分类相关性分数"""
        # 基于查询意图判断分类相关性
        category_keywords = {
            "preference": ["喜欢", "偏好", "favorite", "prefer", "like"],
            "task": ["任务", "待办", "task", "todo", "需要"],
            "event": ["事件", "活动", "event", "activity", "happened"],
            "person": ["人", "person", "who", "name"],
            "goal": ["目标", "计划", "goal", "plan", "want"]
        }
        
        for cat, keywords in category_keywords.items():
            if any(kw in query for kw in keywords):
                if memory.category == cat:
                    return 1.0
                return 0.3
        
        return 0.5
    
    def get_stats(self, user_id: str) -> Dict:
        """获取用户记忆统计"""
        user_filter = Filter(
            must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
        )
        
        count_result = self.client.count(
            collection_name=COLLECTION_NAME,
            count_filter=user_filter
        )
        
        # 获取分类统计
        categories = {}
        for category in MemoryCategory:
            cat_filter = Filter(must=[
                FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                FieldCondition(key="category", match=MatchValue(value=category.value))
            ])
            cat_count = self.client.count(
                collection_name=COLLECTION_NAME,
                count_filter=cat_filter
            )
            if cat_count.count > 0:
                categories[category.value] = cat_count.count
        
        return {
            "total_memories": count_result.count,
            "categories": categories,
            "user_id": user_id
        }
    
    def close(self):
        """关闭服务连接"""
        if hasattr(self, 'client') and self.client:
            self.client.close()
            logger.info("MemoryService closed")


# 全局服务实例
_memory_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    """获取记忆服务实例（单例）"""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service


def init_memory_service(qdrant_url: Optional[str] = None, api_key: Optional[str] = None) -> MemoryService:
    """初始化记忆服务"""
    global _memory_service
    _memory_service = MemoryService(qdrant_url, api_key)
    return _memory_service