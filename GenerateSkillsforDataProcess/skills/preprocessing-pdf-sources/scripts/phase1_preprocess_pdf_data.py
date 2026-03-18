"""
脚本：phase1_preprocess_pdf_data.py（数据预处理与中间文件持久化，本地可重复构建）

唯一入口：遍历 data_prepare/source_file 下所有 .pdf 与 .md 文件，按后缀分别走 PDF 流程或 MD 流程；
也可通过 --pdf-only / --md-only 指定单文件处理。

一、PDF 流程（.pdf）
   - 使用 Unstructured 将 PDF 转为 Markdown（含 base64 图片或占位符）。
   - 将文档中的图片提取到 data_prepare/images/<doc_name>/ 目录，文件名规范化（Windows 安全、短 hash 防冲突）。
   - 在 Markdown 正文中把图片引用替换为占位符 ![...](image_xxx.png)，便于后续 phase2/phase3 按路径关联。
   - 生成 data_prepare/markdown/<doc_name>_processed.json：含文档元数据、content（sections 结构）、references、
     以及从正文中解析出的 [[DOC_REF name="..."] 引用；同时可追加写入 markdown/mapping.json 的引用边（JSON Lines）。
   - 文档内只保留图像占位符与 DOC_REF，不做 OCR/图像理解回填；图像由 phase3_image_vectorize 等脚本单独向量化。

二、MD 流程（.md）
   - 若文件不在 markdown 目录则先复制到 data_prepare/markdown/。
   - 扫描正文中的图片引用，将图片提取到 data_prepare/images/<doc_name>/，并在正文中替换为占位符。
   - 生成 data_prepare/markdown/<doc_name>_processed.json，结构同 PDF 流程；同样支持 mapping.json 引用边追加。

三、输出与下游
   - markdown/*_processed.json 供 phase2_generate_for_chunking_json 按 section 生成 for_chunking.json。
   - markdown/mapping.json（及可选的 mapping_merged.json，由 phase1_consolidate_mapping_json 整合）用于文档引用关系。
   - images/<doc_name>/* 供 phase3_image_vectorize 做图像理解与向量化。
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import os
import re
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import boto3
from botocore.config import Config

from unstructured_client import UnstructuredClient
from unstructured_client.models import operations, shared
from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode
from common_schema import (
    build_asset_record,
    infer_layer_from_source_tree,
    stable_version_from_mapping,
)


def normalize_doc_name(name: str) -> str:
    """
    规范化文档名（用于“引用/检索匹配”的稳定键）：
    - Unicode NFKC（统一全角半角/兼容字符）
    - 去首尾空白、压缩连续空白
    - 统一路径分隔符为空格（避免出现 `a/b` 这种歧义）
    """
    s = unicodedata.normalize("NFKC", (name or ""))
    s = s.replace("\\", " ").replace("/", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_ref_text(text: str) -> str:
    """
    规范化“引用锚文本”（用于 DOC_REF / references / mapping 边）：
    - Unicode NFKC
    - 去首尾空白、压缩连续空白
    - 不做文件名安全化（引用名允许包含更多符号）
    - 替换双引号，避免破坏 `[[DOC_REF name="..."]]` 语法
    """
    s = unicodedata.normalize("NFKC", (text or ""))
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace('"', "'")
    return s


def make_windows_safe_filename(name: str, max_len: int = 120) -> str:
    """
    将任意字符串转换为 Windows 安全的文件名（不含路径）。
    - 替换 Windows 禁止字符：<>:"/\\|?*
    - 去掉尾部空格/点
    - 控制最大长度，超长时截断并附加短 hash 保持稳定
    """
    s = name or ""
    # 禁止字符替换为下划线
    s = re.sub(r'[<>:"/\\\\|\\?\\*]', "_", s)
    # 控制字符替换
    s = re.sub(r"[\x00-\x1f]", "_", s)
    # 压缩下划线与空白
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"_+", "_", s).strip("_")
    # Windows 不允许结尾是空格或点
    s = s.rstrip(" .")
    if not s:
        s = "doc"

    if len(s) > max_len:
        h = hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]
        s = s[: max(1, max_len - 9)].rstrip(" ._")
        s = f"{s}__{h}"
    return s


DOC_REF_PLACEHOLDER_RE = re.compile(r'\[\[DOC_REF\s+name="([^"]+)"\s*\]\]')
TABLE_PLACEHOLDER_RE = re.compile(
    r'\[\[TABLE\s+type="(summary|file)"\s+summary="([^"]*)"(?:\s+path="([^"]*)")?\s*\]\]'
)


def _make_doc_ref_placeholder(doc_name: str) -> str:
    # doc_name 来自 PDF 锚文本（已在 normalize_ref_text 中处理双引号）；允许包含空格/符号
    return f'[[DOC_REF name="{doc_name}"]]'


def extract_references_from_markdown(md_text: str) -> List[str]:
    """
    从 Markdown 文本中提取引用的目标文档名列表（去重，保序）。
    引用来源是 `[[DOC_REF name="..."]]` 占位符。
    """
    if not md_text:
        return []
    seen: set[str] = set()
    refs: List[str] = []
    for m in DOC_REF_PLACEHOLDER_RE.finditer(md_text):
        name = (m.group(1) or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        refs.append(name)
    return refs


def _load_existing_doc_names(markdown_dir: Path) -> set[str]:
    """
    扫描 markdown_dir 下所有 *_processed.json 文件，提取所有文档名（source 字段）。
    用于“引用名 -> 文档名”匹配，解决锚文本与文档名不一致的问题。
    """
    doc_names: set[str] = set()
    for proc_file in markdown_dir.glob("*_processed.json"):
        try:
            data = json.loads(proc_file.read_text(encoding="utf-8"))
            source = data.get("metadata", {}).get("source", "").strip()
            if source:
                doc_names.add(source)
        except Exception:
            continue
    return doc_names


def _match_ref_to_doc_name(ref_name: str, existing_doc_names: set[str]) -> Optional[str]:
    """
    尝试将引用名（锚文本）匹配到已存在的文档名。
    
    匹配策略（优先级从高到低）：
    1. 完全匹配（标准化后）
    2. 包含匹配：引用名包含文档名，或文档名包含引用名
    3. 标准化后包含匹配：去掉空格/标点后能匹配
    
    返回：匹配到的文档名，或 None（保留原引用名）
    """
    if not ref_name or not existing_doc_names:
        return None
    
    ref_norm = normalize_ref_text(ref_name)
    ref_norm_no_space = re.sub(r"\s+", "", ref_norm)
    
    # 1. 完全匹配（标准化后）
    for doc_name in existing_doc_names:
        doc_norm = normalize_doc_name(doc_name)
        if ref_norm == doc_norm:
            return doc_name
    
    # 2. 包含匹配（标准化后）
    for doc_name in existing_doc_names:
        doc_norm = normalize_doc_name(doc_name)
        # 引用名包含文档名，或文档名包含引用名
        if ref_norm in doc_norm or doc_norm in ref_norm:
            return doc_name
    
    # 3. 去掉空格后包含匹配（处理 "设备uptime" vs "设备 uptime" 的情况）
    for doc_name in existing_doc_names:
        doc_norm_no_space = re.sub(r"\s+", "", normalize_doc_name(doc_name))
        if ref_norm_no_space and doc_norm_no_space and (
            doc_norm_no_space in ref_norm_no_space or ref_norm_no_space in doc_norm_no_space
        ):
            return doc_name
    
    return None


def append_mapping_edges_jsonl(mapping_path: Path, source: str, targets: List[str], markdown_dir: Optional[Path] = None) -> None:
    """
    按“逐条边一行”的方式追加写 mapping.json：
    - 每条引用写一行：{"A":"B"}
    - 文件不存在则创建
    - 去重只在当前文档内做（targets 已去重），不读取历史文件
    
    新增：尝试将引用名匹配到已存在的文档名（解决锚文本与文档名不一致的问题）。
    """
    src = (source or "").strip()
    if not src:
        return
    tgts_in = [str(t).strip() for t in (targets or []) if str(t).strip()]
    if not tgts_in:
        return

    p = Path(mapping_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    # 尝试匹配引用名到文档名
    matched_targets: List[str] = []
    if markdown_dir and markdown_dir.exists():
        existing_doc_names = _load_existing_doc_names(markdown_dir)
        for t in tgts_in:
            matched = _match_ref_to_doc_name(t, existing_doc_names)
            matched_targets.append(matched if matched else t)
    else:
        matched_targets = tgts_in

    # 当前文档内去重（保序）
    seen: set[str] = set()
    tgts: List[str] = []
    for t in matched_targets:
        if t not in seen:
            seen.add(t)
            tgts.append(t)

    with p.open("a", encoding="utf-8") as f:
        for t in tgts:
            f.write(json.dumps({src: t}, ensure_ascii=False))
            f.write("\n")


def _extract_pdf_annotation_links(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    使用 PyMuPDF 提取 PDF 注释层的可点击链接（URI / 文件链接 / 内部跳转）。
    返回元素示例：
    {
      "page": 1,
      "kind": "uri|file|page|other",
      "target": "https://... 或 xxx.pdf 或 page:12",
      "anchor_text": "可点击文字（从链接矩形区域截取）"
    }
    """
    if not ENABLE_PDF_ANNOTATION_LINKS:
        return []

    try:
        import fitz  # type: ignore  # PyMuPDF
    except Exception as e:
        raise ImportError("启用了 ENABLE_PDF_ANNOTATION_LINKS，但未安装 PyMuPDF。请先执行：pip install pymupdf") from e

    links_out: List[Dict[str, Any]] = []
    doc = fitz.open(str(pdf_path))
    try:
        for page_index in range(len(doc)):
            page = doc[page_index]
            for lk in page.get_links() or []:
                rect = lk.get("from")
                if rect is None:
                    continue

                r = fitz.Rect(rect)

                # 目标
                target = ""
                kind = "other"
                if lk.get("uri"):
                    kind = "uri"
                    target = str(lk.get("uri") or "").strip()
                elif lk.get("file"):
                    kind = "file"
                    target = str(lk.get("file") or "").strip()
                elif lk.get("page") is not None:
                    kind = "page"
                    target = f"page:{int(lk.get('page')) + 1}"
                else:
                    kind = "other"
                    target = ""

                # 锚文本（从链接矩形区域截取）
                anchor = (page.get_text("text", clip=r) or "").strip()
                anchor = re.sub(r"\s+", " ", anchor).strip()

                # 如果 clip 取不到文字，尝试用 words 拼出来
                if not anchor:
                    try:
                        words = page.get_text("words") or []
                        picked = [w[4] for w in words if fitz.Rect(w[:4]).intersects(r)]
                        anchor = re.sub(r"\s+", " ", " ".join(picked)).strip()
                    except Exception:
                        anchor = ""

                if not target and not anchor:
                    continue

                links_out.append(
                    {
                        "page": page_index + 1,
                        "kind": kind,
                        "target": target,
                        "anchor_text": anchor,
                    }
                )
    finally:
        doc.close()

    return links_out


