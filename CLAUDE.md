# CLAUDE.md

本文件为Claude Code (claude.ai/code)在本仓库工作时提供指导。

## 项目概述

**yu_agent** 是一个学习阶段的Agent框架实现，基于《Hello Agents》教科书的设计模式，构建在OpenAI兼容API之上。它为多个LLM提供商提供统一接口，并实现了四种核心Agent推理模式：简单对话(Simple)、推理+行动(ReAct)、自我反思(Reflection)和计划求解(PlanAndSolve)。

**核心理念**：简洁性配合可扩展性。每个组件都可独立使用；Agent可以使用工具也可以不使用。框架优先考虑清晰度而不是过度抽象。

**版本**：0.1.1 | **Python要求**：>= 3.10 | **License**：MIT

## 仓库结构

```
yu_agent/
├── yu_agent/                    # 主包
│   ├── core/                    # 基础组件
│   │   ├── agent.py             # Agent抽象基类（包含历史记录管理）
│   │   ├── llm.py               # 统一LLM客户端(AgentsLLM)
│   │   ├── message.py           # 消息数据模型(Pydantic)
│   │   ├── config.py            # 配置管理
│   │   └── exceptions.py         # 异常层级
│   ├── agents/                  # Agent模式实现
│   │   ├── simple_agent.py      # 基础对话(支持流式/非流式)
│   │   ├── react_agent.py       # 推理+行动模式（带工具调用）
│   │   ├── reflection_agent.py  # 自我反思&优化循环
│   │   └── plan_solve_agent.py  # 计划分解+执行
│   ├── tools/                   # 工具系统
│   │   ├── base.py              # Tool抽象类和ToolParameter
│   │   ├── registry.py          # 中央工具注册和执行
│   │   ├── chain.py             # 工具流水线(链式执行多个工具)
│   │   ├── async_executor.py    # 并发工具执行(asyncio)
│   │   └── builtin/             # 内置工具实现
│   │       ├── calculator.py    # 数学计算(基于AST的安全求值)
│   │       └── search.py        # 网络搜索(Tavily/SerpAPI后端)
│   ├── __init__.py              # 包导出
│   └── version.py               # 版本元数据
├── setup.py                     # 包配置
├── requirements.txt             # 依赖列表
└── .vscode/                     # VS Code设置
```

## 开发命令

### 安装依赖

```bash
# 以开发模式安装(可编辑)
pip install -e .

# 仅安装依赖
pip install -r requirements.txt

# 安装所有可选搜索后端
pip install -e ".[search]"
```

### 运行示例

```bash
# 运行简单对话Agent
python -c "from yu_agent import SimpleAgent, AgentsLLM; \
agent = SimpleAgent('测试', AgentsLLM()); \
print(agent.run('你好，你怎么样？'))"

# 测试ReAct Agent（带工具）
python -c "from yu_agent import ReActAgent, global_registry, AgentsLLM; \
registry = global_registry; \
agent = ReActAgent('求解器', AgentsLLM(), registry); \
print(agent.run('计算 2**10 + 15 等于多少？'))"

# 测试流式响应
python -c "from yu_agent import SimpleAgent, AgentsLLM; \
agent = SimpleAgent('聊天', AgentsLLM()); \
for chunk in agent.stream_run('生成一个故事'): \
    print(chunk, end='', flush=True)"
```

### 测试和调试

```bash
# Python调试器
python -m pdb script.py

# 检查导入和模块结构
python -c "import yu_agent; print(yu_agent.__version__); print(dir(yu_agent))"

# 验证配置(显示检测到的提供商)
python -c "from yu_agent import AgentsLLM; llm = AgentsLLM(); \
print(f'提供商: {llm.provider}, 模型: {llm.model}')"

# 测试工具注册表
python -c "from yu_agent import global_registry; print(global_registry.list_tools())"
```

## 核心概念与架构

### 1. 消息系统（基础）

**文件**：`core/message.py`

```python
Message(
    content: str,                    # 消息文本内容
    role: "user"|"assistant"|"system"|"tool",  # OpenAI API兼容
    timestamp: datetime,             # 自动填充
    metadata: Dict[str, Any]         # 可选追踪信息
)
```

**关键**：使用Pydantic验证。方法`to_dict()`转换为OpenAI API格式(仅包含role和content)。

### 2. 统一LLM客户端(AgentsLLM)

**文件**：`core/llm.py`

**核心设计**：单一接口支持8+个提供商：
- OpenAI、DeepSeek、Qwen(阿里DashScope)、ModelScope、Kimi(Moonshot)、Zhipu(GLM)、Ollama、vLLM

