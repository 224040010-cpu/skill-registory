"""
脚本：phase3_image_vectorize.py

对 data_prepare/images/ 下的文档配图做「理解 + 嵌入」，写入 ChromaDB，与 phase3_text_QA_vectorize 共用
persist 目录时可实现文本与图像多路召回。

处理逻辑：
- 输入：data_prepare/images/<doc_name>/ 下所有 .png/.jpg/.jpeg/.webp/.gif 图片；doc_name 与 semantic_chunk
  及 markdown 文档名对应。
- 第一步（理解）：调用 AWS Bedrock Claude 3.5 Sonnet，将图片以 base64 传入，生成图像描述/OCR 等文本，
  带重试与退避，结果作为该图像的「描述文本」。
- 第二步（嵌入）：使用 Bedrock Titan embed-text-v2（与 phase3_text_QA_vectorize 一致，维度 1024）对描述文本
  做向量化（与脚本内常量 TITAN_TEXT_V2_MODEL_ID 一致）。
- 第三步（关联上下文）：扫描 data_prepare/semantic_chunk/*_for_chunking.json，根据 chunk 内容中的图片路径
  占位符（如 ![...](image_xxx.png)）匹配当前图像，得到 related_chunk_ids，写入该图像向量的 metadata。
- 输出：写入与 phase3_text_QA_vectorize 相同的 persist 目录（默认 data_prepare/processed_data/chromadb_ver3），
  collection 名为「image_embeddings」；每条 metadata 含 doc_name、image_path、image_description、related_chunk_ids。
- 可通过 --persist-dir 指定持久化目录。
"""

import base64
import json
import re
import sys
import time
import threading
import signal
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Tuple, Set
import boto3
from botocore.exceptions import ClientError

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
    IMAGES_DIR = Path(_cfg["intermediate"]["images"])
    SEMANTIC_CHUNK_DIR = Path(_cfg["intermediate"]["semantic_chunk"])
    DEFAULT_PERSIST_DIR = Path(_cfg["output"]["chromadb"])
except Exception:
    DATA_PREPARE_DIR = Path(__file__).resolve().parents[1]
    PROCESSED_DATA_DIR = DATA_PREPARE_DIR / "processed_data"
    IMAGES_DIR = PROCESSED_DATA_DIR / "images"
    SEMANTIC_CHUNK_DIR = PROCESSED_DATA_DIR / "semantic_chunk"
    DEFAULT_PERSIST_DIR = PROCESSED_DATA_DIR / "chromadb_ver3"

# 从 pipeline_config.json 的 aws / vectorizing 读取（与 phase3_text_QA_vectorize 一致）
_img_cfg = {}
try:
    from pipeline_config_loader import load_config as _load_cfg
    _img_cfg = _load_cfg(ensure_dirs=False)
except Exception:
    pass
_img_aws = _img_cfg.get("aws") or {}
_img_vec = _img_cfg.get("vectorizing") or {}
_img_chromadb = _img_vec.get("chromadb") or {}
CLAUDE_MODEL_ID = _img_aws.get("claude_model", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
TITAN_TEXT_V2_MODEL_ID = _img_aws.get("embedding_model", "amazon.titan-embed-text-v2:0")
TITAN_TEXT_V2_OUTPUT_DIM = 1024
BEDROCK_REGION = _img_aws.get("region", "us-west-2")
CHROMADB_DEFAULT_REBUILD = bool(_img_chromadb.get("rebuild", False))
CHROMADB_DEFAULT_PERSIST_DIR = _img_cfg.get("output", {}).get("chromadb") or str(DEFAULT_PERSIST_DIR)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MIME_MAP = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}


def detect_image_media_type(raw: bytes, path: Path) -> str:
    """根据图片真实字节内容识别 MIME，识别不到时回退到后缀名。"""
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if raw.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if raw.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp"
    return MIME_MAP.get(path.suffix.lower(), "image/png")


def normalize_path_key(p: str) -> str:
    """
    规范化路径字符串，用于图像路径与 for_chunking 来源的匹配。
    统一 Unicode（NFKC）、去除首尾空白、统一斜杠，避免因编码/空格/格式差异导致匹配失败。
    """
    if not p or not isinstance(p, str):
        return ""
    p = unicodedata.normalize("NFKC", p)
    p = p.strip().replace("\\", "/")
    # 去掉多余连续斜杠，保留单斜杠
    parts = [part.strip() for part in p.split("/") if part.strip()]
    return "/".join(parts)