def _extract_pdf_doc_refs_from_links(links: List[Dict[str, Any]]) -> List[str]:
    """
    从 PyMuPDF 提取到的链接中，抽取“引用目标文档名”：
    - **不解析 URL/文件名**（内部资料链接可能不含文档名）
    - 直接使用 PDF 中蓝色可点击文本（anchor_text）作为引用名
    - 只处理 kind=uri/file（排除内部 page 跳转）
    """
    refs: List[str] = []
    seen: set[str] = set()
    for lk in links or []:
        kind = (lk.get("kind") or "").strip()
        if kind not in ("uri", "file"):
            continue
        anchor = normalize_ref_text(lk.get("anchor_text") or "")
        # 过滤过短/空锚文本（避免把无意义的点击区域写入 references）
        if len(anchor) < 2:
            continue
        if anchor not in seen:
            seen.add(anchor)
            refs.append(anchor)
    return refs


def _append_doc_refs_to_markdown(md_text: str, doc_refs: List[str]) -> str:
    """
    将 `[[DOC_REF name="..."]]` 尽量“回填到正文锚文本附近”（保留上下文），供后续分块/检索使用。

    策略：
    - 优先：在正文中找到锚文本（doc_refs 中的字符串）第一次出现的位置，在其后插入占位符
    - 回退：如果正文中找不到锚文本，则把占位符追加到文末“引用文档”清单（便于人工检查哪些没命中）

    注意：不追求严格幂等（你已确认），但会避免同一 doc_ref 在同一份 md_text 中重复插入。
    """
    if not md_text or not doc_refs:
        return md_text

    existing = set(extract_references_from_markdown(md_text))
    to_process = [r for r in doc_refs if r and r not in existing]
    if not to_process:
        return md_text

    text = md_text
    appended: List[str] = []

    for ref in to_process:
        placeholder = _make_doc_ref_placeholder(ref)
        # 若正文里已经出现该占位符就跳过
        if placeholder in text:
            continue

        # 构造“抗空格/标点扰动”的匹配模式：
        # - 既能匹配：设备uptime / 设备 uptime
        # - 也能匹配：土耳其NEVA / 土耳其 NEVA
        # - 允许 chunks 之间出现空白或标点（但不允许插入其它字母/数字序列改变顺序）
        chunks = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", ref)
        if not chunks:
            appended.append(ref)
            continue

        connector = r"[\s\W_]*"
        pat = connector.join(re.escape(c) for c in chunks)
        m = re.search(pat, text)
        if not m:
            appended.append(ref)
            continue

        # 避免在同一位置重复插入（简单检查 match 结束后的近邻文本）
        tail = text[m.end() : m.end() + 80]
        if DOC_REF_PLACEHOLDER_RE.search(tail):
            continue

        insertion = " " + placeholder
        text = text[: m.end()] + insertion + text[m.end() :]

    if appended:
        lines = ["", "## 引用文档（用于多跳检索）"]
        for r in appended:
            lines.append(_make_doc_ref_placeholder(r))
        text = text.rstrip() + "\n" + "\n".join(lines) + "\n"

    return text


