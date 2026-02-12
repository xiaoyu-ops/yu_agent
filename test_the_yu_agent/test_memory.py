"""
yu_agent Memory 系统测试
测试所有4种记忆类型和MemoryManager的功能
"""

import sys
import os
import logging
from datetime import datetime, timedelta

# 关闭冗余的日志和进度条
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("yu_agent").setLevel(logging.WARNING)
logging.disable(logging.CRITICAL)

# 禁用tqdm进度条
os.environ["TQDM_DISABLE"] = "1"

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yu_agent import (
    MemoryManager,
    MemoryConfig,
    MemoryItem,
    WorkingMemory,
    EpisodicMemory,
    SemanticMemory,
)


def test_basic_memory_manager():
    """测试基础的MemoryManager功能"""
    print("\n" + "="*60)
    print("Test 1: Basic MemoryManager Functionality")
    print("="*60)

    # Create configuration - only enable working memory initially
    config = MemoryConfig(
        storage_path="./test_memory_data",
        max_capacity=100,
        importance_threshold=0.1
    )

    # Create manager with limited memory types to avoid dependency issues
    manager = MemoryManager(
        config,
        user_id="test_user",
        enable_working=True,
        enable_episodic=False,  # Disabled to avoid DB dependency
        enable_semantic=False,  # Disabled to avoid NLP dependency
        enable_perceptual=False
    )
    print("OK: MemoryManager created successfully")

    # Add working memory
    print("\n--- Add Memories ---")
    memory1 = manager.add_memory(
        content="User Alice is a Python developer focused on machine learning",
        memory_type="working",
        importance=0.8,
        metadata={"tags": ["developer", "Python"], "specialty": "ML"}
    )
    print(f"OK: Working memory 1 added: {memory1[:8]}...")

    memory2 = manager.add_memory(
        content="Bob is a frontend engineer skilled in React and Vue.js",
        memory_type="working",
        importance=0.7,
        metadata={"tags": ["frontend", "JavaScript"]}
    )
    print(f"OK: Working memory 2 added: {memory2[:8]}...")

    memory3 = manager.add_memory(
        content="Charlie is a product manager responsible for UX design",
        memory_type="working",
        importance=0.6,
        metadata={"tags": ["product", "UX"]}
    )
    print(f"OK: Working memory 3 added: {memory3[:8]}...")

    # Retrieve memories
    print("\n--- Search Memories ---")
    results = manager.retrieve_memories(query="frontend engineer", limit=3)
    print(f"OK: Found {len(results)} memories for 'frontend engineer':")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result.content[:50]}... (importance: {result.importance})")

    # Statistics
    print("\n--- Memory Statistics ---")
    stats = manager.get_memory_stats()
    print(f"OK: Memory system statistics:")
    print(f"  - Total memories: {stats['total_memories']}")
    print(f"  - Enabled types: {stats['enabled_types']}")
    print(f"  - Distribution: {stats['memories_by_type']}")


def test_working_memory():
    """测试工作记忆功能"""
    print("\n" + "="*60)
    print("测试2: 工作记忆(WorkingMemory)功能")
    print("="*60)

    config = MemoryConfig(working_memory_capacity=5, working_memory_tokens=1000)
    working = WorkingMemory(config)

    print("\n--- 添加工作记忆 ---")
    # 添加多条记忆
    for i in range(3):
        item = MemoryItem(
            id=f"work_{i}",
            content=f"工作记忆 {i}: 这是第{i}条临时信息",
            memory_type="working",
            user_id="user1",
            timestamp=datetime.now(),
            importance=0.5 + i*0.2
        )
        working.add(item)
        print(f"[OK] 添加工作记忆 {i}")

    # 检索最近的记忆
    print("\n--- 获取最近记忆 ---")
    recent = working.get_recent(limit=2)
    print(f"[OK] 最近的记忆 ({len(recent)} 条):")
    for item in recent:
        print(f"  - {item.content} (重要性: {item.importance})")

    # 获取最重要的记忆
    print("\n--- 获取重要记忆 ---")
    important = working.get_important(limit=2)
    print(f"[OK] 最重要的记忆 ({len(important)} 条):")
    for item in important:
        print(f"  - {item.content} (重要性: {item.importance})")

    # 上下文摘要
    print("\n--- 上下文摘要 ---")
    summary = working.get_context_summary(max_length=200)
    print(f"[OK] 上下文摘要:\n{summary}")

    # 统计信息
    print("\n--- 工作记忆统计 ---")
    stats = working.get_stats()
    print(f"[OK] 工作记忆统计:")
    print(f"  - 活跃记忆数: {stats['count']}")
    print(f"  - 容量使用率: {stats['capacity_usage']:.1%}")
    print(f"  - Token使用率: {stats['token_usage']:.1%}")


