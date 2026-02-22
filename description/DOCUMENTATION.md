# yu_agent 项目文档

## 📚 项目简介

**yu_agent** 是一个基于《Hello Agents》教科书设计模式的学习阶段智能体框架。它提供了统一的LLM接口、多种Agent推理模式和灵活的工具系统，帮助你快速构建智能应用。

### ✨ 核心特性

- 🤖 **多种Agent模式**：Simple(简单对话) / ReAct(推理+行动) / Reflection(自我反思) / PlanAndSolve(计划求解)
- 🌐 **8+个LLM提供商支持**：OpenAI / DeepSeek / Qwen / ModelScope / Kimi / Zhipu / Ollama / vLLM
- 🔌 **灵活工具系统**：内置计算器、搜索工具和RAG工具，支持自定义工具扩展
- 🔄 **流式响应支持**：实时流式输出，更好的用户体验
- 🧠 **完整记忆系统**：4种记忆类型(工作/情景/语义/感知) + 多数据库支持(SQLite/Qdrant/Neo4j)
- 📚 **RAG检索增强生成**：支持多格式文档、智能检索、向量化存储、增强问答
- ⚡ **异步执行**：支持工具并发执行和流水线组合

---

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
```

---

## 🔌 Selenium集成完全方案 ✅

Selenium已经**完全集成到yu_agent框架**中，有两种可用方式：

### 方案1：Tool方式 ⭐⭐⭐⭐⭐（推荐）

**文件**：`tests/test_MCP/test_6_selenium.py`

#### 特点
- ✅ 最稳定、最简单
- ✅ 截图质量最好（12KB+）
- ✅ 支持所有网站
- ✅ WebDriver保持连接
- ✅ 无需额外服务器

#### 运行
```bash
python tests/test_MCP/test_6_selenium.py
```

#### 代码示例
```python
from yu_agent import SimpleAgent, AgentsLLM, global_registry
from yu_agent.tools.selenium_screenshot import SeleniumScreenshotTool

# 创建Agent（必须传递tool_registry！）
agent = SimpleAgent(
    name="浏览器助手",
    llm=AgentsLLM(),
    tool_registry=global_registry  # 关键：需要传递registry
)

# 创建和注册工具
selenium_tool = SeleniumScreenshotTool(headless=True)
global_registry.register_tool(selenium_tool)

# Agent自动调用工具
response = agent.run("""
使用 selenium_screenshot 工具完成以下任务：
1. 访问 https://example.com
2. 等待页面加载完成（wait_time: 10秒）
3. 截图保存为 "screenshot.png"

工具参数应该是：
- url: https://example.com
- output_path: screenshot.png
- wait_time: 10
""")

# 清理资源
selenium_tool.close()
```

#### 工具参数
```python
{
    'url': 'https://example.com',          # 必需：要访问的URL
    'output_path': 'screenshot.png',        # 可选：截图保存路径
    'wait_time': 10,                        # 可选：等待时间（秒，默认10）
    'wait_for_selector': None               # 可选：等待特定元素CSS选择器
}
```

---

### 方案2：MCP Stdio模式 ⭐⭐⭐⭐

**文件**：`tests/test_MCP/test_6.py`

#### 特点
- ✅ 工作稳定（针对简单网站）
- ✅ 支持MCP协议
- ⚠️ 每次调用启动新进程
- ⚠️ 复杂网站可能不完整

#### 运行
```bash
python tests/test_MCP/test_6.py
```

#### 代码示例
```python
from yu_agent import SimpleAgent, AgentsLLM
from yu_agent.tools import MCPTool

agent = SimpleAgent(name="浏览器助手", llm=AgentsLLM())

# 创建MCP工具
selenium_mcp_tool = MCPTool(
    name="selenium",
    server_command=[
        "python",
        "src/yu_agent/protocols/mcp/selenium_server.py"
    ]
)

# 添加工具
agent.add_tool(selenium_mcp_tool)

# Agent自动发现并使用工具
response = agent.run("""
1. 请使用 selenium 工具的 browser_navigate 功能访问: https://example.com
2. 页面打开后，请等待页面完全加载。
3. 请使用 selenium 工具的 browser_screenshot 功能截图保存为 "screenshot.png"
""")
```

#### MCP服务器支持的工具
- `browser_navigate(url, wait_time)` - 导航到URL
- `browser_screenshot(output_path, wait_for_selector)` - 截图
- `browser_click(selector)` - 点击元素
- `browser_fill(selector, text)` - 填写表单
- `browser_close()` - 关闭浏览器
- `get_server_info()` - 获取服务器信息

---

### 关键要点

#### 1. Agent必须传递tool_registry
```python
# ✅ 正确
agent = SimpleAgent(name="助手", llm=llm, tool_registry=global_registry)