**提供商自动检测逻辑**：
1. 检查提供商特定的环境变量(OPENAI_API_KEY、DEEPSEEK_API_KEY、DASHSCOPE_API_KEY等)
2. 分析API密钥格式(`ms-`前缀 → ModelScope)
3. 检查base_url模式
4. 回退到通用LLM_*变量或默认值

**环境变量**(优先级从高到低)：
```
# 通用变量
LLM_MODEL_ID        # 模型名称(例如: "gpt-4o-mini")
LLM_API_KEY         # 通用API密钥
LLM_BASE_URL        # API端点(https://api.openai.com/v1)
LLM_TIMEOUT         # 请求超时(秒，默认: 60)

# 提供商特定(优先级更高)
OPENAI_API_KEY
DEEPSEEK_API_KEY
DASHSCOPE_API_KEY
MODELSCOPE_API_KEY
KIMI_API_KEY / MOONSHOT_API_KEY
ZHIPU_API_KEY / GLM_API_KEY
OLLAMA_API_KEY / OLLAMA_HOST
VLLM_API_KEY / VLLM_HOST
```

**方法**：
```python
llm.think(messages, temperature) -> Iterator[str]     # 流式响应
llm.invoke(messages) -> str                            # 非流式
llm.stream_invoke(messages) -> Iterator[str]          # think的别名
```

### 3. Agent基类架构

**文件**：`core/agent.py`

**抽象模式**：所有Agent继承自`Agent`(ABC)。强制实现`run(input_text: str) -> str`方法。

**共享属性**：
- `self.history: list[Message]` - 对话记忆(当前进程内存，不持久化)
- `self.llm: AgentsLLM` - LLM客户端实例
- `self.system_prompt: str` - 系统指令
- `self.config: Config` - 配置对象

**共享方法**：
```python
add_message(message: Message)      # 添加消息到历史
get_history() -> list[Message]     # 获取历史的浅拷贝
clear_history()                    # 清空历史列表
```

**关键设计决策**：历史记录**默认不持久化**。Chapter8的内存模块解决这个问题。

### 4. Agent模式实现

#### SimpleAgent（基础对话）

**文件**：`agents/simple_agent.py`

**模式**：直接LLM调用，保留历史

```
run(输入文本) → 构建[系统提示 + 历史 + 用户输入] → LLM → 保存到历史 → 返回
stream_run(输入文本) → 同上但实时产生响应块
```

**使用场景**：聊天机器人、问答系统、通用对话

#### ReActAgent（推理+行动）

**文件**：`agents/react_agent.py`

**模式**：迭代循环，支持工具调用

```
循环直到完成:
  1. LLM生成"思考" + "行动[工具名[输入]]"
  2. 使用正则表达式解析: action_pattern = r"Action\s*:\s*(.*?)\s*(?:\n|$)"
  3. 从格式"工具名[参数]"提取工具名和输入
  4. 通过工具注册表执行工具
  5. 将观察结果追加到历史
  6. 循环(max_steps默认值: 5)
  7. 解析"完成[答案]"停止并返回
```

**集成**：需要将`ToolRegistry`实例传递给构造函数。

**自定义**：构造函数接受`max_steps`、`react_prompt_template`等不同提示词。

#### ReflectionAgent（自我反思循环）

**文件**：`agents/reflection_agent.py`

**模式**：执行 → 反思 → 优化 → 重复

```
1. 初始执行：用任务调用LLM
2. 循环(i = 1 to max_iterations):
   a. 反思：对前一个结果生成批评/反馈
   b. 检查是否需要改进(查找"无需改进"标志)
   c. 如果需要：基于反馈优化前一个响应
   d. 保存执行跟踪到内部Memory对象
3. 返回最终优化结果
```

**记忆跟踪**：内部`Memory`类存储执行历史和反思。

**自定义提示词**：提示词模板字典(`"initial"`、`"reflect"`、`"refine"`)

**使用场景**：代码生成、文档编写、需要质量保证的复杂分析

#### PlanAndSolveAgent（分层分解）

**文件**：`agents/plan_solve_agent.py`

**两阶段架构**：

1. **规划阶段**：
   - LLM生成步骤化计划
   - 必须返回三反引号块中的Python列表：`` ```python [...] ``` ``
   - 使用`ast.literal_eval()`解析

2. **执行阶段**：
   - 对每一步，提供上下文(完整计划、前期结果)
   - LLM每次解决一步
   - 积累结果

