"""
脚本：phase3_text_QA_vectorize.py

使用 ChromaDB 构建本地向量库，将 QA 与语义分块文本用 AWS Bedrock Titan 嵌入后写入同一 persist 目录；
与 phase3_image_vectorize 共用目录时可形成 QA + 语义块 + 图像三路召回。

处理逻辑：
- 嵌入模型：AWS Bedrock amazon.titan-embed-text-v2（与 agent 侧查询嵌入一致），默认持久化目录为
  data_prepare/processed_data/chromadb_ver3（可通过 --persist-dir 覆盖）。
- 数据源与 collection：
  1. QA：从 data_prepare/qa_pair/*.json 读取 qa_pairs，每条构造「问题 + 答案」文本，metadata 含 question、answer、
     category、source、keywords；写入 collection「qa_knowledge_base」。
  2. 语义分块：从 data_prepare/semantic_chunk/*_for_chunking.json 读取 chunks，每条取 content 与 metadata
     （含 refs_in_chunk 等）；写入 collection「semantic_chunks」。
- 默认同时写入上述两个 collection；--qa-only 仅处理 QA，--semantic-only 仅处理 semantic_chunk。
- 同一 persist 目录下可与 phase3_image_vectorize 写入的「image_embeddings」共存，便于多路检索。
- --use-local：使用本地嵌入（若已配置），否则走 Bedrock。
"""

import json
import sys
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Tuple
import argparse
import time
import signal
import threading

# 数据根目录：原始输入在 data_prepare，phase 产物统一落到 processed_data
import sys as _sys
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CONFIGURING = _PROJECT_ROOT / "skills" / "configuring-pipeline"
for _p in (_CONFIGURING, _PROJECT_ROOT):
    if str(_p) not in _sys.path:
        _sys.path.insert(0, str(_p))

try:
    from pipeline_config_loader import load_config as _load_config
    _cfg = _load_config(ensure_dirs=True)
    DATA_PREPARE_DIR = Path(_cfg["input"]["raw_material"]).parent
    PROCESSED_DATA_DIR = DATA_PREPARE_DIR / "processed_data"
except Exception:
    _cfg = {}
    DATA_PREPARE_DIR = Path(__file__).resolve().parents[1]
    PROCESSED_DATA_DIR = DATA_PREPARE_DIR / "processed_data"

_aws = _cfg.get("aws") or {}
AWS_EMBEDDING_MODEL = _aws.get("embedding_model", "amazon.titan-embed-text-v2:0")
AWS_REGION = _aws.get("region", "us-west-2")
_vec = _cfg.get("vectorizing") or {}
_chromadb_vec = _vec.get("chromadb") or {}
CHROMADB_DEFAULT_REBUILD = bool(_chromadb_vec.get("rebuild", False))
CHROMADB_DEFAULT_PERSIST_DIR = _cfg.get("output", {}).get("chromadb") or str(PROCESSED_DATA_DIR / "chromadb_ver3")


