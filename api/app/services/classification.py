"""
Classification Module - LLM-based Memory Classification
记忆分类模块 - 基于LLM的记忆自动分类
"""
import os
import json
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from enum import Enum
import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class MemoryCategory(str, Enum):
    """记忆分类枚举"""
    FACT = "fact"                    # 事实性记忆
    PREFERENCE = "preference"        # 偏好/喜好
    EVENT = "event"                  # 事件/经历
    PERSON = "person"                # 人物信息
    TASK = "task"                    # 任务/待办
    GOAL = "goal"                    # 目标/计划
    EMOTION = "emotion"              # 情感/感受
    KNOWLEDGE = "knowledge"          # 知识/技能
    RELATIONSHIP = "relationship"    # 关系/社交
    HABIT = "habit"                  # 习惯/惯例
    OTHER = "other"                  # 其他

class MemoryImportance(int, Enum):
    """记忆重要性等级"""
    CRITICAL = 5     # 关键记忆
    HIGH = 4         # 重要记忆
    MEDIUM = 3       # 一般记忆
    LOW = 2          # 次要记忆
    TRIVIAL = 1      # 琐碎记忆

class ClassificationResult(BaseModel):
    """分类结果模型"""
    category: MemoryCategory = Field(..., description="记忆分类")
    subcategory: Optional[str] = Field(None, description="子分类")
    importance: MemoryImportance = Field(default=MemoryImportance.MEDIUM, description="重要性等级")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="分类置信度")
    summary: Optional[str] = Field(None, description="记忆摘要")
    entities: List[Dict] = Field(default_factory=list, description="提取的实体")
    temporal_info: Optional[Dict] = Field(None, description="时间信息")
    reasoning: Optional[str] = Field(None, description="分类推理")

class LLMClassifier:
    """基于LLM的记忆分类器"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        self.timeout = 30.0
        
    async def classify(self, content: str, context: Optional[Dict] = None) -> ClassificationResult:
        """
        对记忆内容进行分类
        
        Args:
            content: 记忆内容
            context: 可选的上下文信息
            
        Returns:
            ClassificationResult: 分类结果
        """
        try:
            prompt = self._build_classification_prompt(content, context)
            response = await self._call_llm(prompt)
            result = self._parse_response(response, content)
            return result
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            # 返回默认分类
            return ClassificationResult(
                category=MemoryCategory.OTHER,
                importance=MemoryImportance.MEDIUM,
                confidence=0.0,
                tags=[],
                summary=content[:100] + "..." if len(content) > 100 else content
            )
    
    def _build_classification_prompt(self, content: str, context: Optional[Dict] = None) -> str:
        """构建分类提示词"""
        categories = ", ".join([c.value for c in MemoryCategory])
        
        prompt = f"""请分析以下记忆内容，提供结构化分类信息。

记忆内容：
"""{content}"""

请按以下JSON格式返回结果：
{{
    "category": "从以下选项中选择: {categories}",
    "subcategory": "更具体的子分类（可选）",
    "importance": "1-5的数字，5为最关键",
    "tags": ["相关标签1", "标签2", "标签3"],
    "summary": "记忆的简短摘要（30字以内）",
    "entities": [
        {{"name": "实体名称", "type": "实体类型（人名/地点/组织/时间/其他）"}}
    ],
    "temporal_info": {{
        "when": "提及的时间信息",
        "is_future": false,
        "is_recurring": false
    }},
    "reasoning": "分类理由（简要说明）"
}}

只返回JSON，不要其他内容。"""

        if context:
            prompt += f"\n\n上下文信息：{json.dumps(context, ensure_ascii=False)}"
        
        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """调用LLM API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一个专业的记忆分类助手。请准确分析记忆内容并提供结构化分类。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    def _parse_response(self, response: str, original_content: str) -> ClassificationResult:
        """解析LLM响应"""
        try:
            # 清理响应中的 markdown 代码块
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            data = json.loads(response)
            
            # 映射分类
            category = MemoryCategory(data.get("category", "other").lower())
            
            # 映射重要性
            importance_val = data.get("importance", 3)
            if isinstance(importance_val, str):
                importance_val = int(importance_val)
            importance = MemoryImportance(min(max(importance_val, 1), 5))
            
            return ClassificationResult(
                category=category,
                subcategory=data.get("subcategory"),
                importance=importance,
                tags=data.get("tags", []),
                confidence=0.85,  # LLM分类默认置信度
                summary=data.get("summary", original_content[:100]),
                entities=data.get("entities", []),
                temporal_info=data.get("temporal_info"),
                reasoning=data.get("reasoning")
            )
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}, response: {response[:200]}")
            # 回退到默认解析
            return self._fallback_parse(response, original_content)
    
    def _fallback_parse(self, response: str, original_content: str) -> ClassificationResult:
        """备用解析逻辑"""
        response_lower = response.lower()
        
        # 简单关键词匹配分类
        category = MemoryCategory.OTHER
        if any(kw in response_lower for kw in ["喜好", "喜欢", "讨厌", "偏好", "prefer"]):
            category = MemoryCategory.PREFERENCE
        elif any(kw in response_lower for kw in ["生日", "事件", "去了", "参加", "event"]):
            category = MemoryCategory.EVENT
        elif any(kw in response_lower for kw in ["任务", "待办", "需要完成", "task", "todo"]):
            category = MemoryCategory.TASK
        elif any(kw in response_lower for kw in ["目标", "计划", "想要", "goal", "plan"]):
            category = MemoryCategory.GOAL
        elif any(kw in response_lower for kw in ["感觉", "情绪", "开心", "难过", "emotion", "feel"]):
            category = MemoryCategory.EMOTION
        elif any(kw in response_lower for kw in ["知道", "了解", "知识", "knowledge", "know"]):
            category = MemoryCategory.KNOWLEDGE
        elif any(kw in response_lower for kw in ["朋友", "家人", "同事", "relationship", "friend"]):
            category = MemoryCategory.RELATIONSHIP
        
        return ClassificationResult(
            category=category,
            importance=MemoryImportance.MEDIUM,
            confidence=0.5,
            tags=[],
            summary=original_content[:100] + "..." if len(original_content) > 100 else original_content
        )


