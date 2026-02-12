"""配置管理模块"""

import os
from typing import Optional,Dict,Any
from pydantic import BaseModel
"""pydantic 是一个基于 Python 类型注解的数据验证与解析库：你
通过继承 BaseModel 定义数据/配置模型，pydantic 会自动把原始数
据（如 dict、JSON、环境变量）转换并校验为指定类型的 Python 对
象，校验失败会抛出 ValidationError。核心功能:1.类型验证2.自动解析与转换3.方便的序列化"""


class Config(BaseModel):
    """agent配置类,管理智能体的可配置参数"""

    # LLM配置
    default_model: str = "gpt-3.5-turbo"
    default_provider: str = "openai"
    temperature: float = 0.7
    max_tokens: Optional[int] = None

    # 系统配置
    debug: bool = False # 是否启用调试模式
    log_level: str = "INFO" # 日志记录级别

    # 其他配置
    max_history_length: int = 1000 # 最大历史消息长度

    """@classmethod: 这是一个类方法。你不需要先有一个 config 对象，可
    以直接通过 Config.from_env() 来创建一个新实例。"""
    @classmethod
    def from_env(cls) -> "Config":
        """
        从环境变量中创建配置实例,self代表对象示例，cls代表类本身
            
        """
        return cls(
            debug = os.getenv("DEBUG","false").lower() == "true",
            log_level = os.getenv("LOG_LEVEL","INFO"),
            temperature = float(os.getenv("TEMPERATURE","0.7")),
            max_tokens = int(os.getenv("MAX_TOKENS")) if os.getenv("MAX_TOKENS") else None
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
        return self.dict()