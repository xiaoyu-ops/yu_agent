#!/usr/bin/env python
"""
排查Playwright MCP工具 - 启用详细日志和输出目录
"""

import os
import sys
import io
import logging
import subprocess
import tempfile

# 设置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 路径设置
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, "src"))
sys.path.insert(0, current_dir)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from yu_agent import SimpleAgent, AgentsLLM
from yu_agent.tools import MCPTool
from dotenv import load_dotenv

load_dotenv()

print("=" * 80)
print("排查1：启用Playwright MCP工具的输出目录")
print("=" * 80)

# 创建临时输出目录
output_dir = tempfile.mkdtemp(prefix="playwright_output_")
print(f"\n📁 输出目录: {output_dir}")

# 创建Agent
agent = SimpleAgent(name="Playwright助手", llm=AgentsLLM())

# 创建Playwright工具 - 启用输出目录和其他选项
print("\n1️⃣ 创建Playwright MCPTool（启用输出目录）...")
playwright_tool = MCPTool(
    name="playwright",
    server_command=[
        "npx", "-y", "@playwright/mcp",
        "--output-dir", output_dir,
        "--allow-unrestricted-file-access",
        "--headless"  # 显式启用headless模式
    ]
)

print("2️⃣ 添加工具到Agent...")
agent.add_tool(playwright_tool)

# 执行任务
task = "请访问https://linux.do/latest并截图保存在D:\\yu_agent\\tests\\test_MCP\\example.png"
print(f"\n3️⃣ 执行任务...")
print("-" * 80)

try:
    response = agent.run(task)
    print("\n" + "=" * 80)
    print("Agent回复：")
    print(response)
    print("=" * 80)
except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()

# 检查输出目录中的文件
print("\n4️⃣ 检查输出目录中的文件...")
print("-" * 80)

if os.path.exists(output_dir):
    files = os.listdir(output_dir)
    print(f"输出目录中的文件数: {len(files)}")
    for file in files:
        file_path = os.path.join(output_dir, file)
        if os.path.isfile(file_path):
            size = os.path.getsize(file_path)
            print(f"  - {file} ({size} bytes)")
        else:
            print(f"  - {file}/ (目录)")
else:
    print(f"❌ 输出目录不存在: {output_dir}")

# 检查目标截图文件
print("\n5️⃣ 检查目标截图文件...")
print("-" * 80)

output_file = "D:\\yu_agent\\tests\\test_MCP\\example.png"
if os.path.exists(output_file):
    print(f"✅ 截图文件已生成: {output_file}")
    print(f"   文件大小: {os.path.getsize(output_file)} bytes")
else:
    print(f"❌ 截图文件未生成: {output_file}")

print(f"\n📝 输出目录保存位置: {output_dir}")
print("可以查看该目录了解Playwright MCP工具的详细输出")