def list_all_images() -> List[Tuple[Path, str, str]]:
    """列出 images 下所有图片，返回 [(Path, doc_name, relative_path)]。"""
    if not IMAGES_DIR.exists():
        return []
    out = []
    for doc_dir in sorted(IMAGES_DIR.iterdir()):
        if not doc_dir.is_dir():
            continue
        doc_name = doc_dir.name
        for f in sorted(doc_dir.iterdir()):
            if not f.is_file() or f.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            rel = f"{doc_name}/{f.name}"
            out.append((f, doc_name, rel))
    return out


def image_to_base64(path: Path) -> Tuple[str, str]:
    """读取图片并转为 base64，返回 (base64_data, media_type)。"""
    raw = path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    mime = detect_image_media_type(raw, path)
    return b64, mime


def understand_image_with_claude(client, image_b64: str, media_type: str, max_retries: int = 5) -> str:
    """使用 Claude 3.5 Sonnet 理解图像，返回描述文本。带重试机制。"""
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": """你是一名资深嵌入式系统与通信协议工程师。请根据提供的图像，生成一段**简洁、准确、结构化**的技术描述，用于后续向量检索。遵循以下规则：

1. **先判断图像类型**：从以下类别中选择最匹配的一项：
   - 终端日志（含 AT 命令、URC 消息、错误码）
   - 设备 UI 界面（设置菜单、状态页、弹窗）
   - 硬件设备照片（整机、模块、指示灯、接口）
   - 数据图表（信号强度、电压电流、时序图）
   - 其他（无法归类）

2. **提取关键信息**：
   - 若为终端日志：列出所有 AT 命令、响应、URC（如 QIURC, +CME ERROR）、错误码、状态值。
   - 若为 UI 界面：记录当前页面标题、关键字段值（如 APN、IP 地址、SIM 状态）、错误提示文本。
   - 若为硬件照片：描述设备型号（如有）、指示灯颜色/闪烁状态、线缆连接情况、物理开关位置。
   - 若为图表：说明横纵轴含义、关键数据点、异常区间。

3. **技术解读（1–2 句）**：
   - 用专业术语解释图像反映的现象或问题。
   - 避免猜测，仅基于图像内容推断。
   - 使用标准术语（如 “PDP 上下文去激活” 而非 “网络断了”）。


