# yu_agent - 多模式智能体框架

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-0.1.1-brightgreen.svg)](#)

**yu_agent** 是一个基于《Hello Agents》教科书设计模式的学习阶段智能体框架。它提供了统一的LLM接口、多种Agent推理模式和灵活的工具系统，帮助你快速构建智能应用。

## ✨ 核心特性

- 🤖 **多种Agent模式**：Simple(简单对话) / ReAct(推理+行动) / Reflection(自我反思) / PlanAndSolve(计划求解)
- 🌐 **8+个LLM提供商支持**：OpenAI / DeepSeek / Qwen / ModelScope / Kimi / Zhipu / Ollama / vLLM
- 🔌 **灵活工具系统**：内置计算器、搜索工具和RAG工具，支持自定义工具扩展
- 🔄 **流式响应支持**：实时流式输出，更好的用户体验
- 🧠 **完整记忆系统**：4种记忆类型(工作/情景/语义/感知) + 多数据库支持(SQLite/Qdrant/Neo4j)
- 📚 **RAG检索增强生成**：支持多格式文档、智能检索、向量化存储、增强问答
- ⚡ **异步执行**：支持工具并发执行和流水线组合

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/xiaoyu-ops/agent.git
cd yu_agent

# 安装依赖
pip install -e .

# 或仅安装依赖包
pip install -r requirements.txt
```

### 基础使用

#### 1. 简单对话Agent

```python
from yu_agent import SimpleAgent, AgentsLLM

# 创建LLM客户端
llm = AgentsLLM()

# 创建Agent
agent = SimpleAgent(name="助手", llm=llm)

# 运行对话
response = agent.run("你好，请介绍一下自己")
print(response)
```

#### 2. ReAct推理+行动Agent

```python
from yu_agent import ReActAgent, global_registry, AgentsLLM

# 创建Agent
llm = AgentsLLM()
agent = ReActAgent(
    name="求解器",
    llm=llm,
    tool_registry=global_registry  # 使用全局工具注册表
)

# 执行带工具的任务
result = agent.run("计算 2**10 + 15 * 3 等于多少？")
print(result)
```

#### 3. 自我反思Agent

```python
from yu_agent import ReflectionAgent, AgentsLLM

llm = AgentsLLM()
agent = ReflectionAgent(
    name="优化助手",
    llm=llm,
    max_iterations=3  # 最多迭代3次
)

# 自动优化结果质量
result = agent.run("写一个Python快速排序算法")
print(result)
```

#### 4. 计划求解Agent

```python
from yu_agent import PlanAndSolveAgent, AgentsLLM

llm = AgentsLLM()
agent = PlanAndSolveAgent(
    name="规划师",
    llm=llm
)

# 自动分解问题并逐步求解
result = agent.run("如何制定一个有效的学习计划？")
print(result)
```

### 流式响应

```python
from yu_agent import SimpleAgent, AgentsLLM

agent = SimpleAgent("聊天", AgentsLLM())

# 实时流式输出响应
for chunk in agent.stream_run("生成一个故事"):
    print(chunk, end="", flush=True)
print()
```

## 📚 详细文档

### 环境配置

在项目根目录创建 `.env` 文件：

```bash
# 基础配置
LLM_MODEL_ID=gpt-4o-mini
LLM_API_KEY=sk-your-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_TIMEOUT=60

# 搜索工具（可选）
TAVILY_API_KEY=tvly-your-key
SERPAPI_API_KEY=your-serpapi-key
```

### LLM提供商支持

| 提供商 | 环境变量 | Base URL示例 |
|-------|--------|-----------|
| OpenAI | `OPENAI_API_KEY` | `https://api.openai.com/v1` |
| DeepSeek | `DEEPSEEK_API_KEY` | `https://api.deepseek.com/v1` |
| Qwen(阿里) | `DASHSCOPE_API_KEY` | `https://dashscope.aliyuncs.com/api/v1` |
| ModelScope | `MODELSCOPE_API_KEY` | `https://api-inference.modelscope.cn/v1` |
| Kimi(Moonshot) | `KIMI_API_KEY` | `https://api.moonshot.cn/v1` |
| Zhipu(GLM) | `ZHIPU_API_KEY` | `https://open.bigmodel.cn/api/paas/v4` |
| Ollama | `OLLAMA_HOST` | `http://localhost:11434/v1` |
| vLLM | `VLLM_API_KEY` | `http://localhost:8000/v1` |

自动检测顺序：
1. 检查提供商特定的环境变量
2. 分析API密钥格式
3. 检查base_url模式
4. 回退到通用LLM_*变量

### Agent模式详解

#### SimpleAgent - 基础对话

**适用场景**：聊天机器人、问答系统、通用对话

```python
from yu_agent import SimpleAgent, AgentsLLM

agent = SimpleAgent(
    name="聊天助手",
    llm=AgentsLLM(),
    system_prompt="你是一个友善的AI助手。",  # 自定义系统提示
    # config=...  # 可选配置
)

# 保留对话历史
response1 = agent.run("我叫张三")
response2 = agent.run("我的名字是什么？")  # 会记得张三

# 查看历史
history = agent.get_history()
for msg in history:
    print(f"[{msg.role}] {msg.content}")
```

#### ReActAgent - 推理与行动

**适用场景**：需要调用工具的问题、信息查询、计算任务

```python
from yu_agent import ReActAgent, ToolRegistry, AgentsLLM
from yu_agent.tools.builtin import CalculatorTool, SearchTool

# 创建工具注册表
registry = ToolRegistry()
registry.register_tool(CalculatorTool())
registry.register_tool(SearchTool())

# 创建Agent
agent = ReActAgent(
    name="专家",
    llm=AgentsLLM(),
    tool_registry=registry,
    max_steps=5,  # 最多执行5步
    custom_prompt="自定义提示词"  # 可选
)

# 执行任务
result = agent.run("当前AI的发展趋势如何？")
```

**ReAct执行流程**：
```
用户问题
    ↓
思考(Thought) - LLM分析问题
    ↓
行动(Action) - 选择工具或Finish
    ↓
    ├─ 调用工具 → 观察结果 → 更新历史 → 循环
    └─ Finish[答案] → 返回结果
```

#### ReflectionAgent - 自我反思

**适用场景**：代码生成、文档写作、需要质量保证的任务

```python
from yu_agent import ReflectionAgent, AgentsLLM

agent = ReflectionAgent(
    name="编写助手",
    llm=AgentsLLM(),
    max_iterations=3,  # 最多优化3轮
    custom_prompts={  # 自定义提示词
        "initial": "写一个{task}",
        "reflect": "批评这个{content}",
        "refine": "基于反馈改进：{feedback}"
    }
)

# 自动迭代优化
result = agent.run("Python字典合并的最佳实践")
```

**执行流程**：
```
初始执行
    ↓
反思评价 → 检查是否需要改进
    ↓
    ├─ 无需改进 → 返回
    └─ 需要改进 → 精化 → 保存跟踪 → 循环
```

#### PlanAndSolveAgent - 计划分解

**适用场景**：复杂的多步任务、数学问题、系统性问题

```python
from yu_agent import PlanAndSolveAgent, AgentsLLM

agent = PlanAndSolveAgent(name="规划师", llm=AgentsLLM())

result = agent.run("如何高效学习一门新技能？")
```

**执行流程**：
```
问题
    ↓
规划阶段: LLM生成步骤列表
    ↓
    ```python
    [
        "第一步：了解学习目标和资源",
        "第二步：制定学习计划",
        ...
    ]
    ```
    ↓
执行阶段: 逐步解决每个子问题
    ↓
最终答案
```

### 工具系统

#### 内置工具

**计算器**
```python
from yu_agent import calculate

result = calculate("2**10 + sqrt(16)")
# 支持: +, -, *, /, **, sqrt, sin, cos, tan, log, exp, pi, e 等
```

**搜索**
```python
from yu_agent import search

result = search("Python最新版本")
# 自动选择: Tavily API(首选) > SerpAPI(备选)
```

**RAG (检索增强生成)**
```python
from yu_agent.tools.builtin.rag_tool import RAGTool

# 初始化RAG工具
rag = RAGTool(
    knowledge_base_path="./knowledge_base",
    collection_name="my_rag",
    rag_namespace="default"
)

# 添加文档（支持PDF、Word、Excel等多格式）
rag.add_document("report.pdf")

# 添加文本
rag.add_text("Python是一种高级编程语言...")

# 智能问答 - 自动检索+LLM生成答案
answer = rag.ask("什么是Python？")

# 知识库搜索
results = rag.search("编程语言", limit=5)

# 查看统计信息
stats = rag.run({"action": "stats"})

# 批量添加文档
rag.add_documents_batch(["file1.pdf", "file2.pdf"])

# 清空知识库
rag.run({"action": "clear", "confirm": True})
```

#### 自定义工具

```python
from yu_agent.tools.base import Tool, ToolParameter

class MyTool(Tool):
    name = "my_tool"
    description = "我的自定义工具"

    def run(self, parameters: dict) -> str:
        input_text = parameters.get("input", "")
        # 实现你的逻辑
        return f"处理结果: {input_text}"

    def get_parameters(self):
        return [
            ToolParameter(
                name="input",
                type="string",
                description="输入文本",
                required=True
            )
        ]

# 注册并使用
from yu_agent import ReActAgent, ToolRegistry, AgentsLLM

registry = ToolRegistry()
registry.register_tool(MyTool())

agent = ReActAgent("agent", AgentsLLM(), registry)
result = agent.run("使用my_tool处理数据")
```

#### 工具链式执行

```python
from yu_agent.tools.chain import ToolChain
from yu_agent import global_registry

chain = ToolChain()
chain.add_step("search", "搜索关于{topic}的信息", "search_result")
chain.add_step("calculator", "计算{search_result}中提到的数字", "calc_result")

result = chain.execute(global_registry, {"topic": "Python性能"})
```

#### 异步并发执行

```python
import asyncio
from yu_agent.tools.async_executor import AsyncToolExecutor
from yu_agent import global_registry

async def main():
    async with AsyncToolExecutor(global_registry, max_workers=4) as executor:
        # 并行执行不同工具
        tasks = [
            ("calculator", "2+2"),
            ("search", "AI新闻"),
            ("calculator", "10*5")
        ]
        results = await executor.execute_tools_parallel(tasks)
        for result in results:
            print(result)

asyncio.run(main())

# 或使用同步包装
from yu_agent.tools.async_executor import run_parallel_tools_sync
results = run_parallel_tools_sync(global_registry, tasks)
```

### 高级用法

#### 多Agent协作

```python
from yu_agent import SimpleAgent, ReActAgent, global_registry, AgentsLLM

llm = AgentsLLM()

# Agent 1: 信息收集
researcher = SimpleAgent("研究员", llm)
research_result = researcher.run("总结AI的最新进展")

# Agent 2: 信息处理
analyzer = ReActAgent("分析师", llm, global_registry)
analysis = analyzer.run(f"基于以下信息进行分析：{research_result}")

print(analysis)
```

#### 自定义系统提示

```python
from yu_agent import SimpleAgent, AgentsLLM

system_prompt = """你是一个专业的代码审查专家。
你的职责是：
1. 检查代码的正确性
2. 建议性能优化
3. 提出安全问题

请提供详细的反馈。"""

agent = SimpleAgent("代码审查官", AgentsLLM(), system_prompt=system_prompt)
feedback = agent.run("""
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
""")
print(feedback)
```

#### 自定义配置

```python
from yu_agent import SimpleAgent, AgentsLLM, Config

# 创建自定义配置
config = Config(
    default_model="gpt-4o-mini",
    temperature=0.5,
    max_tokens=2000,
    debug=True,
    log_level="DEBUG"
)

llm = AgentsLLM(temperature=0.3, max_tokens=1000)
agent = SimpleAgent("助手", llm, config=config)
```

### 记忆系统

yu_agent提供完整的分层记忆系统，支持4种核心记忆类型和多种存储后端。

#### 快速开始

```python
from yu_agent import MemoryManager, MemoryConfig

# 创建记忆配置
config = MemoryConfig(
    storage_path="./memory_data",
    max_capacity=1000,
    importance_threshold=0.1
)

# 创建记忆管理器
manager = MemoryManager(config, user_id="user_123")

# 添加记忆
memory_id = manager.add_memory(
    content="用户信息：Alice是一名Python开发者",
    memory_type="semantic",  # 自动分类或显式指定
    importance=0.8,
    metadata={"tags": ["用户", "开发者"]}
)

# 检索记忆
results = manager.retrieve_memories(
    query="Alice的职业",
    limit=5,
    min_importance=0.3
)

for memory in results:
    print(f"内容: {memory.content}")
    print(f"重要性: {memory.importance}")

# 统计信息
stats = manager.get_memory_stats()
print(f"总记忆数: {stats['total_memories']}")
```

#### 4种记忆类型

| 类型 | 用途 | 存储 | 时效 |
|------|------|------|------|
| WorkingMemory | 会话上下文 | 内存 | 分钟级 |
| EpisodicMemory | 交互历史 | SQLite + Qdrant | 天/周级 |
| SemanticMemory | 知识/概念 | Neo4j + Qdrant | 永久 |
| PerceptualMemory | 多模态感知 | 灵活 | 可配置 |

#### 高级功能

```python
# 记忆遗忘策略
forgotten = manager.forget_memories(
    strategy="importance_based",  # 基于重要性
    threshold=0.2  # 删除重要性 < 0.2 的记忆
)

# 或时间基础
forgotten = manager.forget_memories(
    strategy="time_based",
    max_age_days=30  # 删除30天前的记忆
)

# 记忆整合：从短期到长期
consolidated = manager.consolidate_memories(
    from_type="working",
    to_type="episodic",
    importance_threshold=0.7
)

# 多类型混合检索
results = manager.retrieve_memories(
    query="用户问题",
    memory_types=["episodic", "semantic"],  # 多种类型
    limit=10,
    min_importance=0.5
)
```

#### 环境配置

```bash
# 嵌入模型（可选）
EMBED_MODEL_TYPE=dashscope
EMBED_MODEL_NAME=text-embedding-v3
EMBED_API_KEY=your_key

# Qdrant向量数据库
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_key
QDRANT_COLLECTION=memories

# Neo4j图数据库
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# 本地存储
STORAGE_PATH=./memory_data
```

#### 错误处理

```python
from yu_agent import SimpleAgent, AgentsLLM
from yu_agent.core.exceptions import AgentException, LLMException, ToolException

try:
    agent = SimpleAgent("test", AgentsLLM())
    result = agent.run("你好")
except LLMException as e:
    print(f"LLM错误: {e}")
except ToolException as e:
    print(f"工具错误: {e}")
except AgentException as e:
    print(f"Agent错误: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

## 📦 依赖

**核心依赖**：
```
openai==2.18.0              # LLM客户端
pydantic==2.12.5            # 数据验证
tavily==1.1.0               # 搜索API
serpapi==0.1.5              # 备选搜索API
google_search_results==2.4.2  # Google搜索(可选)
python-dotenv               # 环境变量加载
```

**记忆系统依赖**（可选）：
```
qdrant-client>=2.7.0        # 向量数据库
neo4j>=5.13.0               # 图数据库
scikit-learn>=1.3.0         # TF-IDF检索
sentence-transformers>=2.2.0  # 文本嵌入（可选）
dashscope>=1.0.0            # 阿里通义千问（可选）
spacy>=3.7.0                # NLP处理（可选）
```

**快速安装**：
```bash
# 仅核心功能
pip install -e .

# 完整功能（包括记忆和RAG）
pip install -e ".[memory]"

# 或手动安装
pip install qdrant-client neo4j spacy sentence-transformers
python -m spacy download zh_core_web_sm  # 中文NLP模型
```

## 🏗️ 项目结构

```
yu_agent/
├── core/                    # 核心组件
│   ├── agent.py            # Agent基类
│   ├── llm.py              # LLM客户端
│   ├── message.py          # 消息模型
│   ├── config.py           # 配置管理
│   └── exceptions.py        # 异常定义
├── agents/                 # Agent实现
│   ├── simple_agent.py     # 简单对话
│   ├── react_agent.py      # 推理+行动
│   ├── reflection_agent.py # 自我反思
│   └── plan_solve_agent.py # 计划求解
├── tools/                  # 工具系统
│   ├── base.py             # Tool基类
│   ├── registry.py         # 工具注册表
│   ├── chain.py            # 工具链式
│   ├── async_executor.py   # 异步执行
│   └── builtin/            # 内置工具
│       ├── calculator.py
│       └── search.py
├── __init__.py            # 包导出
└── version.py             # 版本信息
```

## 🔧 开发

### 运行示例

```bash
# 简单对话
python -c "from yu_agent import SimpleAgent, AgentsLLM; agent = SimpleAgent('test', AgentsLLM()); print(agent.run('你好'))"

# ReAct推理
python -c "from yu_agent import ReActAgent, global_registry, AgentsLLM; agent = ReActAgent('solver', AgentsLLM(), global_registry); print(agent.run('计算2+2'))"
```

### 调试

```bash
# 启用Python调试器
python -m pdb your_script.py

# 检查模块
python -c "import yu_agent; print(dir(yu_agent))"

# 验证配置
python -c "from yu_agent import AgentsLLM; llm = AgentsLLM(); print(f'{llm.provider}: {llm.model}')"
```

### 测试

```bash
# 创建简单测试脚本
cat > test_basic.py << 'EOF'
from yu_agent import SimpleAgent, AgentsLLM

def test_simple_agent():
    agent = SimpleAgent("test", AgentsLLM())
    response = agent.run("test message")
    assert isinstance(response, str)
    assert len(response) > 0

if __name__ == "__main__":
    test_simple_agent()
    print("✅ 基础测试通过")
EOF

python test_basic.py
```

## 📝 常见问题

### Q: 如何处理API密钥？
A: 使用 `.env` 文件存储敏感信息，框架会自动从环境变量加载：
```bash
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://xxx
```

### Q: 支持本地LLM吗？
A: 支持！可以使用Ollama或vLLM：
```python
llm = AgentsLLM(
    provider="ollama",
    model="llama2",
    base_url="http://localhost:11434/v1"
)
```

### Q: 如何扩展记忆功能？
A: Chapter8项目提供了内存模块实现，可以实现对话持久化。

### Q: Agent支持并发执行吗？
A: 工具系统支持异步并发，Agent本身是顺序执行。使用 `AsyncToolExecutor` 并发执行工具。

### Q: 如何自定义Agent模式？
A: 继承 `Agent` 基类并实现 `run()` 方法。

### Q: 支持哪些LLM？
A: 任何OpenAI兼容的API，包括OpenAI、DeepSeek、Qwen、本地LLM等。

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 👤 作者

Zhuoyang Wu

## 🔗 相关资源

- [Hello Agents教科书](https://github.com/aiwaves-cn/agents)
- [OpenAI API文档](https://platform.openai.com/docs)
- [Pydantic文档](https://docs.pydantic.dev)

## 📞 支持

遇到问题？
- 查看 [CLAUDE.md](./CLAUDE.md) 获取详细的架构文档
- 查看 [BUG_FIXES.md](./BUG_FIXES.md) 了解最近的bug修复
- 提交Issue到项目仓库

---

**祝你使用愉快！** 🚀
