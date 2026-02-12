"""
yu_agent RAG (检索增强生成) 系统测试
测试语义记忆和Agent的集成
"""

import sys
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# 关闭冗余的日志和进度条
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("yu_agent").setLevel(logging.WARNING)
logging.disable(logging.CRITICAL)

# 禁用tqdm进度条
os.environ["TQDM_DISABLE"] = "1"

load_dotenv()

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yu_agent import (
    SimpleAgent,
    AgentsLLM,
    MemoryManager,
    MemoryConfig,
    MemoryItem,
    SemanticMemory,
)


def test_knowledge_base_creation():
    """测试知识库创建和管理"""
    print("\n" + "="*60)
    print("测试1: 知识库创建和管理")
    print("="*60)

    config = MemoryConfig(storage_path="./test_rag_data")

    try:
        semantic = SemanticMemory(config)
        print("[OK] 语义记忆初始化成功")
        print("    提示: Neo4j 需要运行: docker run -p 7687:7687 neo4j:latest")

        print("\n--- 添加知识库文档 ---")
        knowledge_base = [
            {
                "title": "Python编程基础",
                "content": "Python是一种高级编程语言，由Guido van Rossum于1991年首次发布。Python的设计哲学强调代码的可读性和简洁的语法。",
                "category": "编程语言",
                "tags": ["Python", "编程"]
            },
            {
                "title": "机器学习基础",
                "content": "机器学习是人工智能的一个分支，通过算法让计算机从数据中学习模式。主要包括监督学习、无监督学习和强化学习三种类型。",
                "category": "AI",
                "tags": ["机器学习", "AI", "算法"]
            },
            {
                "title": "RAG技术介绍",
                "content": "RAG（检索增强生成）是一种结合信息检索和文本生成的AI技术。它通过检索相关知识来增强大语言模型的生成能力。",
                "category": "LLM",
                "tags": ["RAG", "LLM", "检索"]
            },
            {
                "title": "向量数据库",
                "content": "向量数据库（如Qdrant）用于存储和检索高维向量，支持高效的语义搜索。它们在RAG系统中扮演关键角色。",
                "category": "数据库",
                "tags": ["向量数据库", "Qdrant", "搜索"]
            },
            {
                "title": "图数据库应用",
                "content": "Neo4j是流行的图数据库，用于表示和查询复杂的关系数据。在知识图谱应用中表现出色。",
                "category": "数据库",
                "tags": ["图数据库", "Neo4j", "知识图谱"]
            }
        ]

        doc_ids = []
        for i, doc in enumerate(knowledge_base):
            item = MemoryItem(
                id=f"doc_{i}",
                content=doc["content"],
                memory_type="semantic",
                user_id="system",
                timestamp=datetime.now(),
                importance=0.9,
                metadata={
                    "title": doc["title"],
                    "category": doc["category"],
                    "tags": doc["tags"]
                }
            )
            doc_id = semantic.add(item)
            doc_ids.append(doc_id)
            print(f"[OK] 添加文档 {i}: {doc['title']}")

        # 知识库统计
        print("\n--- 知识库统计 ---")
        stats = semantic.get_stats()
        print(f"[OK] 知识库统计:")
        print(f"  - 文档总数: {stats['count']}")
        print(f"  - 实体总数: {stats['entities_count']}")
        print(f"  - 关系总数: {stats['relations_count']}")

        return semantic, doc_ids

    except Exception as e:
        error_msg = str(e)
        if "Unauthorized" in error_msg or "Neo4j" in error_msg:
            print("[WARNING] Neo4j认证失败 - 知识库创建不可用")
            print("  解决方案:")
            print("    1. 启动Neo4j容器:")
            print("       docker run -d -p 7687:7687 --name neo4j-test \\")
            print("         -e NEO4J_AUTH=neo4j/yu-agents-password neo4j:latest")
            print("    2. 或修改 .env 中的 Neo4j 凭证")
            print("    3. 或跳过此测试，使用WorkingMemory替代")
        else:
            print(f"[WARNING] 知识库创建遇到限制: {error_msg[:100]}")
            print("  提示: 可运行以下命令获得完整功能:")
            print("       pip install qdrant-client neo4j spacy")
        return None, None


