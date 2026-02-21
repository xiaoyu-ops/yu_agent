import os
import sys

# =========================================================================
# 1. 获取当前脚本所在的文件夹路径 (D:\yu_agent\tests\test_context)
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. 获取项目根目录 (即 test_context 的上两级: D:\yu_agent)
project_root = os.path.dirname(os.path.dirname(current_dir))

# 3. 将项目根目录加入到 Python 搜索路径中
sys.path.insert(0, project_root)

# 4. 将 src 目录加入到 Python 搜索路径中，使得可以直接 import yu_agent
sys.path.insert(0, os.path.join(project_root, "src"))

from yu_agent.context import ContextBuilder, ContextConfig, ContextPacket
from yu_agent.tools.builtin import memory_tool, RAGTool
from yu_agent.core.message import Message
from datetime import datetime


# 1. 初始化工具
memory_tool = memory_tool.MemoryTool(user_id="user123")
rag_tool = RAGTool(knowledge_base_path="./knowledge_base")

# 2. 创建 ContextBuilder
config = ContextConfig(
    max_tokens=3000,
    reserve_ratio=0.2,
    min_relevance=0.2,
    enable_compression=True
)

builder = ContextBuilder(
    memory_tool=memory_tool,
    rag_tool=rag_tool,
    config=config
)

# 3. 准备对话历史
conversation_history = [
    Message(content="我正在开发一个数据分析工具", role="user", timestamp=datetime.now()),
    Message(content="很好!数据分析工具通常需要处理大量数据。您计划使用什么技术栈?", role="assistant", timestamp=datetime.now()),
    Message(content="我打算使用Python和Pandas,已经完成了CSV读取模块", role="user", timestamp=datetime.now()),
    Message(content="不错的选择!Pandas在数据处理方面非常强大。接下来您可能需要考虑数据清洗和转换。", role="assistant", timestamp=datetime.now()),
]

# 4. 添加一些记忆
# 注意: 由于记忆系统的语义搜索有待优化，我们主要演示RAG功能
# 为了测试，我们添加一些基础记忆用于上下文
memory_tool.run({
    "action": "add",
    "content": "用户正在开发数据分析工具,使用Python和Pandas,已完成CSV读取模块",
    "memory_type": "episodic",
    "importance": 0.8
})

# 5. 向RAG知识库添加相关文档（这是重点）
print("Adding RAG documents...")
rag_tool.run({
    "action": "add",
    "documents": [
        "Pandas内存优化最佳实践: 数据类型优化是降低内存占用的最直接方法。使用category数据类型可以将object列的内存占用降低80-90%。例如,对于只有有限个不同值的字符串列,使用pd.Categorical()转换可以显著节省内存。另外,使用int32替代int64可以节省50%的内存,使用float32替代float64可以节省50%的内存。",
        "分块读取大文件: 使用chunksize参数可以避免一次性加载整个文件到内存中,这对于处理超过RAM大小的文件非常有用。例如: pd.read_csv('large_file.csv', chunksize=10000)将文件分成10000行的块进行处理,可以逐块处理数据而无需将整个文件加载到内存中。",
        "内存监控和分析工具: 使用df.memory_usage()可以查看DataFrame每列的内存占用详情,使用df.memory_usage(deep=True)可以获得对象列的精确内存占用。使用df.info()可以快速获得数据类型和内存的概览。使用sys.getsizeof()可以获得对象的内存大小。",
        "选择性列加载: 使用usecols参数只加载需要的列,这可以显著减少内存占用。例如: pd.read_csv('file.csv', usecols=['col1', 'col2'])只会加载指定的两列,而不是整个文件。这在处理有几百个列的大文件时特别有用。",
        "数据类型指定: 在读取CSV时使用dtype参数明确指定每列的数据类型,可以避免Pandas的自动推断过程。例如: pd.read_csv('file.csv', dtype={'id': 'int32', 'category': 'category'})可以直接以最优的数据类型读取数据。",
    ],
    "metadata": {"source": "pandas_memory_optimization", "topic": "内存优化"}
})
print("RAG documents added successfully!")

# 5. 构建上下文
context = builder.build(
    user_query="如何优化Pandas的内存占用?",
    conversation_history=conversation_history,
    system_instructions="你是一位资深的Python数据工程顾问。你的回答需要:1) 提供具体可行的建议 2) 解释技术原理 3) 给出代码示例",
    additional_packets=[
        # 补充：直接添加Evidence包，用于展示完整的上下文结构
        # 这演示了如何使用additional_packets参数来注入自定义内容
        ContextPacket(
            content="[知识库] Pandas内存优化最佳实践：1)使用category替代object可节省80-90%内存 2)int32替代int64节省50% 3)float32替代float64节省50% 4)使用chunksize分块读取大文件 5)使用usecols只加载需要的列 6)使用dtype参数预指定数据类型",
            metadata={"type": "knowledge_base"}
        )
    ]
)


print("=" * 80)
print("构建的上下文:")
print("=" * 80)
# 避免 UnicodeEncodeError - 使用 safe 选项
try:
    print(context)
except UnicodeEncodeError:
    # 写入文件而不是打印
    with open('context_output.txt', 'w', encoding='utf-8') as f:
        f.write(context)
    print("[上下文已保存到文件（包含Unicode字符）]")
    print("Length:", len(context), "chars")
print("=" * 80)
