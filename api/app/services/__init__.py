"""
MemoryX AI Services Module
"""
from app.services.classification import (
    classify_memory,
    quick_classify,
    ClassificationResult,
    MemoryCategory,
    MemoryImportance,
    LLMClassifier,
    RuleBasedClassifier,
    HybridClassifier
)

from app.services.scoring import (
    calculate_memory_score,
    calculate_recency,
    calculate_relevance,
    ScoringFactors,
    MemoryScorer,
    DecayFunction,
    get_default_weights,
    create_custom_scorer
)

from app.services.memory_service import (
    MemoryService,
    Memory,
    SearchResult,
    EmbeddingService,
    get_memory_service,
    init_memory_service,
    COLLECTION_NAME,
    VECTOR_SIZE
)

from app.services.temporal_kg import (
    TemporalKG,
    Entity,
    Relation,
    EntityType,
    RelationType,
    TemporalInfo,
    create_temporal_kg,
    extract_entities_from_text
)

__all__ = [
    # Classification
    "classify_memory",
    "quick_classify",
    "ClassificationResult",
    "MemoryCategory",
    "MemoryImportance",
    "LLMClassifier",
    "RuleBasedClassifier",
    "HybridClassifier",
    
    # Scoring
    "calculate_memory_score",
    "calculate_recency",
    "calculate_relevance",
    "ScoringFactors",
    "MemoryScorer",
    "DecayFunction",
    "get_default_weights",
    "create_custom_scorer",
    
    # Memory Service
    "MemoryService",
    "Memory",
    "SearchResult",
    "EmbeddingService",
    "get_memory_service",
    "init_memory_service",
    "COLLECTION_NAME",
    "VECTOR_SIZE",
    
    # Temporal KG
    "TemporalKG",
    "Entity",
    "Relation",
    "EntityType",
    "RelationType",
    "TemporalInfo",
    "create_temporal_kg",
    "extract_entities_from_text"
]