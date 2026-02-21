"""ContextBuilder - GSSC流水线实现

实现 Gather-Select-Structure-Compress 上下文构建流程：
1. Gather: 从多源收集候选信息（历史、记忆、RAG、工具结果）
2. Select: 基于优先级、相关性、多样性筛选
3. Structure: 组织成结构化上下文模板
4. Compress: 在预算内压缩与规范化
"""

# 类型提示库：支持复杂类型注解
from typing import Dict, Any, List, Optional, Tuple
# 数据类装饰器：简化数据结构定义
from dataclasses import dataclass, field
# 日期时间处理：用于记录时间戳和计算新近性
from datetime import datetime
# Token计数库：精确计算OpenAI兼容模型的token数
import tiktoken
# 数学库：用于指数衰减等计算
import math

# 内部导入
from ..core.message import Message  # 消息数据模型
from ..tools.builtin import memory_tool, RAGTool  # 记忆工具和RAG工具


@dataclass
class ContextPacket:
    """上下文信息包 - 封装单个上下文片段及其元数据

    用于在GSSC流程中传递上下文信息，包含内容、时间戳、元数据和计算的token数。
    """
    # 上下文内容文本
    content: str
    # 创建时间戳，用于计算新近性评分（自动记录当前时间）
    timestamp: datetime = field(default_factory=datetime.now)  # 此处的field用法确保每个实例都有独立的时间戳
    # 元数据字典，可用于标记来源类型（如"instructions"、"task_state"等）
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Token数量，自动计算（0表示待计算）
    token_count: int = 0
    # 相关性评分，范围0.0-1.0，1.0表示完全相关
    relevance_score: float = 0.0  # 0.0-1.0

    def __post_init__(self):
        """数据类初始化后自动执行：计算content的token数"""
        if self.token_count == 0:
            # 如果未指定token_count，自动调用count_tokens计算
            self.token_count = count_tokens(self.content)


@dataclass
class ContextConfig:
    """上下文构建配置 - 控制GSSC流程的所有参数

    包含token预算、相关性阈值、MMR多样性参数等核心配置。
    """
    # 总Token预算：LLM上下文窗口的最大token数，建议不超过max_tokens的60%
    max_tokens: int = 8000
    # 生成余量比例：为模型响应预留token空间（典型10-20%）
    reserve_ratio: float = 0.15
    # 最小相关性阈值：低于此值的内容包不被纳入（范围0.0-1.0）
    min_relevance: float = 0.3
    # 启用最大边际相关性(MMR)：权衡相关性与多样性，避免重复内容
    enable_mmr: bool = True
    # MMR平衡参数：λ=0表示纯多样性，λ=1表示纯相关性，推荐0.7
    mmr_lambda: float = 0.7
    # 系统提示模板：可自定义的提示词格式
    system_prompt_template: str = ""
    # 启用压缩：当上下文超预算时是否执行截断压缩
    enable_compression: bool = True

    def get_available_tokens(self) -> int:
        """获取实际可用token预算（总预算 - 生成余量）

        Returns:
            int: 扣除余量后的可用token数
        """
        return int(self.max_tokens * (1 - self.reserve_ratio))