```
run(输入文本):
  plan = 规划器.plan(问题)  # → ["步骤1: ...", "步骤2: ...", ...]
  answer = 执行器.execute(问题, plan)  # 逐步执行
  return answer
```

**使用场景**：多步数学问题、复杂推理、流程性任务

### 5. 工具系统架构

#### Tool基类

**文件**：`tools/base.py`

```python
class ToolParameter(BaseModel):
    name: str
    type: str              # "string"、"number"等
    description: str
    required: bool
    default: Any

class Tool(ABC):
    @abstractmethod
    def run(self, parameters: Dict[str, Any]) -> str

    @abstractmethod
    def get_parameters(self) -> List[ToolParameter]

    def validate_parameters(params) -> bool  # 检查必需参数
    def to_dict() -> Dict                    # 序列化供LLM使用
```

**扩展点**：通过继承`Tool`创建自定义工具。

#### 工具注册表

**文件**：`tools/registry.py`

**设计**：中央注册表，支持`Tool`对象和普通函数两种方式。

```python
registry = ToolRegistry()

# 注册Tool对象(推荐)
registry.register_tool(CalculatorTool())
registry.register_tool(SearchTool())

# 或注册函数(便利方式)
registry.register_function("my_tool", "描述", my_function)

# 执行
result = registry.execute_tool("calculator", "2**10")

# 工具列表
registry.get_tools_description()  # 格式化供LLM使用
registry.list_tools()             # 列出所有工具名
```

**全局实例**：`yu_agent.global_registry` - 预配置的内置工具

**执行逻辑**：
1. 按名称查找工具
2. Tool对象优先于函数工具
3. 将输入作为`{"input": input_text}`传递
4. 返回字符串结果
5. 捕获并格式化异常

#### 内置工具

**计算器**(`tools/builtin/calculator.py`)：
- 运算符：`+, -, *, /, **, ^`
- 函数：`abs, round, max, min, sum`
- 数学：`sqrt, sin, cos, tan, log, exp`
- 常数：`pi, e`
- 实现：基于AST的安全求值(无`eval()`安全风险)

**搜索**(`tools/builtin/search.py`)：
- 双后端：Tavily API(首选) + SerpAPI(备选)
- Tavily：AI优化结果，答案 + 3个来源
- SerpAPI：Google搜索，答案框 + 知识图
- 基于环境变量自动检测

```python
# 搜索环境变量
TAVILY_API_KEY        # 首选
SERPAPI_API_KEY       # 备选

# 使用
from yu_agent import search, SearchTool
result = search("查询")  # 使用混合模式(Tavily → SerpAPI)
```

#### 工具链式执行

**文件**：`tools/chain.py`

**模式**：用变量替换链接多个工具

```python
chain = ToolChain()
chain.add_step("search", "查找关于{话题}的信息", "search_result")
chain.add_step("calculator", "根据{search_result}计算{方程}", "calc_result")

result = chain.execute(registry, {"话题": "AI", "方程": "2+2"})
```

**内置链**：`create_research_chain()`、`create_simple_chain()`

#### 异步工具执行

**文件**：`tools/async_executor.py`

**目的**：多个工具并发执行

```python
async with AsyncToolExecutor(registry, max_workers=4) as executor:
    # 并行运行不同工具
    tasks = [
        ("calculator", "2+2"),
        ("search", "AI新闻"),
        ("calculator", "10*5")
    ]
    results = await executor.execute_tools_parallel(tasks)

    # 或并行运行同一工具多次
    results = await executor.execute_tools_batch("calculator", ["2+2", "3*3", "5-1"])
```

**同步包装器**：`run_parallel_tools_sync()`、`run_batch_tool_sync()`

### 6. 配置系统

**文件**：`core/config.py`

```python
Config(
    default_model: str,           # "gpt-3.5-turbo"
    default_provider: str,        # "openai"
    temperature: float,           # 0.7
    max_tokens: Optional[int],
    debug: bool,                  # False
    log_level: str,               # "INFO"
    max_history_length: int       # 1000
)
```

**创建方式**：`Config.from_env()`从环境变量加载

### 7. 异常层级

**文件**：`core/exceptions.py`

```python
AgentsException
├── LLMException        # LLM相关失败
├── AgentException      # Agent初始化或执行错误
├── ConfigException     # 配置问题
└── ToolException       # 工具注册或执行错误
```

## 关键设计模式

### 1. 惰性加载
**位置**：`core/__init__.py`

