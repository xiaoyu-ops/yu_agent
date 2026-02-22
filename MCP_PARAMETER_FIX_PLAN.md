# MCP 工具参数传递修复方案

## 问题诊断

### 错误现象
```
🎬 行动: playwright_browser_navigate[url=https://example.com]
👀 观察: Invalid input: expected string, received undefined
   path: ["url"]
   expected: "string"
```

### 问题根源

参数流传路径中的断裂点：

```
SimpleAgent._parse_tool_parameters()
├─ 输入: "url=https://example.com"
├─ 处理: 正确解析为 {"url": "https://example.com"} ✅
└─ 输出: {"url": "https://example.com"}
    ↓
MCPWrappedTool.run(params={"url": "https://example.com"})
├─ 第111-115行: 构建 mcp_params
│  {
│    "action": "call_tool",
│    "tool_name": "playwright_browser_navigate",
│    "arguments": params  ← ✅ 参数看起来正确
│  }
└─ 调用 self.mcp_tool.run(mcp_params)
    ↓
MCPTool.run(parameters=mcp_params)
├─ 第396-400行: 提取工具参数
│  tool_name = parameters.get("tool_name")  ✅ 获取到 "playwright_browser_navigate"
│  arguments = parameters.get("arguments", {})  ← ❓ 这里可能有问题
│  result = await client.call_tool(tool_name, arguments)
└─ MCP 客户端调用
    ↓
❌ MCP 服务器返回: url 为 undefined
```

### 真正的问题

在 `MCPTool.run()` 第400行：
```python
result = await client.call_tool(tool_name, arguments)
```

传递的 `arguments` 应该是：
```python
{"url": "https://example.com"}
```

但 MCP 服务器收到的是：
```python
undefined
```

**最可能的原因**：`arguments` 在某个环节变成了字符串或被错误序列化

---

## 修复策略

### 修复点1：MCPWrappedTool 参数传递

**文件**：`src/yu_agent/tools/mcp_wrapper_tool.py`
**行号**：100-118
**问题**：参数直接传递，没有验证

**修复**：
1. 验证 `params` 是 dict 类型
2. 确保 `arguments` 字段被正确设置
3. 添加调试日志

### 修复点2：MCPTool 参数处理

**文件**：`src/yu_agent/tools/protocol_tools.py`
**行号**：395-401
**问题**：可能收到的 arguments 格式不对

**修复**：
1. 验证 `arguments` 确实是 dict
2. 如果是字符串，尝试反序列化
3. 添加错误日志

---

## 实现步骤

### 步骤1：修复 MCPWrappedTool.run()
- 添加参数验证
- 添加日志输出

### 步骤2：修复 MCPTool.run() 中的 call_tool 处理
- 添加参数类型检查
- 添加序列化验证

### 步骤3：测试验证
- 运行 test_6.py
- 检查是否正确调用工具
- 验证参数是否被正确传递

---

## 修复的原则

1. **最小化改动**：只修改必要的代码
2. **向后兼容**：确保现有代码不被破坏
3. **清晰的日志**：便于调试
4. **严谨的验证**：确保参数格式正确
