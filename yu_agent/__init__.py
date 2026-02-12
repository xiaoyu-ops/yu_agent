"""
基于OpenAI原生API构建,提供简洁高效的智能体开发体验。
"""

from .version import __version__, __author__, __email__, __description__

# 核心组件
from .core.llm import AgentsLLM
from .core.config import Config
from .core.message import Message
from .core.exceptions import AgentsException

# Agent实现
from .agents.simple_agent import SimpleAgent
from .agents.react_agent import ReActAgent
from .agents.reflection_agent import ReflectionAgent
from .agents.plan_solve_agent import PlanAndSolveAgent

# 工具系统
from .tools.registry import ToolRegistry, global_registry
from .tools.builtin.search import SearchTool, search
from .tools.builtin.calculator import CalculatorTool, calculate
from .tools.builtin.rag_tool import RAGTool
from .tools.chain import ToolChain, ToolChainManager
from .tools.async_executor import AsyncToolExecutor

# 记忆系统
from .memory import (
    MemoryManager,
    MemoryItem,
    MemoryConfig,
    BaseMemory,
    WorkingMemory,
    EpisodicMemory,
    SemanticMemory,
    PerceptualMemory,
)

__all__ = [
    # 版本信息
    "__version__",
    "__author__",
    "__email__",
    "__description__",

    # 核心组件
    "AgentsLLM",
    "Config",
    "Message",
    "AgentsException",

    # Agent范式
    "SimpleAgent",
    "ReActAgent",
    "ReflectionAgent",
    "PlanAndSolveAgent",

    # 工具系统
    "ToolRegistry",
    "global_registry",
    "SearchTool",
    "search",
    "CalculatorTool",
    "calculate",
    "RAGTool",
    "ToolChain",
    "ToolChainManager",
    "AsyncToolExecutor",

    # 记忆系统
    "MemoryManager",
    "MemoryItem",
    "MemoryConfig",
    "BaseMemory",
    "WorkingMemory",
    "EpisodicMemory",
    "SemanticMemory",
    "PerceptualMemory",
]