使用`__getattr__`按需导入，避免循环依赖。

### 2. 抽象基类
- `Agent` - 强制实现`run()`
- `Tool` - 强制实现`run()`和`get_parameters()`

### 3. 工厂模式
- `Config.from_env()` - 从环境变量创建配置
- 工具便利函数 - `search()`、`calculate()`按需创建实例

### 4. 注册表模式
- `ToolRegistry` - 中央工具管理
- `global_registry` - 全局单例

### 5. 适配器模式
- `AgentsLLM` - 适配8+个LLM提供商到统一接口

### 6. 提供商策略模式
- 自动检测逻辑选择适当的提供商实现
- 每个提供商有不同的凭证要求和base_url

### 7. 流式模式
- 基于生成器(`yield`)实现逐令牌响应
- `think()`返回`Iterator[str]`提供实时UX

## 常见开发模式

### 创建自定义工具

```python
from yu_agent.tools.base import Tool, ToolParameter

class MyTool(Tool):
    def run(self, parameters: dict) -> str:
        # parameters["input"]包含用户输入
        return "结果"

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(name="input", type="string", description="用户输入", required=True)
        ]

# 注册并使用
registry.register_tool(MyTool())
agent = ReActAgent("agent", llm, registry)
```

### 使用多个Agent

```python
llm = AgentsLLM()
agent1 = SimpleAgent("聊天", llm)
agent2 = ReActAgent("求解器", llm, registry)

response1 = agent1.run("你好")
response2 = agent2.run("计算2+2")
```

### 流式响应

```python
agent = SimpleAgent("聊天", llm)

# 实时流式输出令牌
for chunk in agent.stream_run("生成一个故事"):
    print(chunk, end="", flush=True)
print()
```

### 错误处理

```python
from yu_agent import AgentException, AgentsException, ToolException

try:
    agent = ReActAgent("求解器", llm, registry)
    result = agent.run("问题")
except AgentException as e:
    print(f"Agent错误: {e}")
except ToolException as e:
    print(f"工具错误: {e}")
except AgentsException as e:
    print(f"框架错误: {e}")
```

## Chapter8内存模块的集成点

Chapter8内存模块应该钩入以下位置：

1. **Agent历史访问**：`agent.get_history()`返回`list[Message]`
2. **消息添加**：每次交互时调用`agent.add_message(Message)`
3. **Agent初始化**：在第一次`run()`前加载持久化历史
4. **消息序列化**：使用`message.to_dict()`存储
5. **配置集成**：通过`config`参数传递内存后端

**关键挑战**：当前`Agent`基类有`_history`属性(私有)，但`SimpleAgent`引用`self.history` - 需要验证此实现细节。

## 依赖列表

**核心依赖**：
- `openai==2.18.0` - LLM客户端
- `pydantic==2.12.5` - 数据验证和设置
- `tavily==1.1.0` - 网络搜索API客户端
- `serpapi==0.1.5` - Google搜索API客户端

**可选**：
- `google_search_results==2.4.2` - 替代Google搜索

**Python**：>= 3.10(需要现代类型提示)

## 环境配置(快速参考)

```bash
# 在项目根目录创建.env文件
cat > .env << EOF
LLM_MODEL_ID=gpt-4o-mini
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.openai.com/v1
LLM_TIMEOUT=60
TAVILY_API_KEY=tvly-...
SERPAPI_API_KEY=...
EOF

# 加载并验证
python -c "from yu_agent import AgentsLLM; llm = AgentsLLM(); \
print(f'{llm.provider}: {llm.model}')"
```

## 测试方法

添加新功能时：

1. **测试Agent实现**：创建测试脚本验证`run()`行为
2. **测试工具集成**：验证工具正确执行并返回预期格式
3. **测试历史管理**：检查消息被添加和可检索
4. **测试提供商切换**：验证不同LLM提供商工作正常
5. **测试错误情况**：捕获异常和无效输入优雅处理

## 贡献者注意事项

- **循环依赖**：如果添加核心模块，在`__getattr__`中使用惰性导入
- **流式支持**：Agent的`run()`方法始终支持流式和非流式两种方式
- **Pydantic**：使用v2语法(已在requirements中)
- **类型提示**：需要Python 3.10+特性
- **私有方法**：`_`前缀的方法是私有的(例如`_auto_detect_provider()`)
- **工具参数**：执行前始终使用`validate_parameters()`验证
- **异常层级**：使用`core/exceptions.py`中的特定异常类型
- **文档**：为公共方法和类包含文档字符串
