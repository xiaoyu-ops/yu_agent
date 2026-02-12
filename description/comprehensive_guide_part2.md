# yu_agent 完整文档汇总 - 第二部分

**编译时间**: 2026-02-13
**版本**: v0.2.0
**包含**: 架构详解、开发指南、参考文档

---

## 目录

1. [架构深入](#架构深入)
2. [开发指南](#开发指南)
3. [API 参考](#api-参考)
4. [贡献者指南](#贡献者指南)

---

# 架构深入

## 项目结构

```
yu_agent/
├── yu_agent/                    # 主包
│   ├── core/                    # 基础组件
│   │   ├── agent.py             # Agent 抽象基类
│   │   ├── llm.py               # 统一 LLM 客户端
│   │   ├── message.py           # 消息数据模型
│   │   ├── config.py            # 配置管理
│   │   └── exceptions.py         # 异常层级
│   │
│   ├── agents/                  # Agent 模式实现
│   │   ├── simple_agent.py      # 基础对话
│   │   ├── react_agent.py       # 推理+行动
│   │   ├── reflection_agent.py  # 自我反思
│   │   └── plan_solve_agent.py  # 计划分解
│   │
│   ├── tools/                   # 工具系统
│   │   ├── base.py              # Tool 抽象类
│   │   ├── registry.py          # 工具注册表
│   │   ├── chain.py             # 工具链
│   │   ├── async_executor.py    # 异步执行
│   │   └── builtin/             # 内置工具
│   │       ├── calculator.py    # 计算器
│   │       ├── search.py        # 搜索
│   │       └── rag_tool.py      # RAG 工具
│   │
│   ├── memory/                  # 内存系统
│   │   ├── base.py              # 基础类和配置
│   │   ├── manager.py           # 内存管理器
│   │   ├── embedding.py         # 嵌入模型
│   │   ├── types/               # 四种记忆类型
│   │   │   ├── working.py
│   │   │   ├── episodic.py
│   │   │   ├── semantic.py
│   │   │   └── perceptual.py
│   │   └── storage/             # 存储后端
│   │       ├── qdrant_store.py
│   │       ├── neo4j_store.py
│   │       └── document_store.py
│   │
│   └── __init__.py              # 包导出
│
├── test_the_yu_agent/           # 测试
│   ├── test_memory.py           # 内存测试
│   └── test_rag.py              # RAG 测试
│
├── setup.py                     # 包配置
├── requirements.txt             # 依赖
├── .env                         # 环境配置
└── README.md                    # 项目文档
```

## 核心概念

### 1. 消息系统

**文件**: `core/message.py`

```python
Message(
    content: str,                    # 消息文本
    role: "user"|"assistant"|"system"|"tool",
    timestamp: datetime,             # 自动填充
    metadata: Dict[str, Any]         # 可选追踪信息
)
```

**特点**:
- 基于 Pydantic v2 验证
- `to_dict()` 方法转换为 OpenAI 格式
- 支持任意元数据

### 2. 统一 LLM 客户端

**文件**: `core/llm.py`

**支持的提供商**:
- OpenAI (gpt-4, gpt-3.5-turbo)
- DeepSeek (deepseek-chat)
- Qwen (qwen-turbo, qwen-max)
- ModelScope (多个模型)
- Kimi (moonshot-v1)
- Zhipu (glm-3-turbo, glm-4)
- Ollama (本地模型)
- vLLM (本地推理)

**自动检测逻辑**:
1. 检查提供商特定环境变量
2. 分析 API 密钥格式
3. 检查 base_url 模式
4. 回退到通用变量

**方法**:
```python
llm = AgentsLLM()

# 流式响应
for chunk in llm.think(messages, temperature=0.7):
    print(chunk, end="", flush=True)

# 非流式
result = llm.invoke(messages)
```

### 3. Agent 基类架构

**文件**: `core/agent.py`

**核心特性**:
- 抽象基类强制实现 `run()` 方法
- 共享历史记录管理
- 内存中的对话追踪（不持久化）

**共享方法**:
```python
agent.add_message(message)         # 添加消息
agent.get_history()                # 获取历史副本
agent.clear_history()              # 清空历史
```

### 4. 工具系统架构

**Tool 基类**:
```python
class Tool(ABC):
    @abstractmethod
    def run(self, parameters: Dict[str, Any]) -> str:
        """执行工具"""
        pass

    @abstractmethod
    def get_parameters(self) -> List[ToolParameter]:
        """获取参数定义"""
        pass

    def to_dict(self) -> Dict:
        """序列化供 LLM 使用"""
        pass
```

**工具注册表**:
```python
registry = ToolRegistry()

# 注册 Tool 对象
registry.register_tool(MyTool())

# 注册函数
registry.register_function("my_func", "描述", my_function)

# 执行
result = registry.execute_tool("my_func", "input")

# 获取工具列表
tools = registry.get_tools_description()
```

---

# 开发指南

## 创建自定义 Agent

```python
from yu_agent.core.agent import Agent
from yu_agent.core.llm import AgentsLLM
from yu_agent.core.message import Message

class MyAgent(Agent):
    def __init__(self, name: str, llm: AgentsLLM):
        super().__init__(name, llm)
        self.system_prompt = "你是一个有帮助的助手"

    def run(self, input_text: str) -> str:
        # 添加用户消息
        self.add_message(Message(
            content=input_text,
            role="user"
        ))

        # 构建消息列表
        messages = [
            Message(content=self.system_prompt, role="system"),
            *self.history
        ]

        # 调用 LLM
        response = self.llm.invoke(messages)

        # 保存助手回复
        self.add_message(Message(
            content=response,
            role="assistant"
        ))

        return response
```

## 创建自定义工具

```python
from yu_agent.tools.base import Tool, ToolParameter

class WeatherTool(Tool):
    def run(self, parameters: dict) -> str:
        city = parameters.get("city")

        # 你的实现
        weather = get_weather_from_api(city)

        return f"{city} 的天气是: {weather}"

    def get_parameters(self):
        return [
            ToolParameter(
                name="city",
                type="string",
                description="城市名称",
                required=True
            )
        ]

# 使用
from yu_agent import global_registry

tool = WeatherTool()
global_registry.register_tool(tool)

# 现在 Agent 可以调用它
agent = ReActAgent("天气助手", global_registry=global_registry)
result = agent.run("北京的天气怎么样?")
```

## 扩展内存系统

```python
from yu_agent.memory.base import BaseMemory, MemoryItem, MemoryConfig

class MyCustomMemory(BaseMemory):
    def __init__(self, config: MemoryConfig):
        super().__init__(config)
        self.memories = []

    def add(self, memory_item: MemoryItem) -> str:
        self.memories.append(memory_item)
        return memory_item.id

    def retrieve(self, query: str, limit: int = 5, **kwargs):
        # 实现你的检索逻辑
        return self.memories[:limit]

    def update(self, memory_id: str, updates: dict) -> bool:
        # 实现更新逻辑
        return True

    def delete(self, memory_id: str) -> bool:
        # 实现删除逻辑
        return True

    def get_all(self):
        return self.memories
```

---

# API 参考

## Agent 类

### SimpleAgent

```python
agent = SimpleAgent(
    name: str,
    llm: AgentsLLM,
    system_prompt: str = "You are a helpful assistant"
)

# 非流式
result = agent.run(input_text: str) -> str

# 流式
for chunk in agent.stream_run(input_text: str) -> Iterator[str]:
    print(chunk, end="", flush=True)
```

### ReActAgent

```python
agent = ReActAgent(
    name: str,
    llm: AgentsLLM,
    tool_registry: ToolRegistry,
    max_steps: int = 5,
    system_prompt: str = "..."
)

result = agent.run(input_text: str) -> str
```

### ReflectionAgent

```python
agent = ReflectionAgent(
    name: str,
    llm: AgentsLLM,
    max_iterations: int = 3
)

result = agent.run(input_text: str) -> str
```

### PlanAndSolveAgent

```python
agent = PlanAndSolveAgent(
    name: str,
    llm: AgentsLLM
)

result = agent.run(input_text: str) -> str
```

## 内存类

### MemoryManager

```python
manager = MemoryManager(
    config: MemoryConfig,
    user_id: str,
    enable_working: bool = True,
    enable_episodic: bool = False,
    enable_semantic: bool = False,
    enable_perceptual: bool = False
)

# 添加记忆
manager.add_memory(
    content: str,
    memory_type: str,
    importance: float = 0.5,
    metadata: dict = None
) -> str

# 检索记忆
results = manager.retrieve_memories(
    query: str,
    memory_types: List[str] = None,
    limit: int = 5,
    min_importance: float = 0.0
) -> List[MemoryItem]

# 获取统计
stats = manager.get_memory_stats() -> dict
```

## 工具类

### SearchTool

```python
from yu_agent import search

result = search(query: str) -> str
# 自动选择 Tavily (优先) 或 SerpAPI
```

### CalculatorTool

```python
from yu_agent import calculate

result = calculate(expression: str) -> str
# 支持: +, -, *, /, **, ^, sqrt, sin, cos, tan, log, exp
```

### RAGTool

```python
from yu_agent import RAGTool

rag = RAGTool()

# 添加文档
rag.add_document(file_path: str, namespace: str = "default")

# 添加文本
rag.add_text(text: str, namespace: str = "default")

# 智能问答
answer = rag.ask(question: str, namespace: str = "default") -> str

# 搜索
results = rag.search(query: str, limit: int = 5, namespace: str = "default")

# 获取统计
stats = rag.stats(namespace: str = "default") -> dict

# 清空
rag.clear(namespace: str = "default")
```

---

# 贡献者指南

## 代码风格

- 使用 Python 3.10+ 特性
- 类型提示（必需）
- Docstrings（必需）
- 遵循 PEP 8

## 提交流程

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 测试要求

```bash
# 运行所有测试
python test_the_yu_agent/test_memory.py
python test_the_yu_agent/test_rag.py

# 预期: 所有关键测试通过
```

## 文档要求

- 更新相关 README
- 添加代码注释
- 更新 CLAUDE.md
- 提供使用示例

## 报告 Bug

在 GitHub Issues 中包含:
1. Bug 描述
2. 重现步骤
3. 预期行为
4. 实际行为
5. 系统信息

## 功能请求

在 GitHub Issues 中描述:
1. 用例
2. 期望的 API
3. 实现建议
4. 优先级

---

# 高级主题

## 流式 vs 非流式

### 非流式（等待完整响应）

```python
response = agent.run("问题")
print(response)
```

**优点**:
- 实现简单
- 完整性有保证

**缺点**:
- 用户体验差
- 等待时间长

### 流式（逐令牌输出）

```python
for chunk in agent.stream_run("问题"):
    print(chunk, end="", flush=True)
```

**优点**:
- 实时反馈
- 更好的 UX
- 感觉更快

**缺点**:
- 实现复杂
- 难以编辑之前的输出

## 异步执行

```python
from yu_agent.tools.async_executor import AsyncToolExecutor

async def main():
    async with AsyncToolExecutor(registry) as executor:
        # 并行运行多个工具
        tasks = [
            ("calculator", "2+2"),
            ("search", "AI news"),
        ]
        results = await executor.execute_tools_parallel(tasks)

        for result in results:
            print(result)

import asyncio
asyncio.run(main())
```

## 工具链

```python
from yu_agent.tools.chain import ToolChain

chain = ToolChain()
chain.add_step("search", "查找关于{topic}的信息", "search_result")
chain.add_step("calculator", "根据{search_result}计算", "calc_result")

result = chain.execute(registry, {"topic": "AI", "equation": "2+2"})
```

---

# 参考资源

## 官方文档
- [OpenAI API 文档](https://platform.openai.com/docs)
- [Pydantic 文档](https://docs.pydantic.dev/)
- [Neo4j 文档](https://neo4j.com/docs/)
- [Qdrant 文档](https://qdrant.tech/documentation/)

## 学习资源
- 《Hello Agents》电子书
- [Claude API 指南](https://www.anthropic.com/)
- [Hugging Face Transformers](https://huggingface.co/docs/transformers/)

## 相关项目
- [LangChain](https://langchain.com/)
- [LlamaIndex](https://www.llamaindex.ai/)
- [AutoGen](https://microsoft.github.io/autogen/)

---

# 版本历史

## v0.2.0 (2026-02-13)

**新增**:
- ✅ 嵌入模型配置修复
- ✅ MemoryItem 比较方法
- ✅ 日志输出优化
- ✅ 完整文档

**改进**:
- ✅ 错误处理更清晰
- ✅ 启动脚本
- ✅ 故障排查指南

## v0.1.1 (初始版本)

**特性**:
- 基础 Agent 框架
- 工具系统
- 内存系统
- RAG 工具

---

# 许可证

MIT License

Copyright (c) 2026 yu_agent

---

**编译完成**: 2026-02-13
**总行数**: 600+ 行
**涵盖文件**: 11 个 markdown 文档
**建议阅读**: Part1 (快速开始) → Part2 (深入学习)

