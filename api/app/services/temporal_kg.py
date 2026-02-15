"""
Temporal Knowledge Graph Module - Time-aware Knowledge Representation
时序知识图谱模块 - 时间感知知识表示
"""
import json
import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import re

logger = logging.getLogger(__name__)


class RelationType(Enum):
    """关系类型枚举"""
    IS_A = "is_a"                    # 是一个/是一种
    HAS_A = "has_a"                  # 有一个/拥有
    PART_OF = "part_of"              # 是...的一部分
    LOCATED_AT = "located_at"        # 位于
    OCCURRED_AT = "occurred_at"      # 发生在
    HAPPENED_BEFORE = "happened_before"  # 发生在...之前
    HAPPENED_AFTER = "happened_after"    # 发生在...之后
    RELATED_TO = "related_to"        # 相关于
    CAUSED = "caused"                # 导致
    CAUSED_BY = "caused_by"          # 被导致
    SIMILAR_TO = "similar_to"        # 相似于
    DIFFERENT_FROM = "different_from" # 不同于
    BELONGS_TO = "belongs_to"        # 属于
    KNOWS = "knows"                  # 认识
    WORKS_AT = "works_at"            # 工作在
    LIVES_AT = "lives_at"            # 居住在
    MENTIONED_IN = "mentioned_in"    # 被提及于


class EntityType(Enum):
    """实体类型枚举"""
    PERSON = "person"                # 人物
    ORGANIZATION = "organization"    # 组织
    LOCATION = "location"            # 地点
    TIME = "time"                    # 时间
    EVENT = "event"                  # 事件
    CONCEPT = "concept"              # 概念
    OBJECT = "object"                # 物品
    TASK = "task"                    # 任务
    GOAL = "goal"                    # 目标
    EMOTION = "emotion"              # 情感
    PREFERENCE = "preference"        # 偏好


@dataclass
class TemporalInfo:
    """时间信息数据类"""
    timestamp: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None  # 如 "daily", "weekly", "monthly"
    is_fuzzy: bool = False                    # 时间是否模糊
    fuzzy_description: Optional[str] = None   # 模糊时间描述，如 "上周", "去年"
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "is_recurring": self.is_recurring,
            "recurrence_pattern": self.recurrence_pattern,
            "is_fuzzy": self.is_fuzzy,
            "fuzzy_description": self.fuzzy_description
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "TemporalInfo":
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else None,
            start_time=datetime.fromisoformat(data["start_time"]) if data.get("start_time") else None,
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            is_recurring=data.get("is_recurring", False),
            recurrence_pattern=data.get("recurrence_pattern"),
            is_fuzzy=data.get("is_fuzzy", False),
            fuzzy_description=data.get("fuzzy_description")
        )


