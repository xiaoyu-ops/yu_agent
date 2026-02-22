#!/usr/bin/env python
"""
测试参数修复 - 验证参数从SimpleAgent流向MCPTool的整个链路
"""

import os
import sys
import io
import logging

# 设置日志以显示调试信息
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

# =========================================================================
# 1. 获取当前脚本所在的文件夹路径 (D:\yu_agent\tests\test_MCP)
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. 获取项目根目录 (即 test_MCP 的上两级: D:\yu_agent)
project_root = current_dir

# 3. 将项目根目录加入到 Python 搜索路径中
sys.path.insert(0, project_root)

# 4. 将 src 目录加入到 Python 搜索路径中，使得可以直接 import yu_agent
sys.path.insert(0, os.path.join(project_root, "src"))

# 设置标准输出编码为UTF-8（解决Windows编码问题）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from yu_agent import SimpleAgent, ReActAgent, AgentsLLM, global_registry
from yu_agent.tools import MCPTool
from dotenv import load_dotenv

load_dotenv()

print("=" * 80)
print("测试参数修复：MCPWrappedTool + MCPTool 参数传递链")
print("=" * 80)

# 创建 SimpleAgent
agent = SimpleAgent(name="参数测试助手", llm=AgentsLLM())

# 创建 Playwright MCPTool
print("\n1️⃣ 创建 Playwright MCPTool...")
playwright_tool = MCPTool(
    name="playwright",
    server_command=["npx", "-y", "@playwright/mcp"]
)

print(f"   ✅ MCPTool 已创建")

# 尝试发现工具
print("\n2️⃣ 发现 Playwright 工具...")
try:
    playwright_tool._discover_tools()
    tools = playwright_tool.get_expanded_tools()
    print(f"   ✅ 发现了 {len(tools)} 个工具:")
    for tool in tools[:5]:  # 只显示前5个
        print(f"      - {tool.name}")
    if len(tools) > 5:
        print(f"      ... 还有 {len(tools) - 5} 个工具")
except Exception as e:
    print(f"   ❌ 发现工具失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试参数解析
print("\n3️⃣ 测试参数解析...")

test_cases = [
    {"format": "字典格式", "input": "url=https://example.com", "expected": {"url": "https://example.com"}},
    {"format": "列表格式", "input": '["https://example.com"]', "expected": ["https://example.com"]},
]

from yu_agent.agents.simple_agent import SimpleAgent as SA

for i, test in enumerate(test_cases, 1):
    print(f"\n   测试 {i}: {test['format']}")
    print(f"   输入: {test['input']}")
    try:
        result = SA._parse_tool_parameters(test['input'])
        print(f"   输出: {result}")
        print(f"   类型: {type(result).__name__}")
    except Exception as e:
        print(f"   ❌ 解析失败: {e}")

# 测试直接调用 MCPWrappedTool.run()
print("\n4️⃣ 测试 MCPWrappedTool.run() 参数验证...")

# 获取第一个工具
if tools:
    first_tool = tools[0]
    print(f"\n   使用第一个工具: {first_tool.name}")
    print(f"   参数要求: {first_tool.get_parameters()}")

    # 测试有效的参数
    valid_params = {"url": "https://example.com"} if first_tool.name == "playwright_browser_navigate" else {}

    print(f"\n   测试有效参数: {valid_params}")
    result = first_tool.run(valid_params)
    print(f"   结果: {result[:100]}..." if len(result) > 100 else f"   结果: {result}")

print("\n" + "=" * 80)
print("✅ 参数修复测试完成")
print("=" * 80)