class ContextBuilder:
    """上下文构建器 - 实现GSSC上下文流水线

    将四阶段流程应用于上下文构建：
    - Gather (收集): 从多个来源聚合候选信息
    - Select (筛选): 基于相关性、新近性和预算进行智能筛选
    - Structure (组织): 按照结构化模板组织信息
    - Compress (压缩): 在token预算内进行必要的压缩

    用法示例：
    ```python
    builder = ContextBuilder(
        memory_tool=memory_tool,
        rag_tool=rag_tool,
        config=ContextConfig(max_tokens=8000)
    )

    context = builder.build(
        user_query="用户问题",
        conversation_history=[...],
        system_instructions="系统指令"
    )
    ```
    """

    def __init__(
        self,
        memory_tool: Optional[memory_tool.MemoryTool] = None,
        rag_tool: Optional[RAGTool] = None,
        config: Optional[ContextConfig] = None
    ):
        """初始化ContextBuilder

        Args:
            memory_tool: 可选的记忆工具，用于从长期记忆中检索相关信息
            rag_tool: 可选的RAG工具，用于从知识库检索事实证据
            config: 上下文构建配置，包含token预算等参数
        """
        self.memory_tool = memory_tool
        self.rag_tool = rag_tool
        # 如果未提供config，使用默认配置
        self.config = config or ContextConfig()
        # 初始化token编码器：使用cl100k_base编码对应GPT-3.5/GPT-4
        self._encoding = tiktoken.get_encoding("cl100k_base")
    
    def build(
        self,
        user_query: str,
        conversation_history: Optional[List[Message]] = None,
        system_instructions: Optional[str] = None,
        additional_packets: Optional[List[ContextPacket]] = None
    ) -> str:
        """构建完整上下文 - GSSC流水线入口

        执行四阶段流程：收集 → 筛选 → 组织 → 压缩

        Args:
            user_query: 用户当前查询/任务描述，用于计算相关性
            conversation_history: 对话历史消息列表，用于提供上下文
            system_instructions: 系统级别指令，具有最高优先级
            additional_packets: 额外的上下文包（用于注入自定义内容）

        Returns:
            str: 格式化的结构化上下文字符串，ready to feed to LLM
        """
        # Stage 1: Gather - 从多源收集候选信息包
        # 包括：系统指令、记忆检索结果、RAG结果、对话历史等
        packets = self._gather(
            user_query=user_query,
            conversation_history=conversation_history or [],
            system_instructions=system_instructions,
            additional_packets=additional_packets or []
        )

        # Stage 2: Select - 基于相关性、新近性、预算进行智能筛选
        # 计算评分，过滤低相关内容，保持token预算约束
        selected_packets = self._select(packets, user_query)

        # Stage 3: Structure - 按照标准模板组织已选内容
        # 生成结构化输出：[Role & Policies] [Task] [State] [Evidence] 等
        structured_context = self._structure(
            selected_packets=selected_packets,
            user_query=user_query,
            system_instructions=system_instructions
        )

        # Stage 4: Compress - 在预算内进行必要的压缩
        # 如果超预算，执行截断或摘要策略
        final_context = self._compress(structured_context)

        return final_context

    def _gather(
        self,
        user_query: str,
        conversation_history: List[Message],
        system_instructions: Optional[str],
        additional_packets: List[ContextPacket]
    ) -> List[ContextPacket]:
        """Stage 1: Gather - 从多源收集候选信息包

        收集的信息按优先级排列：
        - P0: 系统指令（强约束，必须遵循）
        - P1: 任务状态和关键结论（从记忆中提取）
        - P2: 事实证据（从RAG/知识库检索）
        - P3: 对话历史（提供上下文背景）

        Args:
            user_query: 用户查询，用于相关性检索
            conversation_history: 对话消息列表
            system_instructions: 系统级指令
            additional_packets: 额外输入的包

        Returns:
            List[ContextPacket]: 所有收集到的上下文包列表
        """
        packets = []

        # P0: 系统指令（强约束）
        # 系统指令优先级最高，指定Agent的角色和行为准则
        if system_instructions:
            packets.append(ContextPacket(
                content=system_instructions,
                # 标记为指令类型，在筛选阶段会特殊处理
                metadata={"type": "instructions"}
            ))

        # P1: 从记忆工具中获取任务状态与关键结论
        # 这部分是长期记忆中的重要信息：当前任务进度、已解决的问题等
        if self.memory_tool:
            try:
                # 搜索与任务进展相关的高优先级记忆
                # 关键词：任务状态、子目标、结论、阻塞问题等
                state_results = self.memory_tool.execute(
                    "search",
                    query="(任务状态 OR 子目标 OR 结论 OR 阻塞)",
                    min_importance=0.7,  # 只检索重要度较高的记忆
                    limit=5
                )
                # 如果成功获取结果且不为空，添加到包列表
                if state_results and "未找到" not in state_results:
                    packets.append(ContextPacket(
                        content=state_results,
                        metadata={"type": "task_state", "importance": "high"}
                    ))

                # 搜索与当前用户查询相关的所有记忆
                # 这用于提供历史背景和先前学习的知识
                related_results = self.memory_tool.execute(
                    "search",
                    query=user_query,
                    limit=5,
                    memory_types=["semantic", "episodic"]  # 明确指定搜索语义和情景记忆
                )
                # 改进条件：检查是否是真正的搜索结果
                # 只有当结果长度合理且不是纯"未找到"消息时才认为有效
                is_valid_result = False
                if related_results:
                    result_clean = related_results.strip()
                    # 如果结果只是"未找到"这几个字，就是无效的
                    if result_clean not in ("未找到", "搜索无结果"):
                        # 如果包含"未找到"但还有其他内容，可能是混合结果，也算有效
                        is_valid_result = True
                    elif len(related_results) > 20:
                        # 即使包含"未找到"，如果还有其他内容（>20字符），也算有效
                        is_valid_result = True

                    if is_valid_result:
                        packets.append(ContextPacket(
                            content=related_results,
                            metadata={"type": "related_memory"}
                        ))

            except Exception as e:
                # 记忆检索失败不应中断主流程，仅打印警告
                print(f"⚠️ 记忆检索失败: {e}")

        # P2: 从RAG工具中获取事实证据
        # RAG提供从外部知识库检索的相关信息，用于支撑回答
        if self.rag_tool:
            try:
                # 执行RAG检索：查询与用户输入相关的知识库段落
                rag_results = self.rag_tool.run({
                    "action": "search",
                    "query": user_query,
                    "top_k": 5  # 检索前5个最相关的段落
                })
                # 验证检索结果有效性
                is_valid_result = False
                if rag_results:
                    result_clean = rag_results.strip()
                    # 如果结果只是"未找到"这几个字，就是无效的
                    if result_clean not in ("未找到", "搜索无结果"):
                        is_valid_result = True
                    elif len(rag_results) > 20:
                        # 即使包含"未找到"，如果还有其他内容（>20字符），也算有效
                        is_valid_result = True

                    if is_valid_result:
                        packets.append(ContextPacket(
                            content=rag_results,
                            metadata={"type": "knowledge_base"}
                        ))

            except Exception as e:
                # RAG失败也不中断主流程
                print(f"⚠️ RAG检索失败: {e}")

        # P3: 对话历史（辅助材料）
        # 提供immediate context：最近的几条对话消息
        if conversation_history:
            # 为了节省token，只保留最近的N条消息
            recent_history = conversation_history[-10:]
            # 格式化为可读的对话日志
            history_text = "\n".join([
                f"[{msg.role}] {msg.content}"
                for msg in recent_history
            ])
            packets.append(ContextPacket(
                content=history_text,
                metadata={"type": "history", "count": len(recent_history)}
            ))

        # 添加外部注入的额外包
        packets.extend(additional_packets)

        return packets

    def _select(
        self,
        packets: List[ContextPacket],
        user_query: str
    ) -> List[ContextPacket]:
        """Stage 2: Select - 基于多维度评分进行智能筛选

        执行步骤：
        1. 计算相关性评分（基于关键词重叠）
        2. 计算新近性评分（基于时间戳的指数衰减）
        3. 组合计算复合评分
        4. 按预算进行贪心筛选

        Args:
            packets: 收集阶段得到的所有上下文包
            user_query: 用户查询，用于计算相关性

        Returns:
            List[ContextPacket]: 筛选后的高质量包列表，满足token和相关性约束
        """
        # Step 1: 计算相关性评分（关键词重叠比例）
        # 简单启发式：query中出现的词在content中占的比例
        query_tokens = set(user_query.lower().split())
        for packet in packets:
            content_tokens = set(packet.content.lower().split())
            if len(query_tokens) > 0:
                # 相关性 = 重叠词数 / 查询词数
                overlap = len(query_tokens & content_tokens)
                packet.relevance_score = overlap / len(query_tokens)
            else:
                packet.relevance_score = 0.0

        # Step 2: 计算新近性评分（指数衰减函数）
        # 思想：越新的信息越重要，基于e^(-t/τ)函数
        # τ是时间尺度，典型值1小时，可配置
        def recency_score(ts: datetime) -> float:
            """计算时间戳对应的新近性评分"""
            delta = max((datetime.now() - ts).total_seconds(), 0)
            # 时间常数τ：越小则衰减越快
            tau = 3600  # 1小时：1小时前的信息权重约为37%
            return math.exp(-delta / tau)

        # Step 3: 组合相关性和新近性，计算复合评分
        # 权重：相关性70%（主要），新近性30%（辅助）
        scored_packets: List[Tuple[float, ContextPacket]] = []
        for p in packets:
            rec = recency_score(p.timestamp) # 此处的recency_score函数计算新近性评分
            # 复合评分公式：使用加权平均
            score = 0.7 * p.relevance_score + 0.3 * rec
            scored_packets.append((score, p))

        # Step 4: 系统指令单独处理，优先级最高（必须纳入）
        # 这确保agent始终遵循系统指令
        system_packets = [p for (_, p) in scored_packets if p.metadata.get("type") == "instructions"]
        # 其他包按评分排序，准备筛选
        remaining = [p for (s, p) in sorted(scored_packets, key=lambda x: x[0], reverse=True)
                     if p.metadata.get("type") != "instructions"]

        # Step 5: 根据最小相关性阈值过滤非系统包
        # 丢弃相关性太低的信息，避免引入噪声
        # 注意：对于包含完整句子/段落的包，使用较低的阈值（因为关键词重叠法不够完美）
        # 系统指令始终保留，其他包至少保留阈值为0即可纳入（所有包）
        effective_threshold = 0.0  # 对于来自记忆和RAG的包，降低阈值以避免过度过滤
        filtered = [p for p in remaining if p.relevance_score >= effective_threshold]

        # Step 6: 贪心算法填充预算
        # 从高分到低分逐个添加，直到token预算用尽
        available_tokens = self.config.get_available_tokens()
        selected: List[ContextPacket] = []
        used_tokens = 0

        # 先放入系统指令（不受评分排序影响，必须保留）
        for p in system_packets:
            if used_tokens + p.token_count <= available_tokens:
                selected.append(p)
                used_tokens += p.token_count

        # 再按降序评分加入其余高质量包
        for p in filtered:
            # 预检查：如果加上这个包会超预算，跳过
            if used_tokens + p.token_count > available_tokens:
                continue
            selected.append(p)
            used_tokens += p.token_count

        return selected

    def _structure(
        self,
        selected_packets: List[ContextPacket],
        user_query: str,
        system_instructions: Optional[str]
    ) -> str:
        """Stage 3: Structure - 按照标准化模板组织上下文

        生成标准的结构化提示词模板，包含以下部分：
        - [Role & Policies]: Agent的角色和行为准则
        - [Task]: 当前任务描述
        - [State]: 任务进展状态
        - [Evidence]: 支撑性事实和引用
        - [Context]: 对话历史和背景
        - [Output]: 输出格式要求

        这种结构化格式能显著提升LLM理解和回答质量。

        Args:
            selected_packets: 筛选后的上下文包列表
            user_query: 用户查询
            system_instructions: 系统级指令

        Returns:
            str: 格式化的结构化提示词字符串
        """
        sections = []

        # Section 1: [Role & Policies] - 系统指令和Agent角色定义
        # 这部分定义agent应该扮演的角色、遵循的原则
        p0_packets = [p for p in selected_packets if p.metadata.get("type") == "instructions"]
        if p0_packets:
            role_section = "[Role & Policies]\n"
            role_section += "\n".join([p.content for p in p0_packets]) # 利用换行拼接
            sections.append(role_section)

        # Section 2: [Task] - 当前任务（用户查询）
        # 清晰地陈述用户的问题或请求
        sections.append(f"[Task]\n用户问题：{user_query}")

        # Section 3: [State] - 任务进展状态
        # 显示当前任务的进度、已做决定、待解决问题
        p1_packets = [p for p in selected_packets if p.metadata.get("type") == "task_state"]
        if p1_packets:
            state_section = "[State]\n关键进展与未决问题：\n"
            state_section += "\n".join([p.content for p in p1_packets])
            sections.append(state_section)

        # Section 4: [Evidence] - 事实证据和引用资料
        # 包含所有支撑性信息：检索结果、知识库摘要、记忆等
        # 这些包的metadata类型为：related_memory, knowledge_base, retrieval, tool_result
        p2_packets = [
            p for p in selected_packets
            if p.metadata.get("type") in {"related_memory", "knowledge_base", "retrieval", "tool_result"}
        ]
        if p2_packets:
            evidence_section = "[Evidence]\n事实与引用：\n"
            for p in p2_packets:
                evidence_section += f"\n{p.content}\n"
            sections.append(evidence_section)

        # Section 5: [Context] - 对话历史和背景
        # 提供对话的immediate context，帮助agent理解conversation flow
        p3_packets = [p for p in selected_packets if p.metadata.get("type") == "history"]
        if p3_packets:
            context_section = "[Context]\n对话历史与背景：\n"
            context_section += "\n".join([p.content for p in p3_packets])
            sections.append(context_section)

        # Section 6: [Output] - 输出格式和约束
        # 明确期望的回答格式，提高输出的结构化程度
        output_section = """[Output]
请按以下格式回答：
1. 结论（简洁明确）
2. 依据（列出支撑证据及来源）
3. 风险与假设（如有）
4. 下一步行动建议（如适用）"""
        sections.append(output_section)

        # 使用双换行符连接所有section，形成最终的结构化提示词
        return "\n\n".join(sections)