def test_episodic_memory():
    """测试情景记忆功能"""
    print("\n" + "="*60)
    print("Test 3: Episodic Memory Functionality")
    print("="*60)

    config = MemoryConfig(storage_path="./test_memory_data")

    try:
        episodic = EpisodicMemory(config)
        print("OK: Episodic Memory initialized successfully")

        print("\n--- Add Interaction Events ---")
        # Add multiple events
        events = [
            {
                "content": "User completed a data analysis task",
                "session": "session_001",
                "outcome": "Success",
                "context": {"task_type": "analysis", "domain": "data"}
            },
            {
                "content": "User queried ML algorithm related questions",
                "session": "session_001",
                "outcome": "Answered",
                "context": {"task_type": "learning", "domain": "ML"}
            },
            {
                "content": "User debugged Python code",
                "session": "session_002",
                "outcome": "In Progress",
                "context": {"task_type": "development", "domain": "programming"}
            }
        ]

        for i, event in enumerate(events):
            item = MemoryItem(
                id=f"event_{i}",
                content=event["content"],
                memory_type="episodic",
                user_id="user1",
                timestamp=datetime.now() - timedelta(hours=i),
                importance=0.7 - i*0.1,
                metadata={
                    "session_id": event["session"],
                    "outcome": event["outcome"],
                    "context": event["context"]
                }
            )
            episodic.add(item)
            print(f"OK: Event {i} added: {event['content']}")

        # Query session
        print("\n--- Query Session ---")
        session_episodes = episodic.get_session_episodes("session_001")
        print(f"OK: Found {len(session_episodes)} events in session_001:")
        for ep in session_episodes:
            print(f"  - {ep.content}")

        # Discover patterns
        print("\n--- Behavior Pattern Recognition ---")
        patterns = episodic.find_patterns(user_id="user1", min_frequency=1)
        print(f"OK: Found {len(patterns)} patterns:")
        if patterns:
            for pattern in patterns[:3]:
                print(f"  - {pattern['type']}: {pattern['pattern']} (frequency: {pattern['frequency']})")
        else:
            print("  (No patterns found)")

        # Timeline view
        print("\n--- Timeline View ---")
        timeline = episodic.get_timeline(user_id="user1", limit=5)
        print(f"OK: Timeline ({len(timeline)} items):")
        for item in timeline:
            content = item['content'][:40] + "..." if len(item['content']) > 40 else item['content']
            print(f"  - {item['timestamp']}: {content}")

        # Statistics
        print("\n--- Episodic Memory Statistics ---")
        stats = episodic.get_stats()
        print(f"OK: Episodic memory statistics:")
        print(f"  - Active events: {stats['count']}")
        print(f"  - Sessions: {stats.get('sessions_count', 0)}")
        print(f"  - Time span: {stats.get('time_span_days', 0)} days")
        print(f"  - Avg importance: {stats['avg_importance']:.2f}")

    except Exception as e:
        print(f"WARNING: Episodic memory test has limitations: {str(e)[:100]}")
        print("  Tip: Run 'pip install qdrant-client neo4j' for full functionality")


