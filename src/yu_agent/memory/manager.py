"""记忆管理器 - 记忆核心层的统一管理接口"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import uuid
import logging

"""
记忆管理器模块

本模块提供 MemoryManager 类，作为记忆子系统的统一入口。它负责管理
不同类型的记忆（working, episodic, semantic, perceptual）的生命周期，协调
记忆的添加、检索、更新、删除、遗忘以及从短期到长期的整合。

设计原则：
- 将具体的存储和检索实现下放到各记忆类型（WorkingMemory 等），Manager 只做协调。
- 提供轻量的自动分类与重要性估算，便于上层在不关心底层实现的情况下使用。

注意：各记忆类型需实现统一接口（如 add/retrieve/update/remove/get_all/forget/clear/get_stats/has_memory）。
"""

from .base import MemoryItem, MemoryConfig
from .types.working import WorkingMemory
from .types.episodic import EpisodicMemory
from .types.semantic import SemanticMemory
from .types.perceptual import PerceptualMemory

# 统一的日志记录器，模块内使用 logger.debug/info/warning 来输出运行状态
logger = logging.getLogger(__name__)


class MemoryManager:
    """记忆管理器 - 统一的记忆操作接口

    主要功能：
    - 管理不同类型记忆的实例（短时、情景、语义、感知）
    - 提供记忆的添加、检索、更新与删除接口
    - 执行遗忘策略与记忆整合（例如将重要短期记忆转入长期记忆）
    - 提供统计信息与清理方法

    参数说明：
    - config: MemoryConfig，包含容量、衰减等全局配置
    - user_id: 关联的用户标识，便于按用户隔离记忆
    - enable_*: 控制是否启用对应类型的记忆
    """

    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        user_id: str = "default_user",
        enable_working: bool = True,
        enable_episodic: bool = True,
        enable_semantic: bool = True,
        enable_perceptual: bool = False,
    ):
        # 使用传入的配置或默认配置
        self.config = config or MemoryConfig()
        self.user_id = user_id

        # 记忆类型字典，键为类型名，值为具体记忆实例
        # 将具体实现委托给相应类（实现统一接口）
        self.memory_types: Dict[str, Any] = {}

        if enable_working:
            # 短期/工作记忆，适合暂时性信息
            self.memory_types["working"] = WorkingMemory(self.config)

        if enable_episodic:
            # 情景记忆，记录事件与时间线相关的内容
            self.memory_types["episodic"] = EpisodicMemory(self.config)

        if enable_semantic:
            # 语义记忆，用于存放概念、规则、知识点
            self.memory_types["semantic"] = SemanticMemory(self.config)

        if enable_perceptual:
            # 感知记忆（可选），用于存放感官或外部观察到的信息
            self.memory_types["perceptual"] = PerceptualMemory(self.config) # 实例化

        logger.info(
            "MemoryManager初始化完成，启用记忆类型: %s", list(self.memory_types.keys())
        )

    def add_memory(
        self,
        content: str,
        memory_type: str = "working",
        importance: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        auto_classify: bool = True,
    ) -> str:
        """添加一条记忆并返回生成的记忆ID

        步骤：
        1. 若启用自动分类，则根据内容/元数据决定放入哪个记忆类型
        2. 若未提供重要性评分，使用内置启发式函数估算
        3. 封装为 MemoryItem 并调用对应记忆实例的 add 方法

        返回值：新记忆项的 id（字符串）
        抛错：当指定的 memory_type 不被支持时抛出 ValueError
        """

        # 自动分类记忆类型（如将描述事件的文本分类到 episodic）
        if auto_classify:
            memory_type = self._classify_memory_type(content, metadata)

        # 自动估算重要性（importance 取值范围 0.0 - 1.0）
        if importance is None:
            importance = self._calculate_importance(content, metadata)

        # 构造 MemoryItem（id 使用 uuid4 保证唯一性）
        memory_item = MemoryItem(
            id=str(uuid.uuid4()), # 生成唯一 ID，这个uuid4 是随机生成的，适合分布式环境
            content=content,
            memory_type=memory_type,
            user_id=self.user_id,
            timestamp=datetime.now(),
            importance=importance,
            metadata=metadata or {},
        )

        # 将记忆交给对应类型的实例处理（持久化/索引/缓存等细节由子类实现）
        if memory_type in self.memory_types:
            memory_id = self.memory_types[memory_type].add(memory_item)
            logger.debug("添加记忆到 %s: %s", memory_type, memory_id)
            return memory_id
        else:
            # 非受支持的类型应当被尽早发现并反馈
            raise ValueError(f"不支持的记忆类型: {memory_type}")

    def retrieve_memories(
        self,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 10,
        min_importance: float = 0.0,
        time_range: Optional[tuple] = None,
    ) -> List[MemoryItem]:
        """检索记忆集合，按重要性排序后返回前 N 项

        说明：
        - 默认会在所有已启用的记忆类型中检索。
        - 为了避免在每个类型中都返回过多结果，采用按类型分配 limit 的简单策略（均摊）。
        - 仅支持子类提供的检索接口参数中列出的过滤（例如 min_importance、user_id）。

        参数：
        - query: 查询字符串（具体语义由各记忆类型实现决定）
        - memory_types: 要检索的类型列表（None 表示所有已启用类型）
        - limit: 最终返回的最大条数
        - min_importance: 只返回重要性 >= 该阈值的记忆
        - time_range: 预留参数（(start, end)），当前未在 manager 层统一实现过滤
        """

        if memory_types is None:
            memory_types = list(self.memory_types.keys()) # 默认检索所有已启用的类型

        all_results: List[MemoryItem] = []

        # 将总体 limit 均匀分配到每个类型，保证每个类型都有机会返回结果，limit即最终返回的总数，per_type_limit 是每个类型的最大返回数
        per_type_limit = max(1, limit // max(1, len(memory_types)))

        for memory_type in memory_types:
            if memory_type in self.memory_types:
                memory_instance = self.memory_types[memory_type] # memory_instance 是具体的记忆类型实例，如 WorkingMemory、EpisodicMemory 等
                try:
                    # 调用子类的 retrieve；传入 user_id 便于子类做按用户过滤
                    type_results = memory_instance.retrieve(
                        query=query,
                        limit=per_type_limit,
                        min_importance=min_importance,
                        user_id=self.user_id,
                    )
                    all_results.extend(type_results) # extend 而非 append，避免嵌套列表
                except Exception as e:
                    # 保持容错：某种记忆类型检索失败时记录警告并继续
                    logger.warning("检索 %s 记忆时出错: %s", memory_type, e)
                    continue

        # 合并后按 importance 排序（降序），返回 top-N
        all_results.sort(key=lambda x: x.importance, reverse=True)
        return all_results[:limit]

    def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        importance: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """更新已存在的记忆项

        实现：在各记忆类型中查找拥有该 id 的项，并委托子类执行更新操作。
        返回 True 表示更新成功，否则 False。
        """

        for memory_type, memory_instance in self.memory_types.items(): # memory_instance 是具体的记忆类型实例，如 WorkingMemory、EpisodicMemory 等
            if memory_instance.has_memory(memory_id):
                return memory_instance.update(memory_id, content, importance, metadata)

        logger.warning("未找到记忆: %s", memory_id)
        return False

    def remove_memory(self, memory_id: str) -> bool:
        """删除指定 id 的记忆项

        在各记忆类型中查找，找到即可调用子类的 remove 并返回结果。
        """
        for memory_type, memory_instance in self.memory_types.items(): # memory_instance 是具体的记忆类型实例，如 WorkingMemory、EpisodicMemory 等
            if memory_instance.has_memory(memory_id):
                return memory_instance.remove(memory_id)

        logger.warning("未找到记忆: %s", memory_id)
        return False

    def forget_memories(
        self,
        strategy: str = "importance_based",
        threshold: float = 0.1,
        max_age_days: int = 30,
    ) -> int:
        """执行记忆遗忘策略并返回被遗忘的条数

        参数：
        - strategy: 遗忘策略标识，示例值包括 "importance_based"、"time_based"、"capacity_based"
        - threshold: 遗忘阈值，语义依赖于具体策略
        - max_age_days: 在 time_based 策略下可作为最大保存天数

        该方法遍历所有已启用的记忆类型，若子类实现了 forget 方法则调用之。
        """

        total_forgotten = 0

        for memory_type, memory_instance in self.memory_types.items():
            if hasattr(memory_instance, "forget"):
                forgotten = memory_instance.forget(strategy, threshold, max_age_days)
                total_forgotten += forgotten

        logger.info("记忆遗忘完成: %d 条记忆", total_forgotten)
        return total_forgotten

    def consolidate_memories(
        self,
        from_type: str = "working",
        to_type: str = "episodic",
        importance_threshold: float = 0.7,
    ) -> int:
        """将高重要性的短期记忆整合到长期记忆中

        过程：
        - 从源类型获取所有记忆，挑选 importance >= threshold 的条目
        - 从源中移除并将其加入目标类型，必要时提升重要性

        返回值：整合成功的记忆条数
        """

        if from_type not in self.memory_types or to_type not in self.memory_types:
            logger.warning("记忆类型不存在: %s -> %s", from_type, to_type)
            return 0

        source_memory = self.memory_types[from_type]
        target_memory = self.memory_types[to_type]

        all_memories = source_memory.get_all()
        candidates = [m for m in all_memories if m.importance >= importance_threshold]

        consolidated_count = 0
        for memory in candidates:
            # 先从源删除，避免重复
            if source_memory.remove(memory.id):
                memory.memory_type = to_type
                # 简单策略：稍微提升重要性以反映长期化
                memory.importance = min(1.0, memory.importance * 1.1)
                target_memory.add(memory)
                consolidated_count += 1

        logger.info(
            "记忆整合完成: %d 条记忆从 %s 转移到 %s",
            consolidated_count,
            from_type,
            to_type,
        )
        return consolidated_count

    def get_memory_stats(self) -> Dict[str, Any]:
        """返回当前记忆系统的统计信息字典

        统计字段包括：user_id、启用的类型、每类记忆的统计（由子类提供）以及汇总的总数。
        注意：total_memories 采用子类提供的 count（活跃记忆数），不包括已遗忘或归档的历史数目。
        """

        stats: Dict[str, Any] = {
            "user_id": self.user_id,
            "enabled_types": list(self.memory_types.keys()),
            "total_memories": 0,
            "memories_by_type": {},
            "config": {
                "max_capacity": getattr(self.config, "max_capacity", None),
                "importance_threshold": getattr(self.config, "importance_threshold", None),
                "decay_factor": getattr(self.config, "decay_factor", None),
            },
        }

        for memory_type, memory_instance in self.memory_types.items():
            type_stats = memory_instance.get_stats()
            stats["memories_by_type"][memory_type] = type_stats
            # 使用子类统计中的 count 字段作为活跃记忆数
            stats["total_memories"] += type_stats.get("count", 0)

        return stats

    def clear_all_memories(self):
        """清空所有记忆类型中的内容

        对所有启用的记忆实例调用其 clear 接口，通常用于重置或测试场景。
        """
        for memory_type, memory_instance in self.memory_types.items():
            memory_instance.clear()
        logger.info("所有记忆已清空")

    # ----- 内部辅助函数 -----
    def _classify_memory_type(self, content: str, metadata: Optional[Dict[str, Any]]) -> str:
        """根据内容与元数据进行简单的记忆类型分类

        逻辑：
        - 若 metadata 指定了 type，则优先使用
        - 否则通过关键字判断是否为 episodic、semantic，否则默认 working
        该函数可替换为更复杂的分类器（如 ML 模型或语义相似度判定）。
        """
        if metadata and metadata.get("type"):
            return metadata["type"]

        if self._is_episodic_content(content):
            return "episodic"
        elif self._is_semantic_content(content):
            return "semantic"
        else:
            return "working"

    def _is_episodic_content(self, content: str) -> bool:
        """简单关键字判断：是否像事件/经历相关的文本

        仅作为启发式规则，匹配中文常见表示时间和经历的词语。
        """
        episodic_keywords = ["昨天", "今天", "明天", "上次", "记得", "发生", "经历"]
        return any(keyword in content for keyword in episodic_keywords)

    def _is_semantic_content(self, content: str) -> bool:
        """简单关键字判断：是否像概念/定义/规则相关的文本"""
        semantic_keywords = ["定义", "概念", "规则", "知识", "原理", "方法"]
        return any(keyword in content for keyword in semantic_keywords)

    def _calculate_importance(self, content: str, metadata: Optional[Dict[str, Any]]) -> float:
        """启发式计算记忆重要性（返回 0.0 - 1.0）

        规则（示例）：
        - 基础值为 0.5
        - 若内容较长则略微提升重要性
        - 若包含高权重关键词（如 "重要"）则提升更多
        - 元数据可包含 priority 字段以显式影响重要性
        最终结果会被裁剪到 [0.0, 1.0]
        """
        importance = 0.5  # 基础重要性

        # 内容较长通常意味着信息更丰富，适度提升权重
        if len(content) > 100:
            importance += 0.1

        # 关键词提升（简单启发式）
        important_keywords = ["重要", "关键", "必须", "注意", "警告", "错误"]
        if any(keyword in content for keyword in important_keywords):
            importance += 0.2

        # 元数据优先级字段可以显著影响重要性
        if metadata:
            if metadata.get("priority") == "high":
                importance += 0.3
            elif metadata.get("priority") == "low":
                importance -= 0.2

        # 保证返回值在合法区间
        return max(0.0, min(1.0, importance))

    def __str__(self) -> str:
        stats = self.get_memory_stats()
        return f"MemoryManager(user={self.user_id}, total={stats['total_memories']})"
