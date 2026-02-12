"""异常体系"""

class AgentsException(Exception):
    """HelloAgents基础异常类"""
    pass

class LLMException(AgentsException):
    """LLM相关异常"""
    pass

class AgentException(AgentsException):
    """Agent相关异常"""
    pass

class ConfigException(AgentsException):
    """配置相关异常"""
    pass

class ToolException(AgentsException):
    """工具相关异常"""
    pass
