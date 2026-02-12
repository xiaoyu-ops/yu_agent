"""核心框架模块 - 延迟导入以避免循环依赖"""

__all__ = ["Agent", "AgentsLLM", "LLM", "Message", "Config", "AgentException"]

def __getattr__(name):
    if name == "Agent":
        from .agent import Agent
        return Agent
    if name in ("AgentsLLM", "LLM"):
        from .llm import AgentsLLM
        return AgentsLLM
    if name == "Message":
        from .message import Message
        return Message
    if name == "Config":
        from .config import Config
        return Config
    if name == "AgentException":
        from .exceptions import AgentException
        return AgentException
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

def __dir__():
    return __all__