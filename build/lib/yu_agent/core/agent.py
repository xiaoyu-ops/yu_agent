"""Agent 基类"""

from abc import ABC, abstractmethod
from typing import Optional,Any
from .message import Message
from .config import Config
from .llm import LLM

class Agent(ABC):
    """
    Agent 基类，定义智能体的核心接口和行为
    """

    def __init__(self, name: str, llm: LLM, system_prompt: Optional[str] = None, config: Optional[Config] = None):
        """
        初始化 Agent 实例。

        Args:
            name: 智能体名称，用于标识实例。
            llm: 用于生成响应的 LLM 实例；若为 None 则使用默认 LLM。
            system_prompt: 系统提示（默认提供一个简单职责说明）。
            config: 可选的 Config 对象，包含可配置项。
        """
        self.name = name
        # 如果未提供 llm，则创建一个默认 LLM 实例
        self.llm = llm or LLM()
        # 系统级别的提示，作为每次交互的上下文指令
        self.system_prompt = system_prompt or "你是一个智能体，负责处理用户的请求并提供有用的响应。"
        # 使用提供的配置或默认配置
        self.config = config or Config()
        # 历史消息列表，用于保存交互记录（按顺序保存 Message 对象）
        self.history: list[Message] = []



    @abstractmethod
    def run(self, input_text: str, **kwargs) -> str:
        """运行智能体，处理输入并生成响应。子类必须实现此方法。"""
        pass

    def add_message(self, message: Message):
        """
        将一条 `Message` 添加到历史记录末尾。

        参数:
            message: 要添加的 `Message` 实例。
        """
        self.history.append(message)
        
    def get_history(self) -> list[Message]:
        """
        返回历史消息的浅拷贝，避免外部直接修改内部列表。

        Returns:
            list[Message]: 历史消息拷贝。
        """
        return self.history.copy()
    
    def clear_history(self):
        """
        清空历史记录，移除所有已保存的 `Message`。
        """
        self.history.clear()

    def __str__(self) -> str:
        # 以字符串形式简单展示 Agent 的名称与 LLM 提供者信息，便于调试
        return f"Agent(name={self.name},provider={self.llm.provider})"    
    
    def __repr__(self) -> str:
        return self.__str__()