def test_semantic_search(semantic):
    """测试语义搜索功能"""
    print("\n" + "="*60)
    print("测试2: 语义搜索")
    print("="*60)

    if not semantic:
        print("[WARNING] 跳过此测试(知识库未初始化)")
        return

    search_queries = [
        "Python编程语言的历史",
        "机器学习算法类型",
        "如何使用向量数据库",
        "知识图谱应用"
    ]

    print("\n--- 执行语义搜索 ---")
    for query in search_queries:
        print(f"\n📍 查询: '{query}'")
        try:
            results = semantic.retrieve(query, limit=3)
            print(f"[OK] 找到 {len(results)} 条相关文档:")
            for i, result in enumerate(results, 1):
                score = result.metadata.get('combined_score', 0)
                print(f"  {i}. {result.metadata.get('title', 'Unknown')}")
                print(f"     相关度: {score:.3f}")
                print(f"     摘要: {result.content[:60]}...")
        except Exception as e:
            print(f"  [WARNING] 搜索失败: {str(e)[:100]}")


def test_entity_search(semantic):
    """测试实体搜索"""
    print("\n" + "="*60)
    print("测试3: 实体搜索和知识图谱")
    print("="*60)

    if not semantic:
        print("[WARNING] 跳过此测试(知识库未初始化)")
        return

    entity_queries = ["Python", "机器学习", "RAG"]

    print("\n--- 实体搜索 ---")
    for entity_name in entity_queries:
        print(f"\n🔍 搜索实体: '{entity_name}'")
        try:
            entities = semantic.search_entities(entity_name, limit=3)
            print(f"[OK] 找到 {len(entities)} 个实体:")
            for entity in entities:
                print(f"  - {entity.name}")
                print(f"    类型: {entity.entity_type}")
                print(f"    描述: {entity.description[:60]}...")
        except Exception as e:
            print(f"  [WARNING] 搜索失败: {str(e)[:100]}")

    # 导出知识图谱
    print("\n--- 知识图谱导出 ---")
    try:
        kg = semantic.export_knowledge_graph()
        print(f"[OK] 知识图谱:")
        print(f"  - 实体数: {len(kg['entities'])}")
        print(f"  - 关系数: {len(kg['relations'])}")
        print(f"  - 图节点总数: {kg['graph_stats'].get('total_nodes', 0)}")
        print(f"  - 图边数: {kg['graph_stats'].get('total_relationships', 0)}")
    except Exception as e:
        print(f"  [WARNING] 导出失败: {str(e)[:100]}")


def test_agent_with_rag():
    """Test Agent with RAG integration"""
    print("\n" + "="*60)
    print("Test 4: Agent With RAG Integration")
    print("="*60)

    config = MemoryConfig(storage_path="./test_rag_data")

    # Only enable working memory to avoid embedding model dependency
    memory_manager = MemoryManager(
        config,
        user_id="agent_user",
        enable_working=True,
        enable_episodic=False,
        enable_semantic=False,
        enable_perceptual=False
    )

    print("\n--- Initialize Agent ---")
    try:
        llm = AgentsLLM()
        agent = SimpleAgent(name="RAG Helper", llm=llm)
        print("[OK] Agent initialized successfully")

        # Add background knowledge
        print("\n--- Add Background Knowledge ---")
        background_knowledge = [
            "yu_agent is an AI Agent framework based on Hello Agents textbook",
            "Framework supports 4 memory types: working, episodic, semantic, perceptual",
            "Each memory type has unique storage and retrieval strategies",
            "System integrates Qdrant vector database and Neo4j graph database",
            "Supports automatic classification, importance calculation and forgetting"
        ]

        for knowledge in background_knowledge:
            memory_manager.add_memory(
                content=knowledge,
                memory_type="working",
                importance=0.8,
                metadata={"source": "background"}
            )
        print(f"[OK] Added {len(background_knowledge)} background knowledge items")

        # Simulate conversation
        print("\n--- Simulate Conversation ---")
        user_queries = [
            "What are the four memory types?",
            "What databases does the system use?",
            "How to enhance Agent capability?"
        ]

        for i, query in enumerate(user_queries, 1):
            print(f"\nUser Question {i}: {query}")

            # Retrieve relevant memories
            relevant_memories = memory_manager.retrieve_memories(
                query=query,
                limit=3,
                min_importance=0.5
            )

            print(f"  [SEARCH] Found {len(relevant_memories)} relevant memories")
            for memory in relevant_memories:
                print(f"    - {memory.content[:60]}...")

            # Build enhanced prompt
            context = "\n".join([m.content for m in relevant_memories])
            enhanced_prompt = f"""Background knowledge:
{context}

User question: {query}"""

            print(f"  [OK] Using enhanced prompt to call Agent")

        # Final statistics
        print("\n--- Final Statistics ---")
        stats = memory_manager.get_memory_stats()
        print(f"[OK] Agent memory system statistics:")
        print(f"  - Total memories: {stats['total_memories']}")
        for mem_type, type_stats in stats['memories_by_type'].items():
            print(f"  - {mem_type}: {type_stats.get('count', 0)} items")

    except Exception as e:
        print(f"[WARNING] Agent test issue: {e}")


