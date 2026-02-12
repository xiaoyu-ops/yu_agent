"""
记忆工具
作为yuagent框架提供记忆能力的工具实现。
可以作为工具添加到任何Agent中，为Agent提供记忆功能。
"""

from typing import Optional, List, Dict, Any
from datetime import datetime  # 使用标准库 datetime

from ..base import Tool, ToolParameter
from ..memory import MemoryManager, MemoryConfig

class MemoryTool(Tool):
        """
        记忆工具

        说明:
        - 这是一个 `Tool` 子类，用于为 Agent 提供“记忆”相关的操作接口，
            包括添加、搜索、摘要、统计、更新、删除、遗忘、整合、清空等功能。
        - 外部通过调用 `run(parameters)` 并传入 `action` 参数来执行具体操作，
            其余参数作为对应 action 的输入。
        - 本类将具体的存储与检索逻辑委托给 `MemoryManager` 实现，负责持久化与向量检索等。
        """

        def __init__(self, user_id: str = "default_user", memory_config: MemoryConfig = None, memory_types: List[str] = None):
            """初始化 MemoryTool

            Args:
                user_id: 与记忆管理器关联的用户标识（可选，默认 "default_user"）。
                memory_config: 可选的 `MemoryConfig` 配置实例。
                memory_types: 可选的记忆类型列表（例如: working/semantic/episodic）。
            """
            super().__init__(name="memory", description="提供记忆功能的工具")

            # 存储配置信息与支持的记忆类型
            self.memory_config = memory_config or MemoryConfig()
            self.memory_types = memory_types or ["working", "semantic", "episodic"]

            # 创建 MemoryManager 实例（负责实际的记忆存取）
            # 注意: 变量命名保持为 `memory_manager`，避免拼写不一致问题
            self.memory_manager = MemoryManager(
                config=self.memory_config,
                user_id=user_id,
                enable_working="working" in self.memory_types,
                enable_episodic="episodic" in self.memory_types,
                enable_semantic="semantic" in self.memory_types,
                enable_perceptual="perceptual" in self.memory_types
            )

            # 会话相关状态
            # `current_session_id` 标识当前会话，初始为 None 表示未开始会话
            # `conversation_count` 记录对话轮次，用于自动记录对话时的索引
            self.current_session_id = None
            self.conversation_count = 0

        def run(self,parameters: Dict[str, Any]) -> str:
            """执行工具
            Args:
                parameters (Dict[str, Any]): 工具参数，包含操作类型和相关参数.必须包含action参数
            Returns:
                执行结果字符串。
            """
            # 先进行参数校验（基类 `Tool.validate_parameters` 会调用子类的 `get_parameters()`）
            if not self.validate_parameters(parameters):
                return "参数验证失败，请检查输入参数。"
            
            # 提取要执行的 action，并将其余参数传给 `execute` 方法
            action = parameters.get("action")
            kwargs = {k: v for k, v in parameters.items() if k != "action"}
            return self.execute(action, **kwargs)
        
        def get_parameters(self) -> List[ToolParameter]:
            """获取工具参数定义"""
            return [
                ToolParameter(
                    name = "action",
                    type = "string",
                    description = (
                        "要执行的操作："
                        "add(添加记忆), search(搜索记忆), summary(获取摘要), stats(获取统计), "
                        "update(更新记忆), remove(删除记忆), forget(遗忘记忆), consolidate(整合记忆), clear_all(清空所有记忆)"
                    ),
                    required = True
                ),
                ToolParameter(name="content", type="string", description="记忆内容（add/update时可用；感知记忆可作描述）", required=False),
                ToolParameter(name="query", type="string", description="搜索查询（search时可用）", required=False),
                ToolParameter(name="memory_type", type="string", description="记忆类型：working, episodic, semantic, perceptual（默认：working）", required=False, default="working"),
                ToolParameter(name="importance", type="number", description="重要性分数，0.0-1.0（add/update时可用）", required=False),
                ToolParameter(name="limit", type="integer", description="搜索结果数量限制（默认：5）", required=False, default=5),
                ToolParameter(name="memory_id", type="string", description="目标记忆ID（update/remove时必需）", required=False),
                ToolParameter(name="file_path", type="string", description="感知记忆：本地文件路径（image/audio）", required=False),
                ToolParameter(name="modality", type="string", description="感知记忆模态：text/image/audio（不传则按扩展名推断）", required=False),
                ToolParameter(name="strategy", type="string", description="遗忘策略：importance_based/time_based/capacity_based（forget时可用）", required=False, default="importance_based"),
                ToolParameter(name="threshold", type="number", description="遗忘阈值（forget时可用，默认0.1）", required=False, default=0.1),
                ToolParameter(name="max_age_days", type="integer", description="最大保留天数（forget策略为time_based时可用）", required=False, default=30),
                ToolParameter(name="from_type", type="string", description="整合来源类型（consolidate时可用，默认working）", required=False, default="working"),
                ToolParameter(name="to_type", type="string", description="整合目标类型（consolidate时可用，默认episodic）", required=False, default="episodic"),
                ToolParameter(name="importance_threshold", type="number", description="整合重要性阈值（默认0.7）", required=False, default=0.7)
            ]
        
        def execute(self, action: str, **kwargs) -> str:
            """执行记忆操作
            Args:
                action (str): 要执行的操作类型
                kwargs: 其他相关参数，具体取决于操作类型
            Returns:
                str: 操作结果描述
            """
            if action == "add":
                return self._add_memory(**kwargs)
            elif action == "search":
                return self._search_memory(**kwargs)
            elif action == "summary":
                return self._get_summary(**kwargs)
            elif action == "stats":
                return self._get_stats()
            elif action == "update":
                return self._update_memory(**kwargs)
            elif action == "remove":
                return self._remove_memory(**kwargs)
            elif action == "forget":
                return self._forget(**kwargs)
            elif action == "consolidate":
                return self._consolidate(**kwargs)
            elif action == "clear_all":
                return self._clear_all()
            else:
                return f"不支持的操作: {action}。支持的操作: add, search, summary, stats, update, remove, forget, consolidate, clear_all"

        def _add_memory(
            self,
            content: str = "",
            memory_type: str = "working",
            importance: Optional[float] = 0.5,
            file_path: Optional[str] = None,
            modality: Optional[str] = None,
            **metadata
        ) -> str:
            """添加记忆

            说明:
            - 支持感知记忆（`perceptual`）: 如果传入 `file_path`，会尝试推断 `modality` 并将原始文件路径放入 `raw_data`。
            - 会在 metadata 中注入 `session_id` 与 `timestamp`。
            - 添加失败时返回错误提示。
            """
            try:
                # 确保有会话id
                if self.current_session_id is None:
                    self.current_session_id = f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}"

                # 如果是感知记忆并提供了文件路径，注入模态与原始数据引用
                if memory_type == "perceptual" and file_path:
                    inferred = modality or self._infer_modality(file_path)
                    metadata.setdefault("modality", inferred)
                    metadata.setdefault("raw_data", file_path)

                # 注入会话与时间戳信息
                metadata.update({
                    "session_id": self.current_session_id,
                    "timestamp": datetime.now().isoformat()
                })

                # 调用底层 MemoryManager 添加记忆
                memory_id = self.memory_manager.add_memory(
                    content=content,
                    memory_type=memory_type,
                    importance=importance,
                    metadata=metadata,
                    auto_classify=False,  # 禁用自动分类，使用明确指定的类型
                )

                return f"记忆已添加 (ID: {memory_id[:8]}...)"

            except Exception as e:
                return f"添加记忆失败: {str(e)}"

        def _infer_modality(self, path: str) -> str:
            """根据扩展名推断模态（默认image/audio/text）"""
            try:
                ext = (path.rsplit('.', 1)[-1] or '').lower()
                if ext in {"png", "jpg", "jpeg", "bmp", "gif", "webp"}:
                    return "image"
                if ext in {"mp3", "wav", "flac", "m4a", "ogg"}:
                    return "audio"
                return "text"
            except Exception:
                return "text"


        def _search_memory(
            self,
            query: str,
            limit: int = 5,
            memory_types: List[str] = None,
            memory_type: str = None,  # 添加单数形式的参数支持
            min_importance: float = 0.1
        ) -> str:
            """搜索记忆"""
            try:
                # 处理单数形式的memory_type参数
                if memory_type and not memory_types:
                    memory_types = [memory_type]

                results = self.memory_manager.retrieve_memories(
                    query=query,
                    limit=limit,
                    memory_types=memory_types,
                    min_importance=min_importance
                )

                if not results:
                    return f"未找到与 '{query}' 相关的记忆"

                # 格式化结果
                formatted_results = []
                formatted_results.append(f"找到 {len(results)} 条相关记忆:")

                for i, memory in enumerate(results, 1):
                    memory_type_label = {
                        "working": "工作记忆",
                        "episodic": "情景记忆",
                        "semantic": "语义记忆",
                        "perceptual": "感知记忆"
                    }.get(memory.memory_type, memory.memory_type)

                    content_preview = memory.content[:500] + "..." if len(memory.content) > 500 else memory.content # 预览前500字符，过长则添加省略号
                    formatted_results.append(
                        f"{i}. [{memory_type_label}] {content_preview} (重要性: {memory.importance:.2f})"
                    )

                return "\n".join(formatted_results)

            except Exception as e:
                return f"搜索记忆失败: {str(e)}"

        def _get_summary(self, limit: int = 10) -> str:
            """获取记忆摘要"""
            try:
                stats = self.memory_manager.get_memory_stats()

                summary_parts = [
                    f"记忆系统摘要",
                    f"总记忆数: {stats['total_memories']}",
                    f"当前会话: {self.current_session_id or '未开始'}",
                    f"对话轮次: {self.conversation_count}"
                ]

                # 各类型记忆统计
                if stats['memories_by_type']:
                    summary_parts.append("\n记忆类型分布:")
                    for memory_type, type_stats in stats['memories_by_type'].items():
                        count = type_stats.get('count', 0)
                        avg_importance = type_stats.get('avg_importance', 0)
                        type_label = {
                            "working": "工作记忆",
                            "episodic": "情景记忆",
                            "semantic": "语义记忆",
                            "perceptual": "感知记忆"
                        }.get(memory_type, memory_type)

                        summary_parts.append(f"  • {type_label}: {count} 条 (平均重要性: {avg_importance:.2f})")

                # 获取重要记忆 - 修复重复问题
                important_memories = self.memory_manager.retrieve_memories(
                    query="",
                    memory_types=None,  # 从所有类型中检索
                    limit=limit * 3,  # 获取更多候选，然后去重
                    min_importance=0.5  # 降低阈值以获取更多记忆
                )

                if important_memories:
                    # 去重：使用记忆ID和内容双重去重
                    seen_ids = set()
                    seen_contents = set()
                    unique_memories = []
                    
                    for memory in important_memories:
                        # 使用ID去重
                        if memory.id in seen_ids:
                            continue
                        
                        # 使用内容去重（防止相同内容的不同记忆）
                        content_key = memory.content.strip().lower()
                        if content_key in seen_contents:
                            continue
                        
                        seen_ids.add(memory.id)
                        seen_contents.add(content_key)
                        unique_memories.append(memory)
                    
                    # 按重要性排序
                    unique_memories.sort(key=lambda x: x.importance, reverse=True) # 这个lambda函数的作用是根据记忆对象的importance属性进行排序，reverse=True表示降序排列，即重要性高的记忆会排在前面。
                    summary_parts.append(f"\n重要记忆 (前{min(limit, len(unique_memories))}条):")

                    for i, memory in enumerate(unique_memories[:limit], 1):
                        content_preview = memory.content[:60] + "..." if len(memory.content) > 60 else memory.content
                        summary_parts.append(f"  {i}. {content_preview} (重要性: {memory.importance:.2f})")

                return "\n".join(summary_parts)

            except Exception as e:
                return f"获取摘要失败: {str(e)}"

        def _get_stats(self) -> str:
            """获取统计信息"""
            try:
                stats = self.memory_manager.get_memory_stats()

                stats_info = [
                    f"记忆系统统计",
                    f"总记忆数: {stats['total_memories']}",
                    f"启用的记忆类型: {', '.join(stats['enabled_types'])}",
                    f"会话ID: {self.current_session_id or '未开始'}",
                    f"对话轮次: {self.conversation_count}"
                ]

                return "\n".join(stats_info)

            except Exception as e:
                return f"获取统计信息失败: {str(e)}"

        def auto_record_conversation(self, user_input: str, agent_response: str):
            """自动记录对话

            这个方法可以被Agent调用来自动记录对话历史
            """
            self.conversation_count += 1
            # 记录用户输入
            self._add_memory(
                content=f"用户: {user_input}",
                memory_type="working",
                importance=0.6,
                type="user_input",
                conversation_id=self.conversation_count
            )

            # 记录Agent响应
            self._add_memory(
                content=f"助手: {agent_response}",
                memory_type="working",
                importance=0.7,
                type="agent_response",
                conversation_id=self.conversation_count
            )

            # 如果是重要对话，记录为情景记忆
            if len(agent_response) > 100 or "重要" in user_input or "记住" in user_input:
                interaction_content = f"对话 - 用户: {user_input}\n助手: {agent_response}"
                self._add_memory(
                    content=interaction_content,
                    memory_type="episodic",
                    importance=0.8,
                    type="interaction",
                    conversation_id=self.conversation_count
                )

        def _update_memory(self, memory_id: str, content: str = None, importance: float = None, **metadata) -> str:
            """更新记忆"""
            try:
                success = self.memory_manager.update_memory(
                    memory_id=memory_id,
                    content=content,
                    importance=importance,
                    metadata=metadata or None
                )
                return "记忆已更新" if success else "未找到要更新的记忆"
            except Exception as e:
                return f"更新记忆失败: {str(e)}"

        def _remove_memory(self, memory_id: str) -> str:
            """删除记忆"""
            try:
                success = self.memory_manager.remove_memory(memory_id)
                return "记忆已删除" if success else "未找到要删除的记忆"
            except Exception as e:
                return f"删除记忆失败: {str(e)}"

        def _forget(self, strategy: str = "importance_based", threshold: float = 0.1, max_age_days: int = 30) -> str:
            """遗忘记忆（支持多种策略）"""
            try:
                count = self.memory_manager.forget_memories(
                    strategy=strategy,
                    threshold=threshold,
                    max_age_days=max_age_days
                )
                return f"已遗忘 {count} 条记忆（策略: {strategy}）"
            except Exception as e:
                return f"遗忘记忆失败: {str(e)}"

        def _consolidate(self, from_type: str = "working", to_type: str = "episodic", importance_threshold: float = 0.7) -> str:
            """整合记忆（将重要的短期记忆提升为长期记忆）"""
            try:
                count = self.memory_manager.consolidate_memories(
                    from_type=from_type,
                    to_type=to_type,
                    importance_threshold=importance_threshold,
                )
                return f"已整合 {count} 条记忆为长期记忆（{from_type} → {to_type}，阈值={importance_threshold}）"
            except Exception as e:
                return f"整合记忆失败: {str(e)}"

        def _clear_all(self) -> str:
            """清空所有记忆"""
            try:
                self.memory_manager.clear_all_memories()
                return "已清空所有记忆"
            except Exception as e:
                return f"清空记忆失败: {str(e)}"

        def add_knowledge(self, content: str, importance: float = 0.9):
            """添加知识到语义记忆

            便捷方法，用于添加重要知识
            """
            return self._add_memory(
                content=content,
                memory_type="semantic",
                importance=importance,
                knowledge_type="factual",
                source="manual"
            )

        def get_context_for_query(self, query: str, limit: int = 3) -> str:
            """为查询获取相关上下文

            这个方法可以被Agent调用来获取相关的记忆上下文
            """
            results = self.memory_manager.retrieve_memories(
                query=query,
                limit=limit,
                min_importance=0.3
            )

            if not results:
                return ""

            context_parts = ["相关记忆:"]
            for memory in results:
                context_parts.append(f"- {memory.content}")

            return "\n".join(context_parts)

        def clear_session(self):
            """清除当前会话"""
            self.current_session_id = None
            self.conversation_count = 0

            # 清理工作记忆
            wm = self.memory_manager.memory_types.get('working') if hasattr(self.memory_manager, 'memory_types') else None
            if wm:
                wm.clear()

        def consolidate_memories(self):
            """整合记忆"""
            return self.memory_manager.consolidate_memories()

        def forget_old_memories(self, max_age_days: int = 30):
            """遗忘旧记忆"""
            return self.memory_manager.forget_memories(
                strategy="time_based",
                max_age_days=max_age_days
            )