@dataclass
class Entity:
    """知识图谱实体"""
    id: str
    name: str
    type: EntityType
    aliases: List[str] = None
    properties: Dict[str, Any] = None
    temporal_info: Optional[TemporalInfo] = None
    source_memory_id: Optional[str] = None
    confidence: float = 1.0
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []
        if self.properties is None:
            self.properties = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "aliases": self.aliases,
            "properties": self.properties,
            "temporal_info": self.temporal_info.to_dict() if self.temporal_info else None,
            "source_memory_id": self.source_memory_id,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Entity":
        return cls(
            id=data["id"],
            name=data["name"],
            type=EntityType(data["type"]),
            aliases=data.get("aliases", []),
            properties=data.get("properties", {}),
            temporal_info=TemporalInfo.from_dict(data["temporal_info"]) if data.get("temporal_info") else None,
            source_memory_id=data.get("source_memory_id"),
            confidence=data.get("confidence", 1.0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        )


@dataclass
class Relation:
    """知识图谱关系"""
    id: str
    source_id: str
    target_id: str
    relation_type: RelationType
    properties: Dict[str, Any] = None
    temporal_info: Optional[TemporalInfo] = None
    source_memory_id: Optional[str] = None
    confidence: float = 1.0
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "properties": self.properties,
            "temporal_info": self.temporal_info.to_dict() if self.temporal_info else None,
            "source_memory_id": self.source_memory_id,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Relation":
        return cls(
            id=data["id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            relation_type=RelationType(data["relation_type"]),
            properties=data.get("properties", {}),
            temporal_info=TemporalInfo.from_dict(data["temporal_info"]) if data.get("temporal_info") else None,
            source_memory_id=data.get("source_memory_id"),
            confidence=data.get("confidence", 1.0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        )


class TemporalKG:
    """时序知识图谱"""
    
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relations: Dict[str, Relation] = {}
        self.entity_relations: Dict[str, Set[str]] = {}  # entity_id -> relation_ids
        self._counter = 0
    
    def _generate_id(self, prefix: str) -> str:
        """生成唯一ID"""
        self._counter += 1
        return f"{prefix}_{self._counter}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    def add_entity(
        self,
        name: str,
        entity_type: EntityType,
        aliases: Optional[List[str]] = None,
        properties: Optional[Dict] = None,
        temporal_info: Optional[TemporalInfo] = None,
        source_memory_id: Optional[str] = None,
        confidence: float = 1.0
    ) -> Entity:
        """
        添加实体到知识图谱
        
        Returns:
            Entity: 创建的实体
        """
        # 检查是否已存在相同名称的实体
        existing = self.find_entity_by_name(name)
        if existing:
            # 合并信息
            existing.aliases = list(set(existing.aliases + (aliases or [])))
            if properties:
                existing.properties.update(properties)
            if temporal_info and not existing.temporal_info:
                existing.temporal_info = temporal_info
            existing.confidence = max(existing.confidence, confidence)
            return existing
        
        entity = Entity(
            id=self._generate_id("ent"),
            name=name,
            type=entity_type,
            aliases=aliases or [],
            properties=properties or {},
            temporal_info=temporal_info,
            source_memory_id=source_memory_id,
            confidence=confidence
        )
        
        self.entities[entity.id] = entity
        self.entity_relations[entity.id] = set()
        
        logger.debug(f"Added entity: {name} ({entity_type.value})")
        return entity
    
    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        properties: Optional[Dict] = None,
        temporal_info: Optional[TemporalInfo] = None,
        source_memory_id: Optional[str] = None,
        confidence: float = 1.0
    ) -> Optional[Relation]:
        """
        添加关系到知识图谱
        
        Returns:
            Relation: 创建的关系，如果实体不存在则返回None
        """
        if source_id not in self.entities or target_id not in self.entities:
            logger.warning(f"Cannot add relation: entity not found")
            return None
        
        relation = Relation(
            id=self._generate_id("rel"),
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            properties=properties or {},
            temporal_info=temporal_info,
            source_memory_id=source_memory_id,
            confidence=confidence
        )
        
        self.relations[relation.id] = relation
        self.entity_relations[source_id].add(relation.id)
        self.entity_relations[target_id].add(relation.id)
        
        logger.debug(f"Added relation: {relation_type.value} from {source_id} to {target_id}")
        return relation
    
    def find_entity_by_name(self, name: str) -> Optional[Entity]:
        """通过名称查找实体"""
        name_lower = name.lower()
        for entity in self.entities.values():
            if entity.name.lower() == name_lower:
                return entity
            if any(alias.lower() == name_lower for alias in entity.aliases):
                return entity
        return None
    
    def find_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """通过类型查找实体"""
        return [e for e in self.entities.values() if e.type == entity_type]
    
    def get_entity_relations(self, entity_id: str) -> List[Relation]:
        """获取实体的所有关系"""
        if entity_id not in self.entity_relations:
            return []
        return [self.relations[rid] for rid in self.entity_relations[entity_id]]
    
    def get_related_entities(self, entity_id: str, relation_type: Optional[RelationType] = None) -> List[Tuple[Entity, Relation]]:
        """
        获取与实体相关的其他实体
        
        Returns:
            List[Tuple[Entity, Relation]]: (相关实体, 关系)列表
        """
        relations = self.get_entity_relations(entity_id)
        results = []
        
        for rel in relations:
            if relation_type and rel.relation_type != relation_type:
                continue
            
            if rel.source_id == entity_id:
                related_entity = self.entities.get(rel.target_id)
            else:
                related_entity = self.entities.get(rel.source_id)
            
            if related_entity:
                results.append((related_entity, rel))
        
        return results
    
    def extract_temporal_info(self, text: str) -> TemporalInfo:
        """
        从文本中提取时间信息
        
        这是一个简单实现，实际应用中可能需要更复杂的NLP
        """
        temporal_info = TemporalInfo()
        text_lower = text.lower()
        
        # 检测循环模式
        recurring_patterns = {
            "每天": "daily",
            "每日": "daily",
            "每周": "weekly",
            "每月": "monthly",
            "每年": "yearly",
            "every day": "daily",
            "daily": "daily",
            "every week": "weekly",
            "weekly": "weekly",
            "every month": "monthly",
            "monthly": "monthly"
        }
        
        for pattern, recurrence in recurring_patterns.items():
            if pattern in text_lower:
                temporal_info.is_recurring = True
                temporal_info.recurrence_pattern = recurrence
                break
        
        # 检测具体时间
        # ISO格式日期时间
        iso_pattern = r'\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?'
        iso_matches = re.findall(iso_pattern, text)
        
        if iso_matches:
            try:
                date_str = iso_matches[0]
                if 'T' in date_str:
                    temporal_info.timestamp = datetime.fromisoformat(date_str)
                else:
                    temporal_info.timestamp = datetime.strptime(date_str, "%Y-%m-%d")
            except:
                pass
        
        # 模糊时间
        fuzzy_patterns = {
            "昨天": "yesterday",
            "今天": "today",
            "明天": "tomorrow",
            "上周": "last week",
            "下周": "next week",
            "上个月": "last month",
            "下个月": "next month",
            "去年": "last year",
            "明年": "next year"
        }
        
        for pattern, description in fuzzy_patterns.items():
            if pattern in text:
                temporal_info.is_fuzzy = True
                temporal_info.fuzzy_description = description
                break
        
        return temporal_info
    
    def build_from_memory(self, memory_id: str, content: str, entities_data: List[Dict]) -> List[Entity]:
        """
        从记忆内容构建知识图谱
        
        Args:
            memory_id: 记忆ID
            content: 记忆内容
            entities_data: 实体数据列表 [{"name": "...", "type": "..."}]
            
        Returns:
            List[Entity]: 创建的实体列表
        """
        created_entities = []
        
        # 提取时间信息
        temporal_info = self.extract_temporal_info(content)
        
        # 创建实体
        for ent_data in entities_data:
            entity_type = EntityType(ent_data.get("type", "concept").lower())
            entity = self.add_entity(
                name=ent_data["name"],
                entity_type=entity_type,
                aliases=ent_data.get("aliases", []),
                properties=ent_data.get("properties", {}),
                temporal_info=temporal_info,
                source_memory_id=memory_id,
                confidence=ent_data.get("confidence", 0.8)
            )
            created_entities.append(entity)
        
        # 创建实体间的关系（简单实现：相邻实体间创建相关关系）
        for i in range(len(created_entities) - 1):
            self.add_relation(
                source_id=created_entities[i].id,
                target_id=created_entities[i + 1].id,
                relation_type=RelationType.RELATED_TO,
                source_memory_id=memory_id
            )
        
        return created_entities
    
    def query_by_time_range(
        self,
        start: datetime,
        end: datetime,
        entity_type: Optional[EntityType] = None
    ) -> List[Entity]:
        """
        按时间范围查询实体
        
        Args:
            start: 开始时间
            end: 结束时间
            entity_type: 可选的实体类型过滤
            
        Returns:
            List[Entity]: 符合条件的实体
        """
        results = []
        
        for entity in self.entities.values():
            if entity_type and entity.type != entity_type:
                continue
            
            if not entity.temporal_info:
                continue
            
            ti = entity.temporal_info
            
            # 检查时间重叠
            if ti.timestamp and start <= ti.timestamp <= end:
                results.append(entity)
            elif ti.start_time and ti.end_time:
                if not (ti.end_time < start or ti.start_time > end):
                    results.append(entity)
        
        return results
    
    def find_temporal_relations(self, entity_id: str) -> List[Relation]:
        """
        查找实体的时序关系（之前/之后发生）
        """
        entity = self.entities.get(entity_id)
        if not entity or not entity.temporal_info:
            return []
        
        temporal_relations = []
        all_relations = self.get_entity_relations(entity_id)
        
        for rel in all_relations:
            if rel.relation_type in [RelationType.HAPPENED_BEFORE, RelationType.HAPPENED_AFTER]:
                temporal_relations.append(rel)
            elif rel.temporal_info:
                # 检查关系的时间信息
                temporal_relations.append(rel)
        
        return temporal_relations
    
    def infer_temporal_order(self, entity1_id: str, entity2_id: str) -> Optional[str]:
        """
        推断两个实体的时间顺序
        
        Returns:
            Optional[str]: "before", "after", "concurrent" 或 None
        """
        ent1 = self.entities.get(entity1_id)
        ent2 = self.entities.get(entity2_id)
        
        if not ent1 or not ent2:
            return None
        
        if not ent1.temporal_info or not ent2.temporal_info:
            return None
        
        ti1 = ent1.temporal_info
        ti2 = ent2.temporal_info
        
        # 使用具体时间戳
        if ti1.timestamp and ti2.timestamp:
            if ti1.timestamp < ti2.timestamp:
                return "before"
            elif ti1.timestamp > ti2.timestamp:
                return "after"
            else:
                return "concurrent"
        
        # 使用时间段
        if ti1.end_time and ti2.start_time:
            if ti1.end_time <= ti2.start_time:
                return "before"
        
        if ti2.end_time and ti1.start_time:
            if ti2.end_time <= ti1.start_time:
                return "after"
        
        return None
    
    def get_timeline(self, entity_type: Optional[EntityType] = None, limit: int = 100) -> List[Entity]:
        """
        获取按时间排序的实体时间线
        
        Returns:
            List[Entity]: 按时间排序的实体
        """
        entities_with_time = []
        
        for entity in self.entities.values():
            if entity_type and entity.type != entity_type:
                continue
            
            if entity.temporal_info and entity.temporal_info.timestamp:
                entities_with_time.append((entity, entity.temporal_info.timestamp))
        
        # 按时间排序
        entities_with_time.sort(key=lambda x: x[1])
        
        return [e[0] for e in entities_with_time[:limit]]
    
    def to_dict(self) -> Dict:
        """导出为字典"""
        return {
            "entities": {k: v.to_dict() for k, v in self.entities.items()},
            "relations": {k: v.to_dict() for k, v in self.relations.items()},
            "entity_relations": {k: list(v) for k, v in self.entity_relations.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "TemporalKG":
        """从字典导入"""
        kg = cls()
        
        for ent_data in data.get("entities", {}).values():
            entity = Entity.from_dict(ent_data)
            kg.entities[entity.id] = entity
        
        for rel_data in data.get("relations", {}).values():
            relation = Relation.from_dict(rel_data)
            kg.relations[relation.id] = relation
        
        for ent_id, rel_ids in data.get("entity_relations", {}).items():
            kg.entity_relations[ent_id] = set(rel_ids)
        
        return kg
    
    def to_json(self) -> str:
        """导出为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "TemporalKG":
        """从JSON字符串导入"""
        data = json.loads(json_str)
        return cls.from_dict(data)


# 便捷函数

def create_temporal_kg() -> TemporalKG:
    """创建新的时序知识图谱"""
    return TemporalKG()


def extract_entities_from_text(text: str) -> List[Dict]:
    """
    从文本中提取实体（简化版）
    
    实际应用中应该使用NLP库如spaCy或调用LLM
    """
    # 这是一个占位实现
    entities = []
    
    # 简单的人名检测（首字母大写的单词）
    import re
    potential_names = re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', text)
    for name in potential_names:
        entities.append({
            "name": name,
            "type": "person",
            "confidence": 0.6
        })
    
    return entities