def _extract_pdf_annotation_links_for_json(pdf_path: Optional[Path]) -> List[Dict[str, Any]]:
    """
    给 processed.json 使用的链接信息（不写回 Markdown，避免污染 content）。
    仅保留轻量字段，便于后续调试/溯源。pdf_path 为 None 或不存在时返回 []。
    """
    if not ENABLE_PDF_ANNOTATION_LINKS or not pdf_path or not pdf_path.exists():
        return []
    links = _extract_pdf_annotation_links(pdf_path)
    out: List[Dict[str, Any]] = []
    for lk in links:
        out.append(
            {
                "page": lk.get("page"),
                "kind": lk.get("kind"),
                "anchor_text": lk.get("anchor_text"),
                "target": lk.get("target"),
            }
        )
    return out

# ============================================================================
# 【配置区域】全部从 pipeline_config.json 读取
# ============================================================================
import sys as _sys
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CONFIGURING = _PROJECT_ROOT / "skills" / "configuring-pipeline"
for _p in (_CONFIGURING, _PROJECT_ROOT):
    if str(_p) not in _sys.path:
        _sys.path.insert(0, str(_p))

def _pdf_config():
    try:
        from pipeline_config_loader import load_config as _load_config
        return _load_config(ensure_dirs=True)
    except Exception:
        return {}

_cfg = _pdf_config()

# 路径
try:
    DATA_PREPARE_DIR = Path(_cfg["input"]["raw_material"]).parent
    PROCESSED_DATA_DIR = DATA_PREPARE_DIR / "processed_data"
    SOURCE_DIR = Path(_cfg["intermediate"]["source_file"])
    MARKDOWN_DIR = Path(_cfg["intermediate"]["markdown"])
    IMAGES_DIR = Path(_cfg["intermediate"]["images"])
    TABLE_CACHE_DIR = Path(_cfg["intermediate"]["table_cache"])
except Exception:
    DATA_PREPARE_DIR = Path(__file__).resolve().parents[1]
    PROCESSED_DATA_DIR = DATA_PREPARE_DIR / "processed_data"
    SOURCE_DIR = DATA_PREPARE_DIR / "source_file"
    MARKDOWN_DIR = PROCESSED_DATA_DIR / "markdown"
    IMAGES_DIR = PROCESSED_DATA_DIR / "images"
    TABLE_CACHE_DIR = PROCESSED_DATA_DIR / "table_cache"