class RuleBasedClassifier:
    """基于规则的记忆分类器（用于快速分类或离线场景）"""
    
    # 分类关键词映射
    CATEGORY_KEYWORDS = {
        MemoryCategory.PREFERENCE: ["喜欢", "讨厌", "偏好", "最爱", "不喜欢", "感兴趣", "prefer", "like", "hate", "favorite", "interested"],
        MemoryCategory.EVENT: ["去了", "参加", "发生", "到访", "访问", "旅行", "visit", "attend", "happened", "trip", "travel"],
        MemoryCategory.TASK: ["任务", "待办", "需要", "必须", "完成", "提醒", "task", "todo", "need to", "must", "remind"],
        MemoryCategory.GOAL: ["目标", "计划", "想要", "希望", "打算", "goal", "plan", "want", "hope", "aim"],
        MemoryCategory.EMOTION: ["感觉", "觉得", "开心", "难过", "兴奋", "失望", "feel", "happy", "sad", "excited", "disappointed"],
        MemoryCategory.PERSON: ["姓名", "年龄", "职业", "电话", "邮箱", "name", "age", "job", "phone", "email"],
        MemoryCategory.KNOWLEDGE: ["知道", "了解", "学习", "知识", "技能", "know", "learn", "knowledge", "skill"],
        MemoryCategory.RELATIONSHIP: ["朋友", "家人", "同事", "关系", "friend", "family", "colleague", "relationship"],
        MemoryCategory.HABIT: ["习惯", "每天", "经常", "总是", "habit", "everyday", "often", "always"],
    }
    
    def classify(self, content: str) -> ClassificationResult:
        """基于规则的快速分类"""
        scores = {cat: 0 for cat in MemoryCategory}
        content_lower = content.lower()
        
        # 关键词匹配
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content_lower:
                    scores[category] += 1
        
        # 选择最高分的分类
        best_category = max(scores, key=scores.get)
        if scores[best_category] == 0:
            best_category = MemoryCategory.OTHER
        
        # 基于内容长度和关键词密度确定重要性
        importance = self._estimate_importance(content, scores[best_category])
        
        return ClassificationResult(
            category=best_category,
            importance=importance,
            confidence=min(0.6, 0.3 + scores[best_category] * 0.1),
            tags=list(set([kw for cat, kws in self.CATEGORY_KEYWORDS.items() 
                          for kw in kws if kw in content_lower][:5])),
            summary=content[:80] + "..." if len(content) > 80 else content
        )
    
    def _estimate_importance(self, content: str, keyword_matches: int) -> MemoryImportance:
        """估计记忆重要性"""
        score = keyword_matches * 2
        
        # 基于内容特征加分
        if any(indicator in content for indicator in ["生日", " anniversary", "重要", "critical", " urgently"]):
            score += 3
        if len(content) > 200:
            score += 1
        if "?" in content or "？" in content:
            score += 1  # 问题通常较重要
            
        if score >= 7:
            return MemoryImportance.CRITICAL
        elif score >= 5:
            return MemoryImportance.HIGH
        elif score >= 3:
            return MemoryImportance.MEDIUM
        elif score >= 1:
            return MemoryImportance.LOW
        else:
            return MemoryImportance.TRIVIAL


class HybridClassifier:
    """混合分类器 - 结合规则和LLM分类"""
    
    def __init__(self, api_key: Optional[str] = None, use_llm: bool = True):
        self.rule_classifier = RuleBasedClassifier()
        self.llm_classifier = LLMClassifier(api_key) if use_llm else None
        self.use_llm = use_llm
    
    async def classify(self, content: str, context: Optional[Dict] = None, prefer_speed: bool = False) -> ClassificationResult:
        """
        混合分类
        
        Args:
            content: 记忆内容
            context: 上下文
            prefer_speed: 是否优先速度（使用规则分类）
        """
        if prefer_speed or not self.use_llm or not self.llm_classifier:
            return self.rule_classifier.classify(content)
        
        try:
            # 先进行规则分类作为基础
            rule_result = self.rule_classifier.classify(content)
            
            # 如果规则分类置信度足够高，直接返回
            if rule_result.confidence >= 0.7 and rule_result.category != MemoryCategory.OTHER:
                return rule_result
            
            # 否则使用LLM分类
            llm_result = await self.llm_classifier.classify(content, context)
            
            # 如果LLM分类置信度低，结合规则结果
            if llm_result.confidence < 0.5:
                llm_result.tags = list(set(llm_result.tags + rule_result.tags))
                if llm_result.category == MemoryCategory.OTHER:
                    llm_result.category = rule_result.category
            
            return llm_result
            
        except Exception as e:
            logger.error(f"Hybrid classification failed: {e}")
            return self.rule_classifier.classify(content)


# 便捷函数
async def classify_memory(content: str, api_key: Optional[str] = None, context: Optional[Dict] = None) -> ClassificationResult:
    """便捷的分类函数"""
    classifier = HybridClassifier(api_key=api_key, use_llm=bool(api_key or os.getenv("OPENAI_API_KEY")))
    return await classifier.classify(content, context)


def quick_classify(content: str) -> ClassificationResult:
    """快速分类（仅使用规则）"""
    classifier = RuleBasedClassifier()
    return classifier.classify(content)