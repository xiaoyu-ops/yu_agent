"""
Qdrant向量数据库存储实现
使用专业的Qdrant向量数据库替代ChromaDB
(兼容性修复版：支持 Qdrant-Client 1.x/2.x 及新旧 API)
"""

import logging
import os
import uuid
import threading
from typing import Dict, List, Optional, Any, Union
import numpy as np
from datetime import datetime

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    from qdrant_client.http.models import (
        Distance, VectorParams, PointStruct, 
        Filter, FieldCondition, MatchValue, SearchRequest
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    QdrantClient = None
    models = None

logger = logging.getLogger(__name__)

class QdrantConnectionManager:
    """Qdrant连接管理器 - 防止重复连接和初始化"""
    _instances = {}  # key: (url, collection_name) -> QdrantVectorStore instance
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(
        cls, 
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        collection_name: str = "hello_agents_vectors",
        vector_size: int = 384,
        distance: str = "cosine",
        timeout: int = 30,
        **kwargs
    ) -> 'QdrantVectorStore':
        """获取或创建Qdrant实例（单例模式）"""
        # 创建唯一键
        key = (url or "local", collection_name)
        
        if key not in cls._instances:
            with cls._lock:
                # 双重检查锁定
                if key not in cls._instances:
                    logger.debug(f"🔄 创建新的Qdrant连接: {collection_name}")
                    cls._instances[key] = QdrantVectorStore(
                        url=url,
                        api_key=api_key,
                        collection_name=collection_name,
                        vector_size=vector_size,
                        distance=distance,
                        timeout=timeout,
                        **kwargs
                    )
                else:
                    logger.debug(f"♻️ 复用现有Qdrant连接: {collection_name}")
        else:
            logger.debug(f"♻️ 复用现有Qdrant连接: {collection_name}")
            
        return cls._instances[key]

class QdrantVectorStore:
    """Qdrant向量数据库存储实现"""
    
    def __init__(
        self, 
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        collection_name: str = "hello_agents_vectors",
        vector_size: int = 384,
        distance: str = "cosine",
        timeout: int = 30,
        **kwargs
    ):
        """
        初始化Qdrant向量存储 (支持云API)
        """
        if not QDRANT_AVAILABLE:
            raise ImportError(
                "qdrant-client未安装。请运行: pip install qdrant-client>=1.6.0"
            )
        
        self.url = url
        self.api_key = api_key
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.timeout = timeout
        # HNSW/Query params via env
        try:
            self.hnsw_m = int(os.getenv("QDRANT_HNSW_M", "32"))
        except Exception:
            self.hnsw_m = 32
        try:
            self.hnsw_ef_construct = int(os.getenv("QDRANT_HNSW_EF_CONSTRUCT", "256"))
        except Exception:
            self.hnsw_ef_construct = 256
        try:
            self.search_ef = int(os.getenv("QDRANT_SEARCH_EF", "128"))
        except Exception:
            self.search_ef = 128
        self.search_exact = os.getenv("QDRANT_SEARCH_EXACT", "0") == "1"
        
        # 距离度量映射
        distance_map = {
            "cosine": Distance.COSINE,
            "dot": Distance.DOT,
            "euclidean": Distance.EUCLID,
        }
        self.distance = distance_map.get(distance.lower(), Distance.COSINE)
        
        # 初始化客户端
        self.client = None
        self._initialize_client()
        
    def _initialize_client(self):
        """初始化Qdrant客户端和集合"""
        try:
            # 根据配置创建客户端连接
            if self.url and self.api_key:
                # 使用云服务API
                self.client = QdrantClient(
                    url=self.url,
                    api_key=self.api_key,
                    timeout=self.timeout
                )
                logger.info(f"✅ 成功连接到Qdrant云服务: {self.url}")
            elif self.url:
                # 使用自定义URL（无API密钥）
                self.client = QdrantClient(
                    url=self.url,
                    timeout=self.timeout
                )
                logger.info(f"✅ 成功连接到Qdrant服务: {self.url}")
            else:
                # 使用本地服务（默认）
                self.client = QdrantClient(
                    host="localhost",
                    port=6333,
                    timeout=self.timeout
                )
                logger.info("✅ 成功连接到本地Qdrant服务: localhost:6333")
            
            # 检查连接
            # collections = self.client.get_collections()
            
            # 创建或获取集合
            self._ensure_collection()
            
        except Exception as e:
            logger.error(f"❌ Qdrant连接失败: {e}")
            if not self.url:
                logger.info("💡 本地连接失败，可以考虑使用Qdrant云服务")
                logger.info("💡 或启动本地服务: docker run -p 6333:6333 qdrant/qdrant")
            else:
                logger.info("💡 请检查URL和API密钥是否正确")
            raise
    
    def _ensure_collection(self):
        """确保集合存在，不存在则创建"""
        try:
            # 检查集合是否存在
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                # 创建新集合
                hnsw_cfg = None
                try:
                    hnsw_cfg = models.HnswConfigDiff(m=self.hnsw_m, ef_construct=self.hnsw_ef_construct)
                except Exception:
                    hnsw_cfg = None
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=self.distance
                    ),
                    hnsw_config=hnsw_cfg
                )
                logger.info(f"✅ 创建Qdrant集合: {self.collection_name}")
            else:
                logger.info(f"✅ 使用现有Qdrant集合: {self.collection_name}")
                # 尝试更新 HNSW 配置
                try:
                    self.client.update_collection(
                        collection_name=self.collection_name,
                        hnsw_config=models.HnswConfigDiff(m=self.hnsw_m, ef_construct=self.hnsw_ef_construct)
                    )
                except Exception as ie:
                    logger.debug(f"跳过更新HNSW配置: {ie}")
            # 确保必要的payload索引
            self._ensure_payload_indexes()
                
        except Exception as e:
            logger.error(f"❌ 集合初始化失败: {e}")
            raise

    def _ensure_payload_indexes(self):
        """为常用过滤字段创建payload索引"""
        try:
            index_fields = [
                ("memory_type", models.PayloadSchemaType.KEYWORD),
                ("user_id", models.PayloadSchemaType.KEYWORD),
                ("memory_id", models.PayloadSchemaType.KEYWORD),
                ("timestamp", models.PayloadSchemaType.INTEGER),
                ("modality", models.PayloadSchemaType.KEYWORD),  # 感知记忆模态筛选
                ("source", models.PayloadSchemaType.KEYWORD),
                ("external", models.PayloadSchemaType.BOOL),
                ("namespace", models.PayloadSchemaType.KEYWORD),
                # RAG相关字段索引
                ("is_rag_data", models.PayloadSchemaType.BOOL),
                ("rag_namespace", models.PayloadSchemaType.KEYWORD),
                ("data_source", models.PayloadSchemaType.KEYWORD),
            ]
            for field_name, schema_type in index_fields:
                try:
                    self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field_name,
                        field_schema=schema_type,
                    )
                except Exception as ie:
                    # 索引已存在会报错，忽略
                    logger.debug(f"索引 {field_name} 已存在或创建失败: {ie}")
        except Exception as e:
            logger.debug(f"创建payload索引时出错: {e}")
    
    def add_vectors(
        self, 
        vectors: List[List[float]], 
        metadata: List[Dict[str, Any]], 
        ids: Optional[List[str]] = None
    ) -> bool:
        """添加向量到Qdrant"""
        try:
            if not vectors:
                logger.warning("⚠️ 向量列表为空")
                return False
                
            # 生成ID（如果未提供）
            if ids is None:
                ids = [f"vec_{i}_{int(datetime.now().timestamp() * 1000000)}" 
                       for i in range(len(vectors))]
            
            # 构建点数据
            logger.info(f"[Qdrant] add_vectors start: n_vectors={len(vectors)} n_meta={len(metadata)} collection={self.collection_name}")
            points = []
            for i, (vector, meta, point_id) in enumerate(zip(vectors, metadata, ids)):
                # 确保向量是正确的维度
                try:
                    vlen = len(vector)
                except Exception:
                    logger.error(f"[Qdrant] 非法向量类型: index={i} type={type(vector)} value={vector}")
                    continue
                if vlen != self.vector_size:
                    logger.warning(f"⚠️ 向量维度不匹配: 期望{self.vector_size}, 实际{len(vector)}")
                    continue
                    
                # 添加时间戳到元数据
                meta_with_timestamp = meta.copy()
                meta_with_timestamp["timestamp"] = int(datetime.now().timestamp())
                meta_with_timestamp["added_at"] = int(datetime.now().timestamp())
                if "external" in meta_with_timestamp and not isinstance(meta_with_timestamp.get("external"), bool):
                    # normalize to bool
                    val = meta_with_timestamp.get("external")
                    meta_with_timestamp["external"] = True if str(val).lower() in ("1", "true", "yes") else False
                # 确保点ID是Qdrant接受的类型（无符号整数或UUID字符串）
                safe_id: Any
                if isinstance(point_id, int):
                    safe_id = point_id
                elif isinstance(point_id, str):
                    try:
                        uuid.UUID(point_id)
                        safe_id = point_id
                    except Exception:
                        safe_id = str(uuid.uuid4())
                else:
                    safe_id = str(uuid.uuid4())

                point = PointStruct(
                    id=safe_id,
                    vector=vector,
                    payload=meta_with_timestamp
                )
                points.append(point)
            
            if not points:
                logger.warning("⚠️ 没有有效的向量点")
                return False
            
            # 批量插入
            logger.info(f"[Qdrant] upsert begin: points={len(points)}")
            operation_info = self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True
            )
            logger.info("[Qdrant] upsert done")
            
            logger.info(f"✅ 成功添加 {len(points)} 个向量到Qdrant")
            return True
            
        except Exception as e:
            logger.error(f"❌ 添加向量失败: {e}")
            return False
    
    def search_similar(
            self, 
            query_vector: List[float], 
            limit: int = 10, 
            score_threshold: Optional[float] = None,
            where: Optional[Dict[str, Any]] = None
        ) -> List[Dict[str, Any]]:
            """
            搜索相似向量 (终极增强版：带 HTTP 强制回退)
            """
            try:
                if len(query_vector) != self.vector_size:
                    logger.error(f"❌ 查询向量维度错误: 期望{self.vector_size}, 实际{len(query_vector)}")
                    return []
                
                # 构建过滤器
                query_filter = None
                if where:
                    conditions = []
                    for key, value in where.items():
                        if isinstance(value, (str, int, float, bool)):
                            conditions.append(
                                FieldCondition(
                                    key=key,
                                    match=MatchValue(value=value)
                                )
                            )
                    
                    if conditions:
                        query_filter = Filter(must=conditions)
                
                # 执行搜索
                search_params = None
                try:
                    search_params = models.SearchParams(hnsw_ef=self.search_ef, exact=self.search_exact)
                except Exception:
                    search_params = None
                
                search_result = None
                results = []
                
                # 1. 尝试使用新版 search API
                if hasattr(self.client, 'search'):
                    try:
                        search_result = self.client.search(
                            collection_name=self.collection_name,
                            query_vector=query_vector,
                            query_filter=query_filter,
                            limit=limit,
                            score_threshold=score_threshold,
                            with_payload=True,
                            with_vectors=False,
                            search_params=search_params
                        )
                    except Exception as e:
                        # 打印出来让我们看到原因
                        print(f"⚠️ [调试] 标准 search 失败: {e}")
                        search_result = None

                # 2. 如果 search 失败或不存在，尝试使用 search_points (旧版/兼容版)
                if search_result is None and hasattr(self.client, 'search_points'):
                    try:
                        search_result = self.client.search_points(
                            collection_name=self.collection_name,
                            query_vector=query_vector,
                            top=limit,
                            filter=query_filter,
                            score_threshold=score_threshold,
                            with_payload=True,
                            with_vectors=False,
                            params=search_params
                        )
                    except Exception as e:
                        print(f"⚠️ [调试] search_points 失败: {e}")
                        # 参数签名可能不同，尝试极简调用
                        try:
                            search_result = self.client.search_points(
                                self.collection_name,
                                query_vector,
                                top=limit
                            )
                        except Exception:
                            pass

                # 3. HTTP 强制回退 (这是之前省略的部分，现在加回来)
                if search_result is None:
                    try:
                        import requests
                        print("⚠️ [调试] 正在尝试 HTTP 强制回退模式...")

                        # 构造 URL
                        host = self.url if self.url else "http://localhost:6333"
                        # 去掉末尾的斜杠，防止双斜杠
                        if host.endswith('/'): host = host[:-1]
                        endpoint = f"{host}/collections/{self.collection_name}/points/search"

                        http_payload = {
                            "vector": query_vector,
                            "limit": limit,
                            "with_payload": True,
                            "with_vector": False
                        }
                        # 加上过滤器
                        if where:
                            must_list = []
                            for k, v in where.items():
                                must_list.append({"key": k, "match": {"value": v}})
                            if must_list:
                                http_payload["filter"] = {"must": must_list}
                        
                        # 发送请求
                        resp = requests.post(endpoint, json=http_payload, timeout=self.timeout)
                        resp.raise_for_status()
                        data = resp.json()
                        
                        # 解析 HTTP 结果 (通常在 result 字段里)
                        search_result = data.get("result", [])
                        print(f"✅ [调试] HTTP 回退模式成功! 找到 {len(search_result)} 条数据")

                    except Exception as e:
                        logger.error(f"❌ HTTP 回退模式也失败了: {e}")

                # 4. 解析结果 (通用解析器)
                if search_result:
                    for hit in search_result:
                        try:
                            # 兼容对象属性访问 (getattr) 和 字典键访问 (.get)
                            hid = getattr(hit, 'id', None) or (hit.get('id') if isinstance(hit, dict) else None)
                            hscore = getattr(hit, 'score', None) or (hit.get('score') if isinstance(hit, dict) else None)
                            hpayload = getattr(hit, 'payload', None) or (hit.get('payload') if isinstance(hit, dict) else None)
                            
                            if hpayload is None and isinstance(hit, dict):
                                hpayload = hit.get('payloads') or {}
                            
                            results.append({
                                "id": hid,
                                "score": hscore,
                                "metadata": hpayload or {}
                            })
                        except Exception:
                            continue
                
                logger.debug(f"🔍 Qdrant搜索返回 {len(results)} 个结果")
                return results
                
            except Exception as e:
                logger.error(f"❌ 向量搜索失败: {e}")
                import traceback
                traceback.print_exc()
                return []
    
    def delete_vectors(self, ids: List[str]) -> bool:
        """删除向量"""
        try:
            if not ids:
                return True
                
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=ids
                ),
                wait=True
            )
            
            logger.info(f"✅ 成功删除 {len(ids)} 个向量")
            return True
            
        except Exception as e:
            logger.error(f"❌ 删除向量失败: {e}")
            return False
    
    def clear_collection(self) -> bool:
        """清空集合"""
        try:
            # 删除并重新创建集合
            self.client.delete_collection(collection_name=self.collection_name)
            self._ensure_collection()
            
            logger.info(f"✅ 成功清空Qdrant集合: {self.collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 清空集合失败: {e}")
            return False
    
    def delete_memories(self, memory_ids: List[str]):
        """删除指定记忆"""
        try:
            if not memory_ids:
                return
            # 构建 should 过滤条件：memory_id 等于任一给定值
            conditions = [
                FieldCondition(key="memory_id", match=MatchValue(value=mid))
                for mid in memory_ids
            ]
            query_filter = Filter(should=conditions)
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(filter=query_filter),
                wait=True,
            )
            logger.info(f"✅ 成功按memory_id删除 {len(memory_ids)} 个Qdrant向量")
        except Exception as e:
            logger.error(f"❌ 删除记忆失败: {e}")
            raise
    
    def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息 (兼容性增强版)"""
        try:
            collection_info = self.client.get_collection(self.collection_name)

            # 兼容不同 qdrant-client 版本返回的结构（对象或 dict，或嵌套在 result 中）
            def _safe_get(obj, *attrs):
                cur = obj
                for a in attrs:
                    if cur is None:
                        return None
                    if isinstance(cur, dict):
                        cur = cur.get(a)
                    else:
                        cur = getattr(cur, a, None)
                return cur

            vectors_count = _safe_get(collection_info, 'vectors_count') or _safe_get(collection_info, 'result', 'vectors_count')
            # 兼容新版 points_count
            if vectors_count is None:
                vectors_count = _safe_get(collection_info, 'points_count') or _safe_get(collection_info, 'result', 'points_count')

            indexed_vectors_count = _safe_get(collection_info, 'indexed_vectors_count') or _safe_get(collection_info, 'result', 'indexed_vectors_count')
            points_count = _safe_get(collection_info, 'points_count') or _safe_get(collection_info, 'result', 'points_count')
            segments_count = _safe_get(collection_info, 'segments_count') or _safe_get(collection_info, 'result', 'segments_count')

            info = {
                "name": self.collection_name,
                "vectors_count": int(vectors_count) if vectors_count is not None else 0,
                "indexed_vectors_count": int(indexed_vectors_count) if indexed_vectors_count is not None else 0,
                "points_count": int(points_count) if points_count is not None else 0,
                "segments_count": int(segments_count) if segments_count is not None else 0,
                "config": {
                    "vector_size": self.vector_size,
                    "distance": getattr(self.distance, 'value', str(self.distance)),
                }
            }

            return info
            
        except Exception as e:
            logger.error(f"❌ 获取集合信息失败: {e}")
            return {}
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        info = self.get_collection_info()
        if not info:
            return {"store_type": "qdrant", "name": self.collection_name}
        info["store_type"] = "qdrant"
        return info
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            # 尝试获取集合列表
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"❌ Qdrant健康检查失败: {e}")
            return False
    
    def __del__(self):
        """析构函数，清理资源"""
        if hasattr(self, 'client') and self.client:
            try:
                self.client.close()
            except:
                pass