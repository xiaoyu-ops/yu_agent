# MCP工具问题诊断和修复方案

## 问题描述

当运行以下代码时：
```python
agent = SimpleAgent(name="助手", llm=AgentsLLM())
mcp_tool = MCPTool(name="calculator")
agent.add_tool(mcp_tool)
response = agent.run("计算 25 乘以 16")
```

返回错误：
> "很抱歉，在尝试调用 `calculator_multiply` 工具进行计算时出现了错误（未找到该工具）"

## 根本原因

### 问题链条

1. **MCPTool 工具发现失败**
   - 在 `protocol_tools.py` 的 `_discover_tools()` 方法中（第 244-282 行）
   - 异步操作过程中抛出异常
   - 导致 `self._available_tools = []`（空列表）

2. **工具展开失败**
   - 在 `protocol_tools.py` 的 `get_expanded_tools()` 方法中（第 314-337 行）
   - 检查条件：`if not self.auto_expand: return []`
   - 但 `_available_tools` 为空，所以返回空列表

3. **工具注册被跳过**
   - 在 `simple_agent.py` 的 `add_tool()` 方法中（第 340 行）
   - 条件判断 `if expanded_tools:` 为 False
   - 代码会注册 MCPTool 本身，而不是展开后的工具

4. **工具调用失败**
   - LLM 看到系统提示中有工具列表，但工具注册表中找不到那些工具
   - 导致工具调用失败

### 具体出错位置

文件：`src/yu_agent/tools/protocol_tools.py`
方法：`_discover_tools()`
行号：243-282

```python
def _discover_tools(self):
    """发现MCP服务器提供的所有工具"""
    try:
        from hello_agents.protocols.mcp.client import MCPClient  # ❌ 这里有导入错误
        import asyncio
        # ... 异步发现代码可能失败 ...
    except Exception as e:
        self._available_tools = []  # ❌ 失败后设为空，导致后续工具全部无法使用
```

## 已应用的修复

### 修复1：更新导入路径（已修复）
**文件**：`protocol_tools.py`
**改变**：`hello_agents` → `yu_agent`
```python
from yu_agent.protocols.mcp.client import MCPClient  # ✅ 正确
```

### 修复2：增加错误诊断信息（已修复）
**文件**：`protocol_tools.py`
**改变**：取消注释错误堆栈打印
```python
except Exception as e:
    import traceback
    print(f"⚠️  警告：MCP工具发现失败: {str(e)}")
    traceback.print_exc()  # ✅ 现在会打印详细错误
    self._available_tools = []
```

### 修复3：改进 add_tool 的诊断（已修复）
**文件**：`simple_agent.py`
**改变**：添加更详细的诊断信息
```python
def add_tool(self, tool) -> None:
    # ... 代码 ...
    if expanded_tools:
        for expanded_tool in expanded_tools:
            self.tool_registry.register_tool(expanded_tool)
        print(f"✅ MCP工具 '{tool.name}' 已展开为 {len(expanded_tools)} 个独立工具")
        print(f"   注册的工具名称: {', '.join([t.name for t in expanded_tools])}")  # ✅ 现在显示
        return
    else:
        print(f"⚠️  警告：MCP工具 '{tool.name}' 展开失败，无可用工具")  # ✅ 诊断信息
```

### 修复4：添加 unregister_tool 别名（已修复）
**文件**：`registry.py`
**改变**：添加兼容性方法
```python
def unregister_tool(self, name: str) -> bool:
    """注销工具（别名方法，用于兼容性）"""
    if name in self._tools:
        del self._tools[name]
        return True
    elif name in self._functions:
        del self._functions[name]
        return True
    return False
```

## 诊断步骤

### 方法1：运行诊断脚本
```bash
# 进入测试目录
cd tests/test_MCP

# 运行简化的测试
python test_simple.py

# 或运行完整诊断
python diagnose_mcp.py
```

### 方法2：查看错误输出
修复后的代码现在会显示：
- 工具发现失败时的具体错误信息
- 工具展开失败时的警告
- 注册的工具列表

### 方法3：检查关键步骤
```python
from yu_agent.tools import MCPTool

mcp_tool = MCPTool(name="calculator")

# 检查1：工具是否被发现
print(f"发现的工具数: {len(mcp_tool._available_tools)}")

# 检查2：工具是否能展开
expanded = mcp_tool.get_expanded_tools()
print(f"展开的工具数: {len(expanded)}")

# 检查3：工具名称
print(f"工具名称: {[t.name for t in expanded]}")
```

## 预期的修复结果

修复后，运行测试应该看到：

```
开始MCP
✅ MCP工具 'calculator' 已展开为 6 个独立工具
   注册的工具名称: calculator_add, calculator_subtract, calculator_multiply, calculator_divide, calculator_greet, calculator_get_system_info
结束MCP

计算结果...
🔧 工具 calculator_multiply 执行结果：
400.0
```

而不是：

```
⚠️  工具 'calculator_multiply' 未找到
```

## 仍需排查的问题

如果修复后仍然出现工具未找到的错误，请检查：

1. **异步操作问题**
   - MCPClient 的 list_tools() 是否成功
   - 是否有其他异步异常被吞掉

2. **内置服务器问题**
   - 内置 FastMCP 服务器是否正确初始化
   - @server.tool() 装饰器是否有效

3. **线程池问题**
   - 并发执行器是否有问题
   - 事件循环是否正确管理

## 文件清单

已修改的文件：
- ✅ `src/yu_agent/tools/protocol_tools.py` - 修复导入路径和错误处理
- ✅ `src/yu_agent/agents/simple_agent.py` - 改进诊断信息
- ✅ `src/yu_agent/tools/registry.py` - 添加兼容性方法

新建的诊断文件：
- 📄 `tests/test_MCP/diagnose_mcp.py` - 完整诊断脚本
- 📄 `tests/test_MCP/test_simple.py` - 简化测试脚本
