"""
Scoring Module - Composite Memory Scoring
评分模块 - 记忆复合评分算法
"""
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class DecayFunction(Enum):
    """时间衰减函数类型"""
    EXPONENTIAL = "exponential"      # 指数衰减
    LOGARITHMIC = "logarithmic"      # 对数衰减
    LINEAR = "linear"                # 线性衰减
    STEP = "step"                    # 阶梯衰减


@dataclass
class ScoringFactors:
    """评分子模型"""
    importance: float = 3.0          # 重要性 (1-5)
    recency: float = 1.0             # 时效性 (0-1)
    frequency: float = 0.0           # 访问频率 (0-1)
    relevance: float = 1.0           # 查询相关性 (0-1)
    category_boost: float = 1.0      # 分类权重加成
    user_interaction: float = 1.0    # 用户交互分数 (0-1)
    connection_strength: float = 0.0 # 知识图谱连接强度 (0-1)
    
    def to_dict(self) -> Dict:
        return {
            "importance": self.importance,
            "recency": self.recency,
            "frequency": self.frequency,
            "relevance": self.relevance,
            "category_boost": self.category_boost,
            "user_interaction": self.user_interaction,
            "connection_strength": self.connection_strength
        }


class MemoryScorer:
    """记忆评分器"""
    
    # 默认权重配置
    DEFAULT_WEIGHTS = {
        "importance": 0.25,
        "recency": 0.20,
        "frequency": 0.15,
        "relevance": 0.20,
        "category_boost": 0.10,
        "user_interaction": 0.10,
        "connection_strength": 0.00  # 可选，默认不参与基础评分
    }
    
    # 时间衰减配置
    DECAY_HALF_LIFE_DAYS = {
        "critical": 90,    # 关键记忆：90天半衰期
        "high": 60,        # 重要记忆：60天
        "medium": 30,      # 一般记忆：30天
        "low": 14,         # 次要记忆：14天
        "trivial": 7       # 琐碎记忆：7天
    }
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        初始化评分器
        
        Args:
            weights: 自定义权重配置，None则使用默认权重
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self._validate_weights()
    
    def _validate_weights(self):
        """验证权重配置"""
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.001:
            # 归一化权重
            for key in self.weights:
                self.weights[key] /= total
    
    def calculate_score(self, factors: ScoringFactors) -> float:
        """
        计算综合记忆分数
        
        Args:
            factors: 评分子模型
            
        Returns:
            float: 综合分数 (0-1)
        """
        # 归一化重要性 (1-5 -> 0.2-1.0)
        normalized_importance = factors.importance / 5.0
        
        # 计算加权分数
        score = (
            normalized_importance * self.weights["importance"] +
            factors.recency * self.weights["recency"] +
            factors.frequency * self.weights["frequency"] +
            factors.relevance * self.weights["relevance"] +
            min(factors.category_boost, 2.0) / 2.0 * self.weights["category_boost"] +
            factors.user_interaction * self.weights["user_interaction"] +
            factors.connection_strength * self.weights.get("connection_strength", 0.0)
        )
        
        # 应用sigmoid函数使分数分布更合理
        score = self._sigmoid_normalize(score)
        
        return round(min(max(score, 0.0), 1.0), 4)
    
    def _sigmoid_normalize(self, x: float, steepness: float = 4.0) -> float:
        """使用sigmoid函数归一化分数"""
        # 将0-1映射到更合理的分布
        return 1 / (1 + math.exp(-steepness * (x - 0.5)))
    
    def calculate_recency_score(
        self, 
        created_at: datetime,
        accessed_at: Optional[datetime] = None,
        importance_level: str = "medium",
        decay_function: DecayFunction = DecayFunction.EXPONENTIAL
    ) -> float:
        """
        计算时效性分数
        
        Args:
            created_at: 创建时间
            accessed_at: 最后访问时间
            importance_level: 重要性级别
            decay_function: 衰减函数类型
            
        Returns:
            float: 时效性分数 (0-1)
        """
        now = datetime.utcnow()
        
        # 使用最近交互时间（访问优先于创建）
        reference_time = accessed_at or created_at
        days_diff = (now - reference_time).days
        
        # 获取半衰期
        half_life = self.DECAY_HALF_LIFE_DAYS.get(importance_level.lower(), 30)
        
        if decay_function == DecayFunction.EXPONENTIAL:
            # 指数衰减: score = e^(-λt), λ = ln(2)/half_life
            decay_rate = math.log(2) / half_life
            score = math.exp(-decay_rate * days_diff)
            
        elif decay_function == DecayFunction.LOGARITHMIC:
            # 对数衰减: score = 1 / (1 + log(1 + t/half_life))
            score = 1 / (1 + math.log1p(days_diff / half_life))
            
        elif decay_function == DecayFunction.LINEAR:
            # 线性衰减
            score = max(0, 1 - (days_diff / (half_life * 2)))
            
        elif decay_function == DecayFunction.STEP:
            # 阶梯衰减
            if days_diff <= half_life / 2:
                score = 1.0
            elif days_diff <= half_life:
                score = 0.8
            elif days_diff <= half_life * 2:
                score = 0.5
            elif days_diff <= half_life * 4:
                score = 0.3
            else:
                score = 0.1
        else:
            score = 0.5
        
        # 如果有访问记录，给予加成
        if accessed_at and accessed_at > created_at:
            access_bonus = 0.1 * math.exp(-(now - accessed_at).days / 7)
            score = min(1.0, score + access_bonus)
        
        return round(score, 4)
    
    def calculate_frequency_score(self, access_count: int, access_history: List[datetime]) -> float:
        """
        计算访问频率分数
        
        Args:
            access_count: 访问次数
            access_history: 访问历史记录
            
        Returns:
            float: 频率分数 (0-1)
        """
        if access_count == 0:
            return 0.0
        
        # 基础分数：对数增长
        base_score = math.log1p(access_count) / math.log1p(100)  # 归一化到100次
        
        # 时间集中度加成（近期频繁访问）
        if len(access_history) >= 3:
            now = datetime.utcnow()
            recent_accesses = sum(
                1 for t in access_history 
                if (now - t).days <= 7
            )
            recency_bonus = min(0.3, recent_accesses * 0.1)
        else:
            recency_bonus = 0
        
        score = min(1.0, base_score + recency_bonus)
        return round(score, 4)
    
    def calculate_relevance_score(
        self, 
        query: str,
        memory_content: str,
        memory_tags: List[str],
        vector_similarity: float
    ) -> float:
        """
        计算查询相关性分数
        
        Args:
            query: 查询字符串
            memory_content: 记忆内容
            memory_tags: 记忆标签
            vector_similarity: 向量相似度分数
            
        Returns:
            float: 相关性分数 (0-1)
        """
        query_lower = query.lower()
        content_lower = memory_content.lower()
        
        scores = []
        
        # 向量相似度 (50% 权重)
        scores.append(vector_similarity * 0.5)
        
        # 关键词匹配 (30% 权重)
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        if query_words:
            word_overlap = len(query_words & content_words) / len(query_words)
            scores.append(word_overlap * 0.3)
        
        # 标签匹配 (20% 权重)
        if memory_tags:
            tag_matches = sum(1 for tag in memory_tags if tag.lower() in query_lower)
            tag_score = min(1.0, tag_matches / max(len(query_words), 1))
            scores.append(tag_score * 0.2)
        
        return round(sum(scores), 4)
    
    def calculate_category_boost(self, category: str, user_preferences: Optional[Dict] = None) -> float:
        """
        计算分类权重加成
        
        Args:
            category: 记忆分类
            user_preferences: 用户分类偏好
            
        Returns:
            float: 分类加成 (0.5-2.0)
        """
        # 基础分类权重
        base_weights = {
            "fact": 1.0,
            "preference": 1.3,
            "event": 1.1,
            "person": 1.4,
            "task": 1.5,
            "goal": 1.4,
            "emotion": 0.9,
            "knowledge": 1.2,
            "relationship": 1.3,
            "habit": 0.8,
            "other": 0.7
        }
        
        base_weight = base_weights.get(category.lower(), 1.0)
        
        # 应用用户偏好
        if user_preferences and category in user_preferences:
            preference_boost = user_preferences[category]
            base_weight *= (1 + preference_boost)
        
        return round(min(max(base_weight, 0.5), 2.0), 2)
    
    def calculate_user_interaction_score(
        self,
        is_favorite: bool = False,
        is_pinned: bool = False,
        user_rating: Optional[int] = None,
        manual_priority: Optional[int] = None
    ) -> float:
        """
        计算用户交互分数
        
        Args:
            is_favorite: 是否收藏
            is_pinned: 是否置顶
            user_rating: 用户评分 (1-5)
            manual_priority: 手动优先级 (1-5)
            
        Returns:
            float: 交互分数 (0-1)
        """
        score = 0.0
        
        if is_pinned:
            score += 0.4
        
        if is_favorite:
            score += 0.25
        
        if user_rating:
            score += (user_rating / 5.0) * 0.2
        
        if manual_priority:
            score += (manual_priority / 5.0) * 0.15
        
        return round(min(score, 1.0), 4)
    
    def get_score_breakdown(self, factors: ScoringFactors) -> Dict[str, float]:
        """
        获取分数详细分解
        
        Returns:
            Dict: 各项分数明细
        """
        normalized_importance = factors.importance / 5.0
        
        breakdown = {
            "importance": {
                "raw_value": factors.importance,
                "normalized": normalized_importance,
                "weighted": normalized_importance * self.weights["importance"],
                "weight": self.weights["importance"]
            },
            "recency": {
                "raw_value": factors.recency,
                "weighted": factors.recency * self.weights["recency"],
                "weight": self.weights["recency"]
            },
            "frequency": {
                "raw_value": factors.frequency,
                "weighted": factors.frequency * self.weights["frequency"],
                "weight": self.weights["frequency"]
            },
            "relevance": {
                "raw_value": factors.relevance,
                "weighted": factors.relevance * self.weights["relevance"],
                "weight": self.weights["relevance"]
            },
            "category_boost": {
                "raw_value": factors.category_boost,
                "normalized": min(factors.category_boost, 2.0) / 2.0,
                "weighted": min(factors.category_boost, 2.0) / 2.0 * self.weights["category_boost"],
                "weight": self.weights["category_boost"]
            },
            "user_interaction": {
                "raw_value": factors.user_interaction,
                "weighted": factors.user_interaction * self.weights["user_interaction"],
                "weight": self.weights["user_interaction"]
            }
        }
        
        if "connection_strength" in self.weights:
            breakdown["connection_strength"] = {
                "raw_value": factors.connection_strength,
                "weighted": factors.connection_strength * self.weights["connection_strength"],
                "weight": self.weights["connection_strength"]
            }
        
        breakdown["final_score"] = self.calculate_score(factors)
        
        return breakdown