# ❌ 错误（工具不会被调用）
agent = SimpleAgent(name="助手", llm=llm)
```

#### 2. WebDriver Chrome路径检测
自动检测以下路径：
- `C:\Program Files\Google\Chrome\Application\chrome.exe`
- `C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`
- Linux: `google-chrome`, `google-chrome-stable`, `chromium`

#### 3. ChromeDriver自动管理
使用`webdriver-manager`自动下载和管理ChromeDriver，无需手动配置。

#### 4. 系统代理处理
所有Selenium相关文件都会**自动禁用系统代理环境变量**，避免代理拦截。

---

### 选择指南

| 场景 | 推荐方案 |
|------|--------|
| 快速集成、最稳定 | **Tool方式** |
| 需要MCP接口 | MCP Stdio方式 |
| 复杂多步骤操作 | Tool方式（WebDriver保持连接） |
| 简单网站截图 | 两种都可以 |
| 需要访问复杂网站 | Tool方式（完整性更高） |

---

### 环境依赖

#### 已安装
- `selenium>=4.0`
- `webdriver-manager>=4.0`
- `fastmcp>=3.0` (for MCP)

#### 系统要求
- Google Chrome浏览器已安装
- Python >= 3.10

#### 验证安装
```bash
# 验证Selenium
python -c "from selenium import webdriver; print('✅ Selenium可用')"

# 验证ChromeDriver自动下载
python -c "from webdriver_manager.chrome import ChromeDriverManager; print(ChromeDriverManager().install())"
```

---

### 故障排查

#### 问题：找不到Chrome浏览器
**解决**：确保Chrome已安装到标准位置，或修改代码指定Chrome路径

#### 问题：WebDriver初始化失败
**解决**：
1. 检查是否有系统代理拦截（代码已自动禁用）
2. 确保有足够的磁盘空间（ChromeDriver需要下载）
3. 检查防火墙设置

#### 问题：截图为空白
**原因**：
- Headless模式下某些复杂网站渲染不完整
- 页面加载时间不足
- JavaScript执行时间不足

**解决**：增加`wait_time`参数

#### 问题：MCP工具未被发现
**解决**：确保Agent传递了`tool_registry=global_registry`

---

### 性能参考

#### 典型截图大小
- `https://example.com` - 12.5 KB（简单页面）
- `https://linux.do/latest` - 10+ KB（动态页面）

#### 典型执行时间
- 导航 + 截图 - 10-20秒（取决于页面复杂度）
- Tool方式 - 单个进程，最快
- MCP方式 - 多进程，略慢

---

### 最佳实践

#### ✅ 推荐
```python
# 1. 总是传递tool_registry
agent = SimpleAgent(name="helper", llm=llm, tool_registry=global_registry)

# 2. 为Agent提供清晰的工具指导
prompt = """
使用 selenium_screenshot 工具：
- url: https://example.com
- output_path: screenshot.png
- wait_time: 15
"""

# 3. 总是清理资源
tool.close()
```

#### ❌ 避免
```python
# 1. 忘记传递tool_registry
agent = SimpleAgent(name="helper", llm=llm)  # ❌

# 2. 不清理WebDriver
# tool.close()  # ❌ 缺少这一行

# 3. 在MCP模式下假设状态保持
# 因为每个调用是新进程
```

---

### 核心实现文件

- `src/yu_agent/tools/selenium_screenshot.py` - SeleniumScreenshotTool类
- `src/yu_agent/protocols/mcp/selenium_server.py` - Selenium MCP服务器

### 测试脚本

- `tests/test_MCP/test_6_selenium.py` - **推荐：Tool方式演示**
- `tests/test_MCP/test_6.py` - MCP Stdio方式演示

---

## 📖 其他文档参考

所有详细的项目文档存储在 `description/` 文件夹，包括：

- **CLAUDE.md** - Claude Code工作指导配置
- **MCP参数修复文档** - MCP系统的技术深度分析
- **Playwright分析** - 与Selenium的技术对比
- **Terminal工具文档** - Terminal工具使用指南

建议查看 `description/INDEX.md` 获取完整的文档导航。

---

## 总结

**Selenium集成已经完全可用**，推荐使用**Tool方式**（test_6_selenium.py）：
- ✅ 最稳定可靠
- ✅ 截图质量最好
- ✅ 支持复杂网站
- ✅ 代码最简洁
- ✅ 无需额外配置

**立即开始**：
```bash
python tests/test_MCP/test_6_selenium.py
```