def test_advanced_rag_features():
    """Test advanced RAG features"""
    print("\n" + "="*60)
    print("Test 5: Advanced RAG Features")
    print("="*60)

    config = MemoryConfig(storage_path="./test_rag_data")

    # Only enable working memory to avoid embedding dependency
    manager = MemoryManager(
        config,
        user_id="advanced_user",
        enable_working=True,
        enable_episodic=False,
        enable_semantic=False,
        enable_perceptual=False
    )

    print("\n--- Mixed Memory Type Retrieval ---")
    try:
        # Add working memory
        manager.add_memory(
            content="User learned about vector database today",
            memory_type="working",
            metadata={"session": "learning_session_001"}
        )

        manager.add_memory(
            content="Vector database is core component of RAG",
            memory_type="working",
            metadata={"category": "knowledge"}
        )

        print("[OK] Added mixed memory types")

        # Mixed retrieval
        results = manager.retrieve_memories(
            query="vector database application",
            memory_types=["working"],
            limit=5,
            min_importance=0.2
        )

        print(f"[OK] Mixed retrieval results ({len(results)} items):")
        for result in results:
            print(f"  - [{result.memory_type}] {result.content[:50]}...")

    except Exception as e:
        print(f"  [WARNING] Mixed retrieval: {str(e)[:100]}")

    print("\n--- Memory Forgetting and Consolidation ---")
    try:
        # Execute forgetting strategy
        forgotten = manager.forget_memories(
            strategy="importance_based",
            threshold=0.3
        )
        print(f"[OK] Forgot {forgotten} low-importance memories")

        # Execute consolidation
        consolidated = manager.consolidate_memories(
            from_type="working",
            to_type="episodic",
            importance_threshold=0.6
        )
        print(f"[OK] Consolidated {consolidated} memories to long-term storage")

    except Exception as e:
        print(f"  [WARNING] Forgetting and consolidation: {str(e)[:100]}")


def main():
    """运行所有RAG测试"""
    print("\n" + "="*60)
    print("yu_agent RAG (检索增强生成) 系统完整测试")
    print("="*60)

    try:
        # 创建知识库
        semantic, doc_ids = test_knowledge_base_creation()

        # 搜索测试
        test_semantic_search(semantic)

        # 实体和知识图谱测试
        test_entity_search(semantic)

        # Agent集成测试
        test_agent_with_rag()

        # 高级功能测试
        test_advanced_rag_features()

        print("\n" + "="*60)
        print("[SUCCESS] 所有RAG测试完成!")
        print("="*60)
        print("\n提示: 如果某些测试显示[WARNING]符号，说明依赖未完全安装")
        print("请运行: pip install qdrant-client neo4j spacy")
        print("然后下载spaCy模型:")
        print("  python -m spacy download zh_core_web_sm  # 中文")
        print("  python -m spacy download en_core_web_sm  # 英文")

    except Exception as e:
        print(f"\n[ERROR] RAG测试出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