# 便捷函数

def calculate_memory_score(factors: ScoringFactors, weights: Optional[Dict[str, float]] = None) -> float:
    """便捷函数：计算记忆分数"""
    scorer = MemoryScorer(weights=weights)
    return scorer.calculate_score(factors)


def calculate_recency(
    created_at: datetime,
    accessed_at: Optional[datetime] = None,
    importance_level: str = "medium"
) -> float:
    """便捷函数：计算时效性分数"""
    scorer = MemoryScorer()
    return scorer.calculate_recency_score(created_at, accessed_at, importance_level)


def calculate_relevance(
    query: str,
    memory_content: str,
    memory_tags: List[str],
    vector_similarity: float
) -> float:
    """便捷函数：计算相关性分数"""
    scorer = MemoryScorer()
    return scorer.calculate_relevance_score(query, memory_content, memory_tags, vector_similarity)


def get_default_weights() -> Dict[str, float]:
    """获取默认权重配置"""
    return MemoryScorer.DEFAULT_WEIGHTS.copy()


def create_custom_scorer(
    importance_weight: float = 0.25,
    recency_weight: float = 0.20,
    frequency_weight: float = 0.15,
    relevance_weight: float = 0.20,
    category_weight: float = 0.10,
    interaction_weight: float = 0.10
) -> MemoryScorer:
    """
    创建自定义权重评分器
    
    所有权重会自动归一化到总和为1
    """
    weights = {
        "importance": importance_weight,
        "recency": recency_weight,
        "frequency": frequency_weight,
        "relevance": relevance_weight,
        "category_boost": category_weight,
        "user_interaction": interaction_weight
    }
    return MemoryScorer(weights=weights)