# Unstructured API（托管服务）
_unstructured = _cfg.get("unstructured") or {}
UNSTRUCTURED_API_KEY = (_unstructured.get("api_key") or os.environ.get("UNSTRUCTURED_API_KEY") or "").strip()
UNSTRUCTURED_API_URL = (_unstructured.get("api_url") or "https://api.unstructuredapp.io/general/v0/general").strip()

# AWS
_aws = _cfg.get("aws") or {}
AWS_REGION = _aws.get("region", "us-west-2")
CLAUDE_MODEL_ID = _aws.get("claude_model", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
VISION_MODEL_ID = _aws.get("vision_model", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")

# Tesseract（本地 OCR 回退，可选）
_tess = _cfg.get("tesseract") or {}
TESSERACT_HOME = (_tess.get("home") or os.environ.get("TESSERACT_HOME", r"E:\tesseract") or "").strip() or None
TESSERACT_LANG = _tess.get("lang", "chi_sim+eng")

# PDF 行为
_pdf = _cfg.get("pdf") or {}
DOC_NAME_MAX_LEN = int(_pdf.get("doc_name_max_len", 120))
PDF_STRATEGY = _pdf.get("strategy", "hi_res")
ENABLE_IMAGE_TO_TEXT = bool(_pdf.get("enable_image_to_text", True))
ENABLE_IMAGE_UNDERSTANDING = bool(_pdf.get("enable_image_understanding", True))
ENABLE_PDF_ANNOTATION_LINKS = bool(_pdf.get("enable_pdf_annotation_links", True))

MAPPING_JSON_PATH = MARKDOWN_DIR / "mapping.json"
TABLE_CACHE_REL = "processed_data/table_cache"
# ============================================================================
# 【配置区域结束】
# ============================================================================


class Preprocessor:
    def __init__(
        self,
        unstructured_api_key: str = UNSTRUCTURED_API_KEY,
        unstructured_api_url: str = UNSTRUCTURED_API_URL,
        pdf_strategy: str = PDF_STRATEGY,
        aws_region: str = AWS_REGION,
        tesseract_home: str = TESSERACT_HOME,
        tesseract_lang: str = TESSERACT_LANG,
        claude_model_id: str = CLAUDE_MODEL_ID,
        enable_image_to_text: bool = ENABLE_IMAGE_TO_TEXT,
        enable_image_understanding: bool = ENABLE_IMAGE_UNDERSTANDING,
        vision_model_id: str = VISION_MODEL_ID,
        pdf_dir: Path = SOURCE_DIR,
        markdown_dir: Path = MARKDOWN_DIR,
        images_base_dir: Path = IMAGES_DIR,
    ):
        self.pdf_strategy = pdf_strategy
        self.aws_region = aws_region
        self.model_id = claude_model_id
        self.enable_image_to_text = enable_image_to_text
        self.enable_image_understanding = enable_image_understanding
        self.vision_model_id = (vision_model_id or "").strip() or None
        self.tesseract_home = (tesseract_home or "").strip() or None
        self.tesseract_lang = (tesseract_lang or "").strip() or "chi_sim+eng"

        self.pdf_dir = Path(pdf_dir)
        self.markdown_dir = Path(markdown_dir)
        self.images_base_dir = Path(images_base_dir)
        self.table_cache_dir = TABLE_CACHE_DIR
        self.markdown_dir.mkdir(parents=True, exist_ok=True)
        self.images_base_dir.mkdir(parents=True, exist_ok=True)
        self.table_cache_dir.mkdir(parents=True, exist_ok=True)
        self._bedrock_client = None

        # Unstructured client
        key = unstructured_api_key or UNSTRUCTURED_API_KEY or os.environ.get("UNSTRUCTURED_API_KEY")
        if not key:
            raise ValueError("缺少 Unstructured API Key（请填写 UNSTRUCTURED_API_KEY 或设置环境变量 UNSTRUCTURED_API_KEY）。")
        self.unstructured_client = UnstructuredClient(api_key_auth=key, server_url=unstructured_api_url)

    def get_pdf_name(self, pdf_path: Path) -> str:
        """
        返回“规则后的文档名”（用于输出文件名 & 作为文档唯一标识）。
        规则：raw stem -> normalize -> Windows safe filename。

        注意：若不同 PDF 归一化后发生同名，将直接覆盖输出文件（你已确认接受覆盖策略）。
        """
        raw = pdf_path.stem
        norm = normalize_doc_name(raw)
        return make_windows_safe_filename(norm, max_len=DOC_NAME_MAX_LEN)

    # ---- 图片工具（与原脚本一致）----

    def _list_image_files(self, images_dir: Path) -> List[Path]:
        patterns = ["*.png", "*.jpg", "*.jpeg", "*.gif", "*.webp"]
        files: List[Path] = []
        for pat in patterns:
            files.extend(list(images_dir.glob(pat)))
        return sorted(files, key=lambda p: p.name.lower())

    # ---- 表格工具（MD）----
    def _extract_table_blocks_with_ast(self, md_text: str) -> List[Dict[str, Any]]:
        """
        使用 markdown-it AST 提取 markdown 表格块。
        返回项包含：
        - start_0/end_0: 0-based 行号区间 [start, end)
        - raw_content: 原始表格文本
        """
        md = MarkdownIt("gfm-like", {"maxNesting": 100, "linkify": False})
        tokens = md.parse(md_text)
        root = SyntaxTreeNode(tokens)
        lines = md_text.splitlines(keepends=True)

        blocks: List[Dict[str, Any]] = []
        for node in root.walk():
            if node.type != "table" or not hasattr(node, "map") or node.map is None:
                continue
            start_0, end_0 = node.map
            raw = "".join(lines[start_0:end_0]).strip()
            blocks.append({"start_0": start_0, "end_0": end_0, "raw_content": raw})
        return blocks

    def _parse_gfm_table_to_rows(self, raw_table: str) -> List[List[str]]:
        """
        解析 GFM 表格文本为二维数组。
        """
        rows: List[List[str]] = []
        lines = [ln.strip() for ln in raw_table.strip().splitlines() if ln.strip()]
        for i, line in enumerate(lines):
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if i > 0 and all(re.match(r"^:?-+:?$", c.replace(" ", "")) for c in cells if c):
                continue
            rows.append(cells)
        return rows

    def _rows_to_csv_text(self, rows: List[List[str]]) -> str:
        """
        将表格内容转为 CSV 文本（UTF-8 BOM，保证中文在常见工具中可读）。
        """
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        for row in rows:
            writer.writerow(row)
        return "\ufeff" + buf.getvalue()

    def _get_bedrock_client(self):
        if self._bedrock_client is None:
            cfg = Config(read_timeout=120, connect_timeout=60, retries={"max_attempts": 3})
            self._bedrock_client = boto3.client("bedrock-runtime", region_name=self.aws_region, config=cfg)
        return self._bedrock_client

    def _summarize_table(self, raw_table: str, doc_name: str, table_index: int) -> str:
        """
        对单个表格生成简短语义摘要。
        约束：必须返回可写入占位符的单行文本。
        """
        prompt = f"""你是技术文档结构化助手。请为下面表格生成1-2句摘要。
要求：
1) 语言与表格保持一致（中文表格用中文，英文表格用英文）
2) 准确概括“这张表在定义什么”，尽量包含关键字段/主题
3) 不输出Markdown，不输出项目符号
4) 只输出摘要正文

文档：{doc_name}
表序号：{table_index}
表格内容：
{raw_table[:6000]}
"""
        try:
            resp = self._get_bedrock_client().converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": 400, "temperature": 0.2},
            )
            summary = (
                resp.get("output", {})
                .get("message", {})
                .get("content", [{}])[0]
                .get("text", "")
                .strip()
            )
            if not summary:
                return "该表格包含结构化字段与取值定义。"
            return re.sub(r"\s+", " ", summary).strip()
        except Exception:
            return "该表格包含结构化字段与取值定义。"

    def _make_table_placeholder(self, summary: str, path: Optional[str] = None) -> str:
        safe_summary = (summary or "").replace('"', "'").replace("\n", " ").strip()
        if path:
            safe_path = str(path).replace("\\", "/").strip()
            return f'[[TABLE type="file" summary="{safe_summary}" path="{safe_path}"]]'
        return f'[[TABLE type="summary" summary="{safe_summary}"]]'

    def replace_table_references(self, md_path: Path, doc_name: str) -> Path:
        """
        将 markdown 中表格替换为 TABLE 占位符。
        规则：
        - 所有表格统一导出 CSV 文件
        - 占位符统一使用 file 类型，并带 summary + path
        - 倒序替换避免行号偏移
        """
        text = md_path.read_text(encoding="utf-8")
        blocks = self._extract_table_blocks_with_ast(text)
        if not blocks:
            return md_path

        lines = text.splitlines(keepends=True)
        sorted_blocks = sorted(blocks, key=lambda b: -b["start_0"])
        total = len(sorted_blocks)
        safe_stem = re.sub(r'[<>:"/\\|?*]', "_", doc_name)[:80]

        for idx, block in enumerate(sorted_blocks):
            start_0 = int(block["start_0"])
            end_0 = int(block["end_0"])
            raw = str(block["raw_content"])
            rows = self._parse_gfm_table_to_rows(raw)
            table_num = total - idx  # 保证 table_1 是文档顶部第一张表
            summary = self._summarize_table(raw, doc_name, table_num)
            csv_name = f"{safe_stem}_table_{table_num}.csv"
            csv_path = self.table_cache_dir / csv_name
            csv_path.write_text(self._rows_to_csv_text(rows), encoding="utf-8")
            rel_path = f"{TABLE_CACHE_REL}/{csv_name}"
            placeholder = self._make_table_placeholder(summary=summary, path=rel_path)

            lines[start_0:end_0] = [placeholder + "\n"]

        md_path.write_text("".join(lines), encoding="utf-8")
        return md_path

    # ---- Step 1: PDF -> MD ----
    @staticmethod
    def html_table_to_markdown(html: str, text: str = "") -> str | None:
        """
        按标准 HTML 解析：每个 <tr> 一行，每个 <td>/<th> 一格（含 thead/tbody）。
        若提供 text 且 token 数等于格子数，用 text 按行优先填格以减轻 OCR 错误。
        """
        if not (html or "").strip():
            return None
        html = html.strip()
        m = re.search(r"<table[^>]*>(.*)</table>", html, re.DOTALL | re.IGNORECASE)
        inner = m.group(1) if m else html

        # 按顺序取所有 <tr>...</tr>（thead/tbody 里的 tr 都会按出现顺序拿到）
        trs = re.findall(r"<tr[^>]*>(.*?)</tr>", inner, re.DOTALL | re.IGNORECASE)
        rows = []
        for tr in trs:
            cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.DOTALL | re.IGNORECASE)
            cell_texts = []
            for c in cells:
                t = re.sub(r"<[^>]+>", " ", c)
                t = re.sub(r"\s+", " ", t).strip()
                cell_texts.append(t.replace("|", "\\|"))
            if cell_texts:
                rows.append(cell_texts)

        if not rows:
            return None
        ncols = max(len(r) for r in rows)
        grid = [(r + [""] * ncols)[:ncols] for r in rows]
        nrows, ncols = len(grid), len(grid[0]) if grid else 0
        # 用 text 按行优先填格（token 数须等于格子数）
        if text and nrows * ncols > 0:
            tokens = text.strip().split()
            if len(tokens) == nrows * ncols:
                for i in range(nrows):
                    for j in range(ncols):
                        grid[i][j] = tokens[i * ncols + j].replace("|", "\\|")
        md_lines = []
        for i, row in enumerate(grid):
            md_lines.append("| " + " | ".join(str(c).strip() for c in row) + " |")
            if i == 0:
                md_lines.append("| " + " | ".join(["---"] * ncols) + " |")
        return "\n".join(md_lines)

    def pdf_to_markdown(self, pdf_path: Path) -> Path:
        pdf_name = self.get_pdf_name(pdf_path)
        output_path = self.markdown_dir / f"{pdf_name}.md"

        if self.pdf_strategy == "hi_res":
            strategy = shared.Strategy.HI_RES
        elif self.pdf_strategy == "fast":
            strategy = shared.Strategy.FAST
        else:
            strategy = shared.Strategy.AUTO

        pdf_bytes = pdf_path.read_bytes()

        resp = self.unstructured_client.general.partition(
            request=operations.PartitionRequest(
                partition_parameters=shared.PartitionParameters(
                    files=shared.Files(content=pdf_bytes, file_name=pdf_path.name),
                    strategy=strategy,
                    languages=["chi_sim", "eng"],
                    extract_image_block_types=["Image", "Table"],
                    extract_images_in_pdf=True,
                )
            )
        )

        elements = resp.elements or []
        md_lines: List[str] = []
        for el in elements:
            el_type = el.get("type", "")
            text = (el.get("text") or "").strip()
            metadata = el.get("metadata") or {}

            if el_type == "Title":
                level = metadata.get("category_depth", 1) or 1
                md_lines.append(f"\n{'#' * int(level)} {text}\n")
            elif el_type == "Table":
                table_html = metadata.get("text_as_html")
                md_table = self.html_table_to_markdown(table_html or "", text=text) if table_html else None
                if md_table:
                    md_lines.append("\n" + md_table + "\n")
                else:
                    md_lines.append("\n" + (table_html or text or "") + "\n")
            elif el_type in ["ListItem", "NarrativeText"]:
                if text:
                    md_lines.append(f"{text}\n")
            elif el_type == "Image":
                img_base64 = metadata.get("image_base64")
                if img_base64:
                    md_lines.append(f"\n![image](data:image/png;base64,{img_base64})\n")
                else:
                    md_lines.append("\n[图片]\n")
            else:
                if text:
                    md_lines.append(f"{text}\n")

        md_text = "\n".join(md_lines)
        # 尝试从 PDF 注释层提取可点击链接并回填到 Markdown（用于修复“PDF 可点击但 md 丢链接”的问题）
        doc_refs_from_pdf: List[str] = []
        if ENABLE_PDF_ANNOTATION_LINKS:
            links = _extract_pdf_annotation_links(pdf_path)
            if links:
                doc_refs_from_pdf = _extract_pdf_doc_refs_from_links(links)

        # 仅依赖 PDF 注释层链接生成 DOC_REF（你已说明 md 中不会出现 xxx.pdf 文本）
        if doc_refs_from_pdf:
            # 先尝试匹配锚文本到文档名（解决锚文本与文档名不一致的问题）
            # 这样占位符和 mapping.json 都会使用匹配后的文档名，保证检索时能匹配
            existing_doc_names = _load_existing_doc_names(self.markdown_dir) if self.markdown_dir.exists() else set()
            matched_refs: List[str] = []
            for ref in doc_refs_from_pdf:
                matched = _match_ref_to_doc_name(ref, existing_doc_names)
                matched_refs.append(matched if matched else ref)
            
            # 使用匹配后的引用名（如果匹配成功）来插入占位符
            # 注意：_append_doc_refs_to_markdown 内部会用匹配后的引用名在正文中查找锚文本
            # 如果匹配后的文档名与正文中的锚文本不一致，可能找不到，但这是合理的（匹配失败时保留原引用名）
            md_text = _append_doc_refs_to_markdown(md_text, matched_refs)
            # 追加写 mapping.json（逐条边一行）：A->B、A->C 分成两行写入
            # 使用匹配后的引用名，确保与占位符一致
            append_mapping_edges_jsonl(MAPPING_JSON_PATH, pdf_name, matched_refs, markdown_dir=self.markdown_dir)

        output_path.write_text(md_text, encoding="utf-8")
        return output_path

    # ---- Step 2: extract images from MD ----

    def extract_images_from_markdown(self, md_path: Path, pdf_name: str, min_size: int = 1000) -> Tuple[Path, int]:
        images_dir = self.images_base_dir / pdf_name
        images_dir.mkdir(parents=True, exist_ok=True)

        content = md_path.read_text(encoding="utf-8")
        pattern = r"!\[.*?\]\(data:image/(.*?);base64,(.*?)\)"
        matches = re.findall(pattern, content)

        saved = 0
        counter = 0
        for image_format, b64 in matches:
            try:
                img_bytes = base64.b64decode(b64)
                if len(img_bytes) < min_size:
                    continue
                counter += 1
                ext = (image_format or "png").lower().strip()
                ext = "jpeg" if ext == "jpg" else ext
                file_path = images_dir / f"image_{counter:03d}.{ext}"
                file_path.write_bytes(img_bytes)
                saved += 1
            except Exception:
                continue

        return images_dir, saved

    # ---- Step 4: replace image refs（仅占位符 ![...](image_xxx.png)，不做 OCR/回填）----

    def replace_image_references(self, md_path: Path, pdf_name: str) -> Path:
        content = md_path.read_text(encoding="utf-8")
        images_dir = self.images_base_dir / pdf_name
        existing_images = self._list_image_files(images_dir) if images_dir.exists() else []

        pattern = r"!\[([^\]]*)\]\(data:image/[^;]+;base64,[^)]+\)"
        counter = 0

        def _repl(m: re.Match) -> str:
            nonlocal counter
            alt = m.group(1) or "image"
            if counter < len(existing_images):
                p = existing_images[counter]
                counter += 1
                return f"![{alt}]({p.name})"
            return ""

        new_content = re.sub(pattern, _repl, content)
        md_path.write_text(new_content, encoding="utf-8")
        return md_path

    # ---- Step 5: md -> processed json ----

    def markdown_to_processed_json(
        self, md_path: Path, pdf_name: str, pdf_path: Optional[Path] = None
    ) -> Path:
        content = md_path.read_text(encoding="utf-8")
        images_dir = self.images_base_dir / pdf_name
        images = [p.name for p in self._list_image_files(images_dir)] if images_dir.exists() else []
        pdf_annotation_links = (
            _extract_pdf_annotation_links_for_json(pdf_path)
            if pdf_path and pdf_path.exists()
            else []
        )

        # 引用文档列表：以正文中 `[[DOC_REF ...]]` 为准（便于检查“命中/未命中回退”效果）
        references = extract_references_from_markdown(content)
        table_placeholders = list(TABLE_PLACEHOLDER_RE.finditer(content))
        table_file_count = sum(1 for m in table_placeholders if (m.group(1) or "").strip().lower() == "file")
        table_summary_count = sum(
            1 for m in table_placeholders if (m.group(1) or "").strip().lower() == "summary"
        )

        # 若文档含「# 数字. 标题」形式的案例标题（如典型问题汇总），仅以之为 section 边界，
        # 将 问题描述/问题根因/解决方法 等并入同一 section；否则仍按每个 # 一个 section
        use_case_boundary = bool(re.search(r"^#+\s*\d+\.", content, re.MULTILINE))
        CASE_BOUNDARY_RE = re.compile(r"^\d+\.")

        sections: List[Dict[str, Any]] = []
        current: Dict[str, Any] = {"title": "Introduction", "content": "", "level": 0}
        for line in content.split("\n"):
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                title = line.lstrip("#").strip()
                if use_case_boundary:
                    is_case_boundary = bool(CASE_BOUNDARY_RE.match(title))
                    is_first = len(sections) == 0 and not current["content"].strip()
                    if is_case_boundary or is_first:
                        # 仅在新开一个 section 时才 append 上一段，避免同一 dict 被重复 append
                        if current["content"].strip() or current["title"]:
                            sections.append(current)
                        current = {"title": title, "content": "", "level": level}
                    else:
                        current["content"] += line + "\n"
                else:
                    if current["content"].strip():
                        sections.append(current)
                    current = {"title": title, "content": "", "level": level}
            else:
                current["content"] += line + "\n"
        if current["content"].strip() or current["title"]:
            sections.append(current)

        json_path = self.markdown_dir / f"{pdf_name}_processed.json"

        source_raw = pdf_path.stem if pdf_path else md_path.stem
        source_path = str(pdf_path.absolute()) if pdf_path else str(md_path.absolute())
        processed_at = datetime.now().isoformat()
        processed = {
            "metadata": {
                "source": pdf_name,
                "source_raw": source_raw,
                "source_path": source_path,
                "processed_at": processed_at,
                "markdown_path": str(md_path.absolute()),
                "images_dir": str(images_dir.absolute()) if images_dir.exists() else None,
                "image_count": len(images),
                "section_count": len(sections),
                "reference_count": len(references),
                "table_placeholder_count": len(table_placeholders),
                "table_summary_count": table_summary_count,
                "table_file_count": table_file_count,
                "pdf_annotation_link_count": len(pdf_annotation_links),
                "total_chars": len(content),
            },
            # 方案A：仅维护“引用的目标文档名列表”（文档名即唯一 ID；不做存在性判断）
            "references": references,
            # PDF 注释层链接（不放在 content 里，避免污染后续向量化/QA）
            "pdf_annotation_links": pdf_annotation_links,
            "content": {"full_text": content, "sections": sections, "images": images},
        }

        # phase-1 安全接入 common_schema：只新增 asset_meta，不替换旧 metadata。
        # 多跳、表格、图像链路继续依赖原有 metadata / references / content 结构。
        source_file_path = pdf_path if pdf_path else md_path
        knowledge_layer = infer_layer_from_source_tree(source_file_path, SOURCE_DIR)
        asset_version = stable_version_from_mapping(
            {
                "display_name": pdf_name,
                "source_raw": source_raw,
                "source_path": source_path,
                "references": references,
                "pdf_annotation_links": pdf_annotation_links,
                "sections": sections,
                "images": images,
                "table_placeholder_count": len(table_placeholders),
                "table_summary_count": table_summary_count,
                "table_file_count": table_file_count,
                "total_chars": len(content),
            }
        )
        processed["asset_meta"] = build_asset_record(
            asset_type="document_processed",
            knowledge_layer=knowledge_layer,
            display_name=pdf_name,
            source_name=source_raw,
            source_path=source_path,
            storage_path=json_path,
            version=asset_version,
            created_at=processed_at,
            updated_at=processed_at,
            pipeline_stage="phase1",
            is_source_of_truth=True,
            stats={
                "section_count": len(sections),
                "image_count": len(images),
                "reference_count": len(references),
                "total_chars": len(content),
            },
            attributes={
                "markdown_path": str(md_path.absolute()),
                "images_dir": str(images_dir.absolute()) if images_dir.exists() else None,
                "table_placeholder_count": len(table_placeholders),
                "table_summary_count": table_summary_count,
                "table_file_count": table_file_count,
                "pdf_annotation_link_count": len(pdf_annotation_links),
            },
        ).to_dict()
        json_path.write_text(json.dumps(processed, ensure_ascii=False, indent=2), encoding="utf-8")
        return json_path


    def preprocess_one_md(
        self,
        md_path: Path,
        name: Optional[str] = None,
        pdf_path: Optional[Path] = None,
    ) -> Dict[str, Path]:
        """
        预处理单个 Markdown 文件（不依赖 PDF）：
        - 提取图片到 images/<name>/
        - 替换 Markdown 中的图片引用（base64 -> 文件名）
        - 写入 markdown/<name>_processed.json
        name 默认用 md_path.stem；若由 PDF 流程调用则传入 pdf_name，pdf_path 传入以保留链接等信息。
        """
        doc_name = name if name is not None else md_path.stem
        self.extract_images_from_markdown(md_path, doc_name)
        self.replace_image_references(md_path, doc_name)
        self.replace_table_references(md_path, doc_name)
        processed_json = self.markdown_to_processed_json(md_path, doc_name, pdf_path)
        return {"md": md_path, "processed_json": processed_json}

    def preprocess_one_pdf_core(self, pdf_path: Path) -> Dict[str, Path]:
        """
        预处理单个 PDF（核心部分，不包含图像理解/回填）：
        - PDF -> Markdown
        - 再按 md 流程：提取图片、替换引用、写入 processed.json
        """
        pdf_name = self.get_pdf_name(pdf_path)
        md_path = self.pdf_to_markdown(pdf_path)
        return self.preprocess_one_md(md_path, name=pdf_name, pdf_path=pdf_path)