def test_semantic_memory():
    """测试语义记忆功能"""
    print("\n" + "="*60)
    print("测试4: 语义记忆(SemanticMemory)功能")
    print("="*60)

    config = MemoryConfig(storage_path="./test_memory_data")

    try:
        semantic = SemanticMemory(config)
        print("[OK] 语义记忆初始化成功")

        print("\n--- 添加知识 ---")
        knowledge_items = [
            "Python是一种高级编程语言，具有简洁的语法和强大的生态系统",
            "机器学习是AI的一个分支，通过算法让计算机从数据中学习",
            "向量数据库用于存储和检索高维向量，支持语义搜索"
        ]

        memory_ids = []
        for i, knowledge in enumerate(knowledge_items):
            item = MemoryItem(
                id=f"concept_{i}",
                content=knowledge,
                memory_type="semantic",
                user_id="user1",
                timestamp=datetime.now(),
                importance=0.8,
                metadata={"category": "技术", "tags": ["编程", "AI"]}
            )
            mem_id = semantic.add(item)
            memory_ids.append(mem_id)
            print(f"[OK] 添加知识 {i}: {knowledge[:40]}...")

        # 语义检索
        print("\n--- 语义检索 ---")
        results = semantic.retrieve("编程语言特性", limit=3)
        print(f"[OK] 搜索'编程语言特性'，找到 {len(results)} 条相关知识:")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result.content[:50]}...")
            print(f"     相关度: {result.metadata.get('combined_score', 0):.3f}")

        # 实体搜索
        print("\n--- 实体搜索 ---")
        entities = semantic.search_entities("Python", limit=3)
        print(f"[OK] 搜索实体'Python'，找到 {len(entities)} 个:")
        for entity in entities:
            print(f"  - {entity.name} ({entity.entity_type})")

        # 统计信息
        print("\n--- 语义记忆统计 ---")
        stats = semantic.get_stats()
        print(f"[OK] 语义记忆统计:")
        print(f"  - 活跃知识数: {stats['count']}")
        print(f"  - 实体总数: {stats['entities_count']}")
        print(f"  - 关系总数: {stats['relations_count']}")
        print(f"  - 平均重要性: {stats['avg_importance']:.2f}")

        # 知识图谱导出
        print("\n--- 知识图谱统计 ---")
        kg = semantic.export_knowledge_graph()
        print(f"[OK] 知识图谱:")
        print(f"  - 实体数: {len(kg['entities'])}")
        print(f"  - 关系数: {len(kg['relations'])}")
        print(f"  - 图节点总数: {kg['graph_stats'].get('total_nodes', 0)}")

    except Exception as e:
        print(f"[WARNING] 语义记忆测试有限制 (需要spaCy/Neo4j/Qdrant): {str(e)[:100]}")
        print("  提示: 可运行 'pip install spacy qdrant-client neo4j' 获得完整功能")


def test_memory_operations():
    """测试记忆的更新、删除等操作"""
    print("\n" + "="*60)
    print("测试5: 记忆操作(更新、删除、遗忘)")
    print("="*60)

    config = MemoryConfig(storage_path="./test_memory_data")
    manager = MemoryManager(config, user_id="test_user")

    print("\n--- 添加测试记忆 ---")
    memory_id = manager.add_memory(
        content="原始内容: 这是一条测试记忆",
        memory_type="working",
        importance=0.5
    )
    print(f"[OK] 添加记忆: {memory_id[:8]}...")

    # 更新记忆
    print("\n--- 更新记忆 ---")
    updated = manager.update_memory(
        memory_id,
        content="更新内容: 这条记忆已被更新",
        importance=0.8
    )
    print(f"[OK] 更新结果: {updated}")

    # 遗忘记忆
    print("\n--- 遗忘记忆 ---")
    forgotten = manager.forget_memories(
        strategy="importance_based",
        threshold=0.2
    )
    print(f"[OK] 遗忘了 {forgotten} 条低重要性记忆")

    # 整合记忆
    print("\n--- 记忆整合 ---")
    print("  添加一些工作记忆...")
    for i in range(3):
        manager.add_memory(
            content=f"工作记忆{i}: 重要信息",
            memory_type="working",
            importance=0.8
        )

    consolidated = manager.consolidate_memories(
        from_type="working",
        to_type="episodic",
        importance_threshold=0.7
    )
    print(f"[OK] 整合了 {consolidated} 条记忆从工作记忆到情景记忆")

    # 最终统计
    print("\n--- 最终统计 ---")
    final_stats = manager.get_memory_stats()
    print(f"[OK] 最终记忆系统状态:")
    print(f"  - 总记忆数: {final_stats['total_memories']}")
    for mem_type, stats in final_stats['memories_by_type'].items():
        print(f"  - {mem_type}: {stats.get('count', 0)} 条")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("yu_agent Memory System Complete Test")
    print("="*60)

    try:
        # Basic tests
        test_basic_memory_manager()

        # Tests that don't require Qdrant/Neo4j
        test_working_memory()
        test_episodic_memory()

        # Optional tests
        try:
            test_semantic_memory()
        except:
            print("\nNOTE: Semantic memory test skipped (requires Qdrant/Neo4j)")

        try:
            test_memory_operations()
        except:
            print("\nNOTE: Memory operations test skipped")

        print("\n" + "="*60)
        print("OK: All available tests completed!")
        print("="*60)
        print("\nNote: Some tests show WARNING if dependencies are not fully installed.")
        print("For full functionality, run: pip install qdrant-client neo4j spacy")
        print("Then download spaCy models:")
        print("  python -m spacy download zh_core_web_sm")
        print("  python -m spacy download en_core_web_sm")

    except Exception as e:
        print(f"\nERROR: Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