def load_qa_data() -> Tuple[List[str], List[Dict[str, Any]], List[str]]:
    """从 data_prepare/qa_pair 加载所有 QA JSON，返回 (documents, metadatas, ids)。含完整 metadata。"""
    qa_dir = PROCESSED_DATA_DIR / "qa_pair"
    if not qa_dir.exists():
        print(f"✗ 目录不存在: {qa_dir}")
        return [], [], []
    qa_files = list(qa_dir.glob("*.json"))

    if not qa_files:
        print("✗ 没有找到 QA JSON 文件（data_prepare/qa_pair/*.json）")
        return [], [], []

    print(f"[QA] 找到 {len(qa_files)} 个文件")

    documents = []
    metadatas = []
    ids = []

    for qa_file in qa_files:
        with open(qa_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        qa_pairs = data.get('qa_pairs', [])
        if not qa_pairs:
            continue
        source = data.get('metadata', {}).get('source', qa_file.stem)
        asset_meta = data.get("asset_meta") or {}
        knowledge_layer = (asset_meta.get("knowledge_layer") or data.get("metadata", {}).get("knowledge_layer") or "")[:100]
        asset_id = (asset_meta.get("asset_id") or "")[:200]
        print(f"  加载: {qa_file.name} -> {len(qa_pairs)} 条")

        for qa in qa_pairs:
            doc_text = f"问题: {qa['question']}\n\n答案: {qa['answer']}"
            documents.append(doc_text)
            # 完整 metadata，便于检索与 rerank 使用
            metadatas.append({
                'question': (qa.get('question') or '')[:10000],
                'answer': (qa.get('answer') or '')[:10000],
                'category': qa.get('category', 'N/A'),
                'source': source,
                'keywords': ','.join(qa.get('keywords', [])) if isinstance(qa.get('keywords'), list) else str(qa.get('keywords', '')),
                'knowledge_layer': knowledge_layer,
                'asset_id': asset_id,
            })
            raw_id = f"{source}||{qa.get('question', '')}||{qa.get('answer', '')}"
            stable_id = hashlib.sha1(raw_id.encode("utf-8")).hexdigest()[:24]
            ids.append(f"qa_{stable_id}")

    print(f"✓ [QA] 共 {len(documents)} 条，均有 metadata\n")
    return documents, metadatas, ids


def load_semantic_chunk_data() -> Tuple[List[str], List[Dict[str, Any]], List[str]]:
    """从 data_prepare/semantic_chunk 加载 *_for_chunking.json，返回 (documents, metadatas, ids)。含完整 metadata。"""
    chunk_dir = PROCESSED_DATA_DIR / "semantic_chunk"
    if not chunk_dir.exists():
        print(f"✗ 目录不存在: {chunk_dir}")
        return [], [], []
    chunk_files = list(chunk_dir.glob("*_for_chunking.json"))

    if not chunk_files:
        print("✗ 没有找到 for_chunking JSON 文件")
        return [], [], []

    print(f"[Semantic] 找到 {len(chunk_files)} 个 for_chunking 文件")

    documents = []
    metadatas = []
    ids = []

    for chunk_file in chunk_files:
        print(f"  加载: {chunk_file.name}")

        with open(chunk_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            chunks = data.get('chunks', [])
            asset_meta = data.get("asset_meta") or {}
            dataset_asset_id = (asset_meta.get("asset_id") or "")[:200]
            dataset_layer = (asset_meta.get("knowledge_layer") or (data.get("document_metadata") or {}).get("knowledge_layer") or "")[:100]

            for ch in chunks:
                meta = ch.get('metadata', {})
                content = ch.get('content', '')
                chunk_id = meta.get('chunk_id', f"{chunk_file.stem}_{len(documents)}")

                # ChromaDB metadata 仅支持 str/int/float/bool，列表转成字符串
                refs = meta.get('refs_in_chunk', [])
                refs_str = ','.join(refs) if isinstance(refs, list) else str(refs)
                
                # 提取 chunk content 中的图像占位符，建立图像-上下文关联
                import re
                image_pattern = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')
                image_paths_in_chunk = image_pattern.findall(content)
                image_paths_str = ','.join(image_paths_in_chunk) if image_paths_in_chunk else ''

                documents.append(content)
                # 完整 metadata，便于检索与 rerank 使用（Chroma 仅支持 str/int/float/bool，长字符串截断）
                # source_type / segment_jsonl / case_id 供 Agent 表格/日志 Tool Calling（含 query_log_by_case）
                seg_jsonl = (meta.get('segment_jsonl') or '').strip().replace('\\', '/')[:500]
                metadatas.append({
                    'doc_name': meta.get('doc_name', chunk_file.stem.replace('_for_chunking', '')),
                    'chunk_id': chunk_id,
                    'section_title': (meta.get('section_title') or '')[:500],
                    'section_index': int(meta.get('section_index', 0)),
                    'char_count': int(meta.get('char_count', 0)),
                    'refs_in_chunk': refs_str[:2000],
                    'image_paths': image_paths_str[:2000],  # 该 chunk 包含的图像路径（逗号分隔）
                    'source_path': (meta.get('source_path') or '')[:500],
                    'markdown_path': (meta.get('markdown_path') or '')[:500],
                    'source_type': (meta.get('source_type') or '')[:100],
                    'segment_jsonl': seg_jsonl,
                    'case_id': (meta.get('case_id') or '')[:100],  # 日志案例 ID，供 query_log_by_case
                    'knowledge_layer': (meta.get('knowledge_layer') or dataset_layer)[:100],
                    'asset_id': dataset_asset_id,
                })
                ids.append(chunk_id)

            print(f"    {len(chunks)} 个 chunk")

    print(f"✓ [Semantic] 共 {len(documents)} 个 chunk，均有 metadata\n")
    return documents, metadatas, ids


def _get_or_create_client(persist_dir: str, client: Any = None):
    """获取或创建 Chroma 持久化客户端。"""
    try:
        import chromadb
        from chromadb.config import Settings
    except ImportError:
        print("✗ 请先安装 chromadb: pip install chromadb")
        sys.exit(1)
    if client is not None:
        return client
    return chromadb.PersistentClient(
        path=persist_dir,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )


def create_chromadb_collection(
    documents: List[str],
    metadatas: List[Dict[str, Any]],
    ids: List[str],
    collection_name: str = "knowledge_base",
    use_aws: bool = True,
    persist_dir: str = "./chromadb_ver3",
    client: Any = None,
    rebuild: bool = False,
):
    """向 ChromaDB 添加一个集合及数据。documents/metadatas/ids 长度需一致。可传入已有 client 以共用同一 DB。"""
    try:
        import chromadb
        from chromadb.config import Settings
    except ImportError:
        print("✗ 请先安装 chromadb: pip install chromadb")
        sys.exit(1)

    if not documents or len(documents) != len(metadatas) or len(documents) != len(ids):
        raise ValueError("documents、metadatas、ids 长度必须一致且非空")

    client = _get_or_create_client(persist_dir, client)

    print("=" * 80)
    print(f"集合: {collection_name}")
    print("=" * 80)
    print(f"持久化路径: {persist_dir}")

    if rebuild:
        try:
            client.delete_collection(collection_name)
            print(f"✓ 已删除旧集合 {collection_name}")
        except Exception:
            pass

    if use_aws:
        print("使用 AWS Bedrock Titan Embed Text v2 (amazon.titan-embed-text-v2，与 agent 查询一致)")
        try:
            import boto3
            from chromadb.utils.embedding_functions import EmbeddingFunction
            from botocore.exceptions import ClientError

            TITAN_MODEL_ID = AWS_EMBEDDING_MODEL
            TITAN_OUTPUT_DIM = 1024
            TITAN_MAX_CHARS = 8192  # 单条文本字符上限，超出截断

            class TitanEmbeddingFunction(EmbeddingFunction):
                def __init__(self, region_name: str = None):
                    self.region_name = region_name or AWS_REGION
                    self.model_id = TITAN_MODEL_ID
                    self.output_dimension = TITAN_OUTPUT_DIM
                    self.max_chars = TITAN_MAX_CHARS
                    self.stop_event = threading.Event()

                def _get_client(self):
                    if not hasattr(threading.current_thread(), 'bedrock_client'):
                        threading.current_thread().bedrock_client = boto3.client(
                            'bedrock-runtime', region_name=self.region_name
                        )
                    return threading.current_thread().bedrock_client

                def _interruptible_sleep(self, seconds: float):
                    if self.stop_event.is_set():
                        raise KeyboardInterrupt("用户中断")
                    self.stop_event.wait(timeout=seconds)
                    if self.stop_event.is_set():
                        raise KeyboardInterrupt("用户中断")

                def __call__(self, input: List[str]) -> List[List[float]]:
                    total = len(input)
                    print(f"  开始嵌入 {total} 个文本（Titan embed-text-v2）...")
                    print(f"  提示: 按 Ctrl+C 可中断")
                    start_time = time.time()

                    def signal_handler(signum, frame):
                        print("\n\n⚠ 收到中断信号，正在停止...")
                        self.stop_event.set()

                    if threading.current_thread() is threading.main_thread():
                        signal.signal(signal.SIGINT, signal_handler)

                    all_embeddings: List[List[float]] = []
                    max_retries = 3
                    retry_delay = 1.0

                    for i, raw_text in enumerate(input):
                        if self.stop_event.is_set():
                            break
                        text = (raw_text or " ").strip()[: self.max_chars] or " "

                        for attempt in range(max_retries):
                            try:
                                self._interruptible_sleep(0.05 if attempt == 0 else retry_delay * (2 ** (attempt - 1)))
                                if self.stop_event.is_set():
                                    raise KeyboardInterrupt("用户中断")
                                bedrock_client = self._get_client()
                                body = json.dumps({
                                    "inputText": text,
                                    "dimensions": self.output_dimension,
                                    "normalize": True,
                                })
                                response = bedrock_client.invoke_model(
                                    modelId=self.model_id,
                                    body=body,
                                    contentType="application/json",
                                    accept="application/json",
                                )
                                if self.stop_event.is_set():
                                    raise KeyboardInterrupt("用户中断")
                                response_body = json.loads(response["body"].read())
                                embedding = response_body.get("embedding", [])
                                if embedding and len(embedding) == self.output_dimension:
                                    all_embeddings.append(embedding)
                                    break
                                raise ValueError(f"Titan 返回异常向量长度: {len(embedding) if embedding else 0}")
                            except KeyboardInterrupt:
                                raise
                            except ClientError as e:
                                error_code = e.response.get("Error", {}).get("Code", "")
                                if error_code == "ThrottlingException" and attempt < max_retries - 1:
                                    wait = retry_delay * (2 ** attempt) * 2
                                    print(f"\n    ⚠ 限流: 第 {i+1} 条，等待 {wait:.1f}s 重试 ({attempt+1}/{max_retries})")
                                    self._interruptible_sleep(wait)
                                    continue
                                print(f"\n    ✗ Titan 嵌入失败: {e}")
                                all_embeddings.append([0.0] * self.output_dimension)
                                break
                            except Exception as e:
                                if attempt < max_retries - 1:
                                    self._interruptible_sleep(retry_delay * (2 ** attempt))
                                    continue
                                print(f"\n    ✗ Titan 嵌入异常: {e}")
                                all_embeddings.append([0.0] * self.output_dimension)
                                break
                        else:
                            all_embeddings.append([0.0] * self.output_dimension)

                        done = len(all_embeddings)
                        if done % 50 == 0 or done == total:
                            elapsed = time.time() - start_time
                            rate = done / elapsed if elapsed > 0 else 0
                            eta = (total - done) / rate if rate > 0 else 0
                            print(f"    进度: {done}/{total} ({done*100//total}%) | "
                                  f"速度: {rate:.1f} 个/秒 | 预计剩余: {eta:.0f} 秒", end="\r")

                    elapsed = time.time() - start_time
                    if len(all_embeddings) < total:
                        print(f"\n  ⚠ 部分完成: {len(all_embeddings)}/{total} 个向量")
                        for _ in range(total - len(all_embeddings)):
                            all_embeddings.append([0.0] * self.output_dimension)
                    else:
                        print(f"\n  ✓ 完成嵌入 {len(all_embeddings)} 个向量，耗时 {elapsed:.1f} 秒")
                    return all_embeddings

            embedding_function = TitanEmbeddingFunction(region_name=AWS_REGION)

            collection = client.get_or_create_collection(
                name=collection_name,
                embedding_function=embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
            print("✓ 使用 AWS Bedrock amazon.titan-embed-text-v2:0")
        except Exception as e:
            print(f"✗ AWS Bedrock embeddings 初始化失败: {e}")
            print("  回退到默认 sentence-transformers embeddings")
            collection = client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
    else:
        print("使用默认 sentence-transformers embeddings")
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    if rebuild:
        print(f"✓ 集合已重建: {collection_name}")
    else:
        print(f"✓ 集合已打开（增量模式）: {collection_name}")

    batch_size = 1000
    total_batches = (len(documents) + batch_size - 1) // batch_size

    print(f"\n准备写入 {len(documents)} 个文档到集合...")

    for i in range(0, len(documents), batch_size):
        batch_num = i // batch_size + 1
        end_idx = min(i + batch_size, len(documents))
        print(f"  批次 {batch_num}/{total_batches}: upsert {end_idx - i} 个文档")
        collection.upsert(
            documents=documents[i:end_idx],
            metadatas=metadatas[i:end_idx],
            ids=ids[i:end_idx]
        )

    print(f"✓ 文档写入完成（upsert，新增或更新）")
    print(f"✓ 数据已持久化到: {persist_dir}")

    return client, collection


def main():
    """主函数：同一 VectorDB 下同时写入 qa_knowledge_base 与 semantic_chunks 两个 collection。"""
    parser = argparse.ArgumentParser(
        description='创建 ChromaDB 本地向量数据库（QA + semantic_chunk 双 collection）',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--use-aws',
        action='store_true',
        default=True,
        help='使用 AWS Bedrock embeddings（默认启用）'
    )

    parser.add_argument(
        '--use-local',
        action='store_true',
        help='使用本地 sentence-transformers embeddings'
    )

    parser.add_argument(
        '--persist-dir',
        type=str,
        default=CHROMADB_DEFAULT_PERSIST_DIR,
        help='ChromaDB 持久化目录（默认从 pipeline_config.json output.chromadb 读取）'
    )
    parser.add_argument(
        '--rebuild',
        action='store_true',
        default=CHROMADB_DEFAULT_REBUILD,
        help='重建 collection（会删除旧数据）；默认从 pipeline_config.json vectorizing.chromadb.rebuild 读取，通常为增量(False)'
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--qa-only',
        action='store_true',
        help='仅向量化 QA 数据（qa_pair/*.json），不加载 semantic_chunk'
    )
    group.add_argument(
        '--semantic-only',
        action='store_true',
        help='仅向量化 Semantic 数据（semantic_chunk/*_for_chunking.json），不加载 qa_pair'
    )

    args = parser.parse_args()
    use_aws = not args.use_local
    persist_dir = args.persist_dir
    qa_only = args.qa_only
    semantic_only = args.semantic_only
    rebuild = args.rebuild

    if qa_only:
        print("模式: 仅 QA\n")
    elif semantic_only:
        print("模式: 仅 Semantic\n")
    print(f"写入策略: {'重建(rebuild)' if rebuild else '增量(upsert)'}")
    print("加载数据源（QA: data_prepare/qa_pair，Semantic: data_prepare/semantic_chunk）\n")
    qa_docs, qa_meta, qa_ids = load_qa_data() if not semantic_only else ([], [], [])
    sem_docs, sem_meta, sem_ids = load_semantic_chunk_data() if not qa_only else ([], [], [])

    if not qa_docs and not sem_docs:
        print("✗ 没有可加载数据（qa_pair 与 semantic_chunk 均无有效文件）")
        sys.exit(1)

    client = None
    coll_qa, coll_sem = None, None

    if qa_docs:
        client, coll_qa = create_chromadb_collection(
            qa_docs, qa_meta, qa_ids,
            collection_name="qa_knowledge_base",
            use_aws=use_aws,
            persist_dir=persist_dir,
            client=client,
            rebuild=rebuild,
        )
    if sem_docs:
        client, coll_sem = create_chromadb_collection(
            sem_docs, sem_meta, sem_ids,
            collection_name="semantic_chunks",
            use_aws=use_aws,
            persist_dir=persist_dir,
            client=client,
            rebuild=rebuild,
        )

    print("\n" + "=" * 80)
    print("✓ ChromaDB 文本侧创建完成（qa + semantic_chunks，与 image_embeddings 同 DB 则三 collection）")
    print("=" * 80)
    print(f"持久化路径: {persist_dir}")
    qa_count = coll_qa.count() if coll_qa is not None else 0
    sem_count = coll_sem.count() if coll_sem is not None else 0
    if coll_qa is not None:
        print(f"  qa_knowledge_base: {qa_count} 条")
    if coll_sem is not None:
        print(f"  semantic_chunks:   {sem_count} 条")
    print("\n图像嵌入请运行: python data_prepare/phase3_image_vectorize.py")
    print("检索建议：三路召回（QA + semantic + image）→ 合并 → rerank")

    try:
        from pipeline_run_logger import append_run_record
        append_run_record(
            step_id="phase3_text_qa",
            script="phase3_text_QA_vectorize.py",
            status="success",
            files_processed=qa_count + sem_count,
            detail={"persist_dir": str(persist_dir), "qa_count": qa_count, "semantic_count": sem_count},
        )
    except Exception as e:
        print(f"[run_log] 写入运行记录失败: {e}")


if __name__ == "__main__":
    main()