if __name__ == "__main__":
    """
    唯一入口：遍历 source_file 文件夹，遇 .pdf 按 PDF 流程、遇 .md 按 MD 流程处理。
    - .pdf：PDF -> Markdown -> 提取图片 -> 占位符 ![...](image_xxx.png) -> processed.json
    - .md：复制到 markdown/ -> 提取图片、占位符 -> processed.json
    可选 --md-only <path>：只处理单个 .md 文件。
    """
    import argparse

    parser = argparse.ArgumentParser(description="遍历 source_file 预处理 PDF/MD，输出 markdown/*_processed.json")
    parser.add_argument(
        "--md-only",
        type=str,
        default=None,
        metavar="PATH",
        help="只处理一个 .md 文件（不遍历 source_file）",
    )
    args = parser.parse_args()

    pre = Preprocessor()

    if args.md_only:
        md_path = Path(args.md_only).resolve()
        if not md_path.exists():
            print(f"✗ 文件不存在: {md_path}")
            raise SystemExit(1)
        if md_path.suffix.lower() != ".md":
            print(f"✗ 请指定 .md 文件: {md_path}")
            raise SystemExit(1)
        dest = MARKDOWN_DIR / md_path.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if md_path.resolve() != dest.resolve():
            shutil.copy2(md_path, dest)
        out = pre.preprocess_one_md(dest)
        print(f"✓ 已生成: {out.get('processed_json')}")
        raise SystemExit(0)

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    pdf_files = sorted(SOURCE_DIR.rglob("*.pdf"))
    md_files = sorted(SOURCE_DIR.rglob("*.md"))
    all_files = sorted(pdf_files + md_files, key=lambda p: (str(p.parent), p.name))

    if not all_files:
        print(f"✗ 未找到 .pdf 或 .md 文件：{SOURCE_DIR}")
        raise SystemExit(1)

    print("=" * 80)
    print("预处理脚本：phase1_preprocess_pdf_data.py（唯一入口：遍历 source_file）")
    print("=" * 80)
    print(f"SOURCE_DIR: {SOURCE_DIR}")
    print(f"MARKDOWN_DIR: {MARKDOWN_DIR}")
    print(f"IMAGES_DIR: {IMAGES_DIR}")
    print(f"待处理: {len(pdf_files)} 个 PDF，{len(md_files)} 个 MD，共 {len(all_files)} 个文件")
    print("=" * 80)

    for idx, path in enumerate(all_files, 1):
        suffix = path.suffix.lower()
        print(f"\n{'*' * 80}")
        print(f"[{idx}/{len(all_files)}] {path.name}")
        print(f"{'*' * 80}")
        if suffix == ".pdf":
            doc_name = pre.get_pdf_name(path)
            print(f"文档名: {path.stem} -> {doc_name}")
            out = pre.preprocess_one_pdf_core(path)
            for k, v in out.items():
                print(f"  - {k}: {v}")
        elif suffix == ".md":
            dest_md = MARKDOWN_DIR / path.name
            if path.resolve() != dest_md.resolve():
                dest_md.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest_md)
                print(f"已复制到 {dest_md}")
            out = pre.preprocess_one_md(dest_md)
            for k, v in out.items():
                print(f"  - {k}: {v}")
        else:
            print(f"  跳过（非 .pdf/.md）")

    print("\n全部预处理完成。")
    try:
        from pipeline_run_logger import append_run_record
        append_run_record(
            step_id="phase1_pdf",
            script="phase1_preprocess_pdf_data.py",
            status="success",
            files_processed=len(all_files),
            detail={"pdf_count": len(pdf_files), "md_count": len(md_files)},
        )
    except Exception as e:
        print(f"[run_log] 写入运行记录失败: {e}")