注意：
- 不要添加建议、解决方案或“可能”“也许”等不确定表述。
- 不要使用 Markdown、代码块或换行符以外的格式。
- 如果图像模糊或信息不足，如实说明“图像不清晰，无法识别具体内容”。""",
                    },
                ],
            }
        ],
    })
    
    # ThrottlingException 时使用较长退避，避免频繁触发限流
    retry_delay = 5.0
    throttle_delay = 15.0  # 限流时首次等待 15 秒，再按指数增加
    for attempt in range(max_retries):
        try:
            response = client.invoke_model(
                modelId=CLAUDE_MODEL_ID,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            data = json.loads(response["body"].read())
            content = data.get("content", [])
            if content and len(content) > 0:
                text = content[0].get("text", "")
                return text
            else:
                return ""
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == 'ThrottlingException' and attempt < max_retries - 1:
                wait_time = throttle_delay * (2 ** attempt)
                print(f"    [限流] 等待 {wait_time:.0f}s 后重试 ({attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
                continue
            code = e.response.get("Error", {}).get("Code", "")
            msg = e.response.get("Error", {}).get("Message", str(e))
            raise Exception(f"Claude 图像理解失败 [{code}]: {msg}")
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                time.sleep(wait_time)
                continue
            raise Exception(f"Claude 图像理解异常: {e}")
    
    return ""


def embed_text_with_titan(client, text: str, max_retries: int = 3) -> List[float]:
    """使用 Titan Text v2 对文本做嵌入，返回向量。带重试机制。"""
    body = json.dumps({
        "inputText": text,
        "dimensions": TITAN_TEXT_V2_OUTPUT_DIM,
        "normalize": True,
    })
    
    retry_delay = 1.0
    for attempt in range(max_retries):
        try:
            response = client.invoke_model(
                modelId=TITAN_TEXT_V2_MODEL_ID,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            data = json.loads(response["body"].read())
            embedding = data.get("embedding", [])
            if not embedding:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                raise Exception("Titan 嵌入返回为空")
            return embedding
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == 'ThrottlingException' and attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt) * 2
                time.sleep(wait_time)
                continue
            code = e.response.get("Error", {}).get("Code", "")
            msg = e.response.get("Error", {}).get("Message", str(e))
            raise Exception(f"Titan 嵌入失败 [{code}]: {msg}")
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (2 ** attempt))
                continue
            raise Exception(f"Titan 嵌入异常: {e}")
    
    raise Exception("Titan 嵌入失败（已重试所有次数）")


def build_image_to_chunk_mapping() -> Dict[str, List[str]]:
    """
    扫描 semantic_chunk/*_for_chunking.json，建立图像路径 -> chunk_id 列表的映射。
    返回: {image_path: [chunk_id1, chunk_id2, ...]}
    """
    mapping: Dict[str, List[str]] = {}
    image_pattern = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')
    
    if not SEMANTIC_CHUNK_DIR.exists():
        print(f"⚠ semantic_chunk 目录不存在，跳过图像-chunk 关联建立")
        return mapping
    
    chunk_files = list(SEMANTIC_CHUNK_DIR.glob("*_for_chunking.json"))
    if not chunk_files:
        print(f"⚠ 未找到 for_chunking.json 文件，跳过图像-chunk 关联建立")
        return mapping
    
    print(f"扫描 {len(chunk_files)} 个 for_chunking.json 文件，建立图像-chunk 关联...")
    
    for chunk_file in chunk_files:
        try:
            # 文档名来自 for_chunking 文件名（去掉 _for_chunking 后缀），用于与 images 下文件夹名匹配
            doc_name_from_file = chunk_file.stem.replace("_for_chunking", "")
            with open(chunk_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                chunks = data.get('chunks', [])
                
                for ch in chunks:
                    meta = ch.get('metadata', {})
                    content = ch.get('content', '')
                    chunk_id = meta.get('chunk_id', '')
                    
                    if not chunk_id:
                        continue
                    
                    # 提取 content 中的图像路径
                    image_paths = image_pattern.findall(content)
                    for img_path in image_paths:
                        img_path = (img_path or "").strip()
                        if not img_path:
                            continue
                        # 统一为 doc_name/image_xxx.png：chunk 里可能只有 image_xxx.png
                        if "/" not in img_path:
                            full_key = f"{doc_name_from_file}/{img_path}"
                        else:
                            full_key = img_path
                        key = normalize_path_key(full_key)
                        if not key:
                            continue
                        if key not in mapping:
                            mapping[key] = []
                        if chunk_id not in mapping[key]:
                            mapping[key].append(chunk_id)
        except Exception as e:
            print(f"  ⚠ 读取 {chunk_file.name} 失败: {e}")
            continue
    
    total_images = len(mapping)
    total_links = sum(len(chunk_ids) for chunk_ids in mapping.values())
    print(f"✓ 建立 {total_images} 个图像与 {total_links} 个 chunk 的关联")
    print(f"  （说明：仅统计在 semantic_chunk/*_for_chunking.json 的 chunk 正文中出现过占位符的图像；")
    print(f"   仅已关联的图像会进入后续处理流程）\n")
    return mapping


def is_image_linked(rel_path: str, doc_name: str, img_basename: str, mapping: Dict[str, List[str]]) -> bool:
    """判断该图片是否在 mapping 中有关联（与查找 related_chunk_ids 逻辑一致）。"""
    norm_rel = normalize_path_key(rel_path)
    if norm_rel in mapping:
        return True
    norm_doc = normalize_path_key(doc_name)
    for map_key, chunk_ids in mapping.items():
        key_parts = map_key.split("/", 1)
        key_doc = normalize_path_key(key_parts[0]) if len(key_parts) > 1 else ""
        key_basename = key_parts[-1].split("/")[-1] if key_parts else ""
        if key_doc == norm_doc and key_basename == img_basename:
            return True
    return False


def main():
    import argparse
    try:
        import chromadb
        from chromadb.config import Settings
    except ImportError:
        print("✗ 请先安装 chromadb: pip install chromadb")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="图像理解+向量化并写入 ChromaDB（image_embeddings）")
    parser.add_argument(
        "--persist-dir",
        type=str,
        default=CHROMADB_DEFAULT_PERSIST_DIR,
        help="ChromaDB 持久化目录（默认从 pipeline_config.json output.chromadb 读取，需与 phase3_text_QA_vectorize 一致）",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="每张图片处理前的等待秒数，用于降低 API 限流概率（默认: 1.0，遇 Throttling 可改为 2 或 3）",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        default=CHROMADB_DEFAULT_REBUILD,
        help="重建 image_embeddings（会删除旧数据）；默认从 pipeline_config.json vectorizing.chromadb.rebuild 读取，通常为增量(False)",
    )
    args = parser.parse_args()
    persist_dir = args.persist_dir
    request_delay = max(0.0, args.delay)
    rebuild = args.rebuild

    all_images = list_all_images()
    if not all_images:
        print(f"✗ 未找到图片：{IMAGES_DIR}")
        sys.exit(1)

    print(f"找到 {len(all_images)} 张图片")
    print(
        f"流程：Claude 4.5 haiku 图像理解 → Titan embed-text-v2 文本嵌入（维度 {TITAN_TEXT_V2_OUTPUT_DIM}）"
    )
    print(f"写入策略: {'重建(rebuild)' if rebuild else '增量(upsert)'}")
    print(f"ChromaDB 路径: {persist_dir}\n")

    # 建立图像-chunk 关联映射，仅已关联的图像进入处理流程
    image_to_chunks = build_image_to_chunk_mapping()
    items = [
        (path, doc_name, rel_path)
        for path, doc_name, rel_path in all_images
        if is_image_linked(rel_path, doc_name, path.name, image_to_chunks)
    ]
    skipped = len(all_images) - len(items)
    if skipped > 0:
        print(f"仅处理已与 for_chunking 关联的图像：{len(items)} 张（跳过未关联 {skipped} 张）\n")
    if not items:
        print("✗ 没有已关联的图片，无需处理")
        sys.exit(0)

    # 初始化 Bedrock 客户端（每个线程会创建独立的 client）
    stop_event = threading.Event()
    
    def signal_handler(signum, frame):
        print("\n\n⚠ 收到中断信号，正在停止...")
        stop_event.set()
    
    # 注册信号处理器
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGINT, signal_handler)
    
    def process_single_image(item_data: Tuple[int, Path, str, str]) -> Tuple[int, Dict[str, Any] | None]:
        """处理单张图片的函数，用于并发调用"""
        idx, img_path, doc_name, rel_path = item_data
        
        if stop_event.is_set():
            return (idx, None)
        
        try:
            # 为每个线程创建独立的 client
            client_bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
            
            # 1. 读取图片并转为 base64
            image_b64, media_type = image_to_base64(img_path)
            
            if stop_event.is_set():
                return (idx, None)
            
            # 2. Claude 图像理解
            description = understand_image_with_claude(client_bedrock, image_b64, media_type)
            if not description:
                return (idx, {"error": "图像理解返回为空"})
            
            if stop_event.is_set():
                return (idx, None)
            
            # 3. Titan Text v2 嵌入描述文本
            embedding = embed_text_with_titan(client_bedrock, description)
            
            # 4. 查找关联的 chunk_id（规范化路径匹配 + 按「文档名+文件名」回退，兼容格式差异）
            related_chunk_ids: Set[str] = set()
            norm_rel = normalize_path_key(rel_path)
            if norm_rel in image_to_chunks:
                related_chunk_ids.update(image_to_chunks[norm_rel])
            else:
                # 回退：按「规范化文档名 + 文件名」匹配（解决图像文件夹名与 for_chunking 文件名不完全一致）
                norm_doc = normalize_path_key(doc_name)
                img_basename = img_path.name
                for map_key, chunk_ids in image_to_chunks.items():
                    key_parts = map_key.split("/", 1)
                    key_doc = normalize_path_key(key_parts[0]) if len(key_parts) > 1 else ""
                    key_basename = key_parts[-1].split("/")[-1] if key_parts else ""
                    if key_doc == norm_doc and key_basename == img_basename:
                        related_chunk_ids.update(chunk_ids)
                        break
            
            related_chunk_ids_str = ','.join(sorted(related_chunk_ids)) if related_chunk_ids else ''
            
            return (idx, {
                "embedding": embedding,
                "metadata": {
                    "doc_name": doc_name[:500],
                    "image_path": rel_path[:1000],
                    "image_description": description[:5000],
                    "related_chunk_ids": related_chunk_ids_str[:2000],
                },
                "id": f"img_{rel_path.replace('/', '_')}",
                "document": description[:10000],
                "related_chunk_count": len(related_chunk_ids),
            })
        except Exception as e:
            return (idx, {"error": str(e)})

    print(f"开始顺序处理 {len(items)} 张图片（每张图片需调用 2 次 API）...")
    if request_delay > 0:
        print(f"请求间隔: {request_delay}s（降低限流概率）")
    print(f"提示: 按 Ctrl+C 可中断\n")
    
    all_results: Dict[int, Dict[str, Any]] = {}
    start_time = time.time()
    
    try:
        for idx, (img_path, doc_name, rel_path) in enumerate(items):
            if stop_event.is_set():
                print("\n⚠ 已停止")
                break
            if idx > 0 and request_delay > 0:
                time.sleep(request_delay)
            try:
                _, result = process_single_image((idx, img_path, doc_name, rel_path))
                all_results[idx] = result
                completed = idx + 1
                if result and "error" not in result:
                    chunk_info = f"，关联 {result.get('related_chunk_count', 0)} 个 chunk" if result.get('related_chunk_count', 0) > 0 else ""
                    print(f"[{completed}/{len(items)}] ✓ {rel_path}{chunk_info}")
                elif result and "error" in result:
                    print(f"[{completed}/{len(items)}] ✗ {rel_path}: {result['error']}")
                if completed % 10 == 0 or completed == len(items):
                    elapsed = time.time() - start_time
                    rate = completed / elapsed if elapsed > 0 else 0
                    eta = (len(items) - completed) / rate if rate > 0 else 0
                    print(f"  总体进度: {completed}/{len(items)} ({completed*100//len(items)}%) | "
                          f"速度: {rate:.2f} 张/秒 | 预计剩余: {eta:.0f} 秒\n")
            except Exception as e:
                all_results[idx] = {"error": str(e)}
                completed = idx + 1
                print(f"[{completed}/{len(items)}] ✗ 处理失败: {e}")
    except KeyboardInterrupt:
        print("\n⚠ 用户中断")
        stop_event.set()
    
    # 整理结果
    all_embeddings: List[List[float]] = []
    all_metadatas: List[Dict[str, Any]] = []
    all_ids: List[str] = []
    all_documents: List[str] = []
    
    for idx in range(len(items)):
        if idx in all_results and all_results[idx] and "error" not in all_results[idx]:
            result = all_results[idx]
            all_embeddings.append(result["embedding"])
            all_metadatas.append(result["metadata"])
            all_ids.append(result["id"])
            all_documents.append(result["document"])
        elif idx not in all_results or not all_results[idx]:
            # 跳过未完成的
            pass

    if not all_embeddings:
        print("\n✗ 没有成功处理的图片")
        sys.exit(1)

    print(f"\n成功处理 {len(all_embeddings)} 张图片，写入 ChromaDB...")

    # 写入 ChromaDB（同一 DB，无 embedding_function，仅写入预计算向量）
    client_chroma = chromadb.PersistentClient(
        path=persist_dir,
        settings=Settings(anonymized_telemetry=False, allow_reset=True),
    )
    if rebuild:
        try:
            client_chroma.delete_collection("image_embeddings")
            print("✓ 已删除旧集合 image_embeddings")
        except Exception:
            pass

    collection = client_chroma.get_or_create_collection(
        name="image_embeddings",
        metadata={"hnsw:space": "cosine"},
    )
    # 按 Chroma 限制分批 add（单次不宜过大）
    add_batch = 500
    for j in range(0, len(all_embeddings), add_batch):
        collection.upsert(
            ids=all_ids[j : j + add_batch],
            embeddings=all_embeddings[j : j + add_batch],
            metadatas=all_metadatas[j : j + add_batch],
            documents=all_documents[j : j + add_batch],
        )
    print(f"✓ image_embeddings 写入完成（upsert，新增或更新）: {len(all_embeddings)} 条")
    print("✓ 与 qa_knowledge_base、semantic_chunks 同库，检索时可三路召回（文本+图像）")
    print("✓ 图像-上下文关联已建立：image_embeddings.metadata.related_chunk_ids 指向 semantic_chunks.chunk_id")
    try:
        from pipeline_run_logger import append_run_record
        append_run_record(
            step_id="phase3_image",
            script="phase3_image_vectorize.py",
            status="success",
            files_processed=len(all_embeddings),
            detail={"persist_dir": str(persist_dir)},
        )
    except Exception as e:
        print(f"[run_log] 写入运行记录失败: {e}")


if __name__ == "__main__":
    main()