# TODO: Stage 4的压缩策略目前是简单的贪心截断，未来可以升级为基于LLM的智能摘要，保持关键信息的同时进一步压缩文本长度。

    def _compress(self, context: str) -> str:
        """Stage 4: Compress - 在token预算内进行压缩和规范化

        如果结构化上下文超出token预算，执行压缩策略：
        - 按行逐行评估token占用
        - 优先保留开头的结构标题
        - 在token用尽前截断
        - 保持基本结构完整性

        更高级的实现可采用LLM摘要，但当前使用简单截断策略。

        Args:
            context: 结构化上下文字符串

        Returns:
            str: 压缩后的上下文字符串（满足token预算约束）
        """
        # 如果禁用压缩，直接返回原始上下文
        if not self.config.enable_compression:
            return context

        # 计算当前上下文的token占用
        current_tokens = count_tokens(context)
        # 获取可用预算
        available_tokens = self.config.get_available_tokens()

        # 如果未超预算，无需压缩
        if current_tokens <= available_tokens:
            return context

        # 超预算警告：打印日志供调试使用
        print(f"⚠️ 上下文超预算 ({current_tokens} > {available_tokens})，执行截断")

        # 按换行符分割，保留行级粒度
        # 这样做的好处：保持结构标题完整，避免中间截断
        lines = context.split("\n")
        compressed_lines = []
        used_tokens = 0

        # 贪心地从头到尾添加行，直到token用尽
        for line in lines:
            line_tokens = count_tokens(line)
            # 预检查：这一行会导致超预算吗？
            if used_tokens + line_tokens > available_tokens:
                # 是：停止添加，保持结构完整性
                break
            # 否：添加这一行
            compressed_lines.append(line)
            used_tokens += line_tokens

        # 返回压缩后的结果
        return "\n".join(compressed_lines)


def count_tokens(text: str) -> int:
    """计算文本的token数量

    这是GSSC流水线的核心工具函数，用于：
    - 计算上下文包的token占用（在ContextPacket初始化时调用）
    - 评估上下文大小是否超预算
    - 指导贪心筛选和压缩策略

    实现：
    - 主方案：使用tiktoken库精确计算（适用于OpenAI兼容API）
    - 降级方案：失败时使用启发式估算（1 token ≈ 4字符）

    Args:
        text: 要计算的文本字符串

    Returns:
        int: token数量（整数）
    """
    try:
        # 使用cl100k_base编码，对应GPT-3.5和GPT-4
        # 这是OpenAI官方推荐的编码方式
        encoding = tiktoken.get_encoding("cl100k_base")
        # 编码文本并返回token列表长度
        return len(encoding.encode(text))
    except Exception:
        # 降级方案：如果tiktoken不可用或出错
        # 使用经验值：平均每个token约占4个字符
        # 这是一个粗略估算，误差可能±20%，但保证系统可用性
        return len(text) // 4

