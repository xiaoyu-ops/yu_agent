# yu_agent 完整文档汇总 - 第一部分

**编译时间**: 2026-02-13
**版本**: v0.2.0
**总内容**: 从 11 个 markdown 文件合并

---

## 目录

1. [快速开始](#快速开始)
2. [项目概述](#项目概述)
3. [内存系统](#内存系统)
4. [RAG 系统](#rag-系统)
5. [环境配置](#环境配置)
6. [故障排查](#故障排查)

---

# 快速开始

## 5 分钟启动

### 验证基础功能

```bash
cd D:\yu_agent
python test_the_yu_agent/test_rag.py
```

**预期结果**:
- ✅ Test 4: Agent 与 RAG 集成 - 通过
- ✅ Test 5: 高级 RAG 功能 - 通过
- ⚠️ Test 1-3: 因 Neo4j 不可用被跳过（正常）

### 启用完整功能

**Windows**:
```powershell
powershell setup_dev_env.ps1
# 选择 1 启动所有服务
```

**Linux/Mac**:
```bash
bash setup_dev_env.sh
# 选择 1 启动所有服务
```

---

# 项目概述

## yu_agent 是什么？

**yu_agent** 是一个学习阶段的 Agent 框架实现，基于《Hello Agents》教科书的设计模式，构建在 OpenAI 兼容 API 之上。

### 核心特性

- **简洁设计**: 优先考虑清晰度而不是过度抽象
- **多 LLM 支持**: OpenAI、DeepSeek、Qwen、ModelScope 等 8+ 个提供商
- **四种 Agent 模式**: Simple、ReAct、Reflection、PlanAndSolve
- **完整内存系统**: WorkingMemory、EpisodicMemory、SemanticMemory、PerceptualMemory
- **RAG 工具**: 文档管理、智能问答、知识检索
- **工具系统**: 计算器、搜索、RAG、自定义工具

### 版本信息

- **版本**: 0.1.1
- **Python**: >= 3.10
- **License**: MIT

---

# 内存系统

## 系统架构

### 四种记忆类型

#### 1. WorkingMemory（工作记忆）
- **用途**: 短期记忆，存储当前任务信息
- **存储**: 内存 + SQLite
- **检索**: TF-IDF 关键词搜索
- **容量**: 10 项，2000 tokens，120 分钟 TTL
- **特点**: 最快，无需外部依赖

#### 2. EpisodicMemory（事件记忆）
- **用途**: 记录事件和会话
- **存储**: SQLite + 可选 Qdrant
- **检索**: 时间范围、会话、行为模式
- **特点**: 追踪用户行为历史

#### 3. SemanticMemory（语义记忆）
- **用途**: 长期知识存储
- **存储**: Qdrant（向量） + Neo4j（图）
- **检索**: 向量相似度 + 知识图谱推理
- **特点**: 支持复杂推理和关系查询

#### 4. PerceptualMemory（感知记忆）
- **用途**: 多模态数据（文本、图像、音频、视频）
- **存储**: 文件系统 + Qdrant
- **检索**: 多模态向量搜索
- **特点**: 支持多种媒体类型

### 使用示例

```python
from yu_agent import MemoryManager, MemoryConfig, MemoryItem
from datetime import datetime

# 创建配置
config = MemoryConfig(storage_path="./memory_data")

# 创建内存管理器
manager = MemoryManager(
    config,
    user_id="user_123",
    enable_working=True,
    enable_episodic=True,
    enable_semantic=False,  # 需要 Neo4j
    enable_perceptual=False
)

# 添加记忆
manager.add_memory(
    content="用户对 Python 感兴趣",
    memory_type="working",
    importance=0.8,
    metadata={"topic": "programming"}
)

# 检索记忆
results = manager.retrieve_memories(
    query="Python 编程",
    limit=5,
    min_importance=0.5
)

# 获取统计
stats = manager.get_memory_stats()
print(f"总记忆数: {stats['total_memories']}")
```

### 数据库配置

#### Qdrant（向量数据库）

```env
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=yu_agents_vectors
QDRANT_VECTOR_SIZE=384
```

启动:
```bash
docker run -p 6333:6333 qdrant/qdrant:latest
```

#### Neo4j（图数据库）

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=yu-agents-password
```

启动:
```bash
docker run -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/yu-agents-password \
  neo4j:latest
```

#### 嵌入模型

```env
EMBED_MODEL_TYPE=local
EMBED_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
```

---

# RAG 系统

## RAG 工具概述

**RAG**（检索增强生成）是一种结合信息检索和文本生成的 AI 技术。

### 核心功能

- 📄 **多格式文档支持**: PDF、Word、Excel、PPT、图像、音频
- 🔍 **智能搜索**: 向量搜索 + 关键词混合搜索
- 🧠 **LLM 集成**: 自动检索相关内容并生成答案
- 📚 **知识管理**: 命名空间隔离、文档组织
- 💾 **持久化**: Qdrant 向量存储 + 文件系统

### 使用示例

```python
from yu_agent import RAGTool

# 初始化
rag = RAGTool()

# 添加文档
rag.add_document("path/to/document.pdf", namespace="project1")

# 智能问答
answer = rag.ask(
    "文档中的关键信息是什么?",
    namespace="project1"
)
print(answer)

# 搜索
results = rag.search("关键词", limit=5, namespace="project1")
for result in results:
    print(f"- {result['title']}: {result['score']}")

# 获取统计
stats = rag.stats(namespace="project1")
print(f"文档数: {stats['document_count']}")
```

### 与 Agent 集成

```python
from yu_agent import ReActAgent, RAGTool, global_registry

# 注册 RAG 工具
rag = RAGTool()
global_registry.register_tool(rag)

# 创建 Agent
agent = ReActAgent("知识助手", global_registry=global_registry)

# 使用 Agent 查询知识库
result = agent.run("请查询知识库中关于 Python 的内容")
```

### 与记忆系统结合

```python
from yu_agent import MemoryManager, RAGTool

# 创建内存和 RAG
memory = MemoryManager()
rag = RAGTool()

# RAG 获取知识
context = rag.search("用户问题", limit=3)

# 存储到记忆
for doc in context:
    memory.add_memory(
        content=doc["content"],
        memory_type="semantic",
        importance=doc["score"],
        metadata={"source": "rag"}
    )

# 后续检索使用记忆
results = memory.retrieve_memories("用户问题")
```

---

# 环境配置

## .env 配置

### LLM 配置

```env
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_ID=gpt-4o-mini
LLM_TIMEOUT=60
```

### 数据库配置

```env
# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=yu_agents_vectors

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=yu-agents-password

# 嵌入模型
EMBED_MODEL_TYPE=local
EMBED_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
```

### 搜索工具配置

```env
TAVILY_API_KEY=tvly-xxx
SERPAPI_API_KEY=xxx
```

## 安装依赖

### 基础安装

```bash
pip install -e .
```

### 完整安装（包含所有可选依赖）

```bash
pip install -e ".[memory]"
```

### 分别安装

```bash
# 内存系统
pip install qdrant-client neo4j sentence-transformers scikit-learn spacy

# 搜索工具
pip install tavily-python serpapi

# 其他
pip install python-dotenv
```

### 下载 spaCy 模型

```bash
python -m spacy download zh_core_web_sm  # 中文
python -m spacy download en_core_web_sm  # 英文
```

---

# 故障排查

## 常见问题

### 问题 1: 嵌入模型不可用

**错误**:
```
RuntimeError: 所有嵌入模型都不可用，请安装依赖或检查配置
```

**原因**:
- sentence-transformers 未安装
- .env 不在项目根目录

**解决**:
```bash
# 复制 .env 到根目录
cp test_the_yu_agent/.env .env

# 安装依赖
pip install sentence-transformers
```

### 问题 2: Neo4j 认证失败

**错误**:
```
Neo4j认证失败: The client is unauthorized due to authentication failure
```

**原因**:
- Neo4j 未运行
- 用户名/密码错误

**解决**:
```bash
# 启动 Neo4j
docker run -d -p 7687:7687 --name neo4j-yu-agent \
  -e NEO4J_AUTH=neo4j/yu-agents-password neo4j:latest

# 验证凭证
python -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://localhost:7687',
                              auth=('neo4j', 'yu-agents-password'))
with driver.session() as session:
    print('✅ 连接成功')
driver.close()
"
```

### 问题 3: MemoryItem 排序错误

**错误**:
```
'<' not supported between instances of 'MemoryItem' and 'MemoryItem'
```

**原因**: 使用了旧版本代码

**解决**:
```bash
# 更新代码
git pull
# 或重新安装
pip install -e . --force-reinstall
```

### 问题 4: 连接超时

**错误**:
```
Connection refused或Unable to connect
```

**原因**:
- 数据库未启动或启动不完整
- 防火墙阻止

**解决**:
```bash
# 检查容器状态
docker ps | grep -E "(neo4j|qdrant)"

# 查看日志
docker logs neo4j-yu-agent
docker logs qdrant-yu-agent

# 重启容器
docker restart neo4j-yu-agent
docker restart qdrant-yu-agent

# 等待启动
sleep 30

# 测试连接
curl http://localhost:6333/health
```

---

## 内存问题修复历史

### Bug #1: MemoryItem 排序失败

**症状**: Test 4 在添加背景知识时失败

**根本原因**: MemoryItem 类缺少比较方法

**修复**:
- 文件: `yu_agent/memory/base.py`
- 添加: `__lt__`, `__le__`, `__gt__`, `__ge__`, `__eq__` 方法
- 基于 timestamp 进行排序

### Bug #2: 嵌入模型配置不可用

**症状**: RuntimeError: 所有嵌入模型都不可用

**根本原因**: .env 文件位置不正确

**修复**:
- 将 .env 从 `test_the_yu_agent/` 复制到项目根目录
- 验证 sentence-transformers 已安装

### Bug #3: 日志输出过多

**症状**: 测试输出达到 30KB，充满进度条和日志

**修复**:
- 禁用 sentence-transformers 日志
- 禁用 httpx 日志
- 禁用 tqdm 进度条

---

## 测试结果总结

| 测试 | 状态 | 说明 |
|------|------|------|
| Test 1: 知识库创建 | ⚠️ | Neo4j 不可用 |
| Test 2: 语义搜索 | ⚠️ | 依赖 Test 1 |
| Test 3: 实体搜索 | ⚠️ | 依赖 Test 1 |
| Test 4: Agent 集成 | ✅ | 完全通过 |
| Test 5: 高级功能 | ✅ | 完全通过 |

**结论**: 核心功能（WorkingMemory + Agent）正常，可选功能（SemanticMemory）需要数据库。

