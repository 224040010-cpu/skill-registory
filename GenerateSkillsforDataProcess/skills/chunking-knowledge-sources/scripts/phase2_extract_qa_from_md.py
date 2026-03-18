"""
脚本：phase2_extract_qa_from_md.py

从 data_prepare/markdown/ 下的 Markdown 文件中提取 Q&A 对并生成元数据，输出到 data_prepare/qa_pair/，
供 phase3_text_QA_vectorize 向量化入 ChromaDB 的 qa_knowledge_base collection。

处理逻辑：
- 输入：data_prepare/markdown/ 下所有 .md 文件（或通过 --file 指定单个文件）。
- 对每个 .md：按 chunk 切分正文后调用 AWS Bedrock Claude（converse API，模型见 BEDROCK_MODEL_ID），
  使用固定 prompt 提取与安装/操作/维护/故障排查/规格/安全等相关的 Q&A 对，要求与文档语言一致（中/英）。
- 输出（均在 data_prepare/qa_pair/）：
  - <doc_stem>_qa.json：含 qa_pairs 数组（question, answer, category, keywords）及 metadata（source 等）；
  - <doc_stem>_qa.md：人类可读的 Q&A 列表；
  - <doc_stem>.md.metadata.json：文档级元数据，便于检索与溯源。
- 若传入 --no-qa：不调用 Claude，仅根据 .md 内容生成 metadata 文件（不生成 _qa.json / _qa.md）。

依赖：boto3、Bedrock 可用权限；markdown 目录必须存在，否则脚本退出。
"""

import os
import sys
import json
import re
import threading
from pathlib import Path
from typing import List, Dict
from common_schema import build_asset_record, stable_version_from_mapping

# Bedrock 配置（从 pipeline_config.json 的 aws 读取）
import sys as _sys
_proj = Path(__file__).resolve().parents[3]
_configuring = _proj / "skills" / "configuring-pipeline"
for _p in (_configuring, _proj):
    if str(_p) not in _sys.path:
        _sys.path.insert(0, str(_p))
_aws_cfg = {}
try:
    from pipeline_config_loader import load_config as _load_cfg
    _aws_cfg = _load_cfg(ensure_dirs=False).get("aws") or {}
except Exception:
    pass
BEDROCK_REGION = _aws_cfg.get("region", "us-west-2")
BEDROCK_MODEL_ID = _aws_cfg.get("bedrock_model", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")


class QAExtractor:
    def __init__(self, enable_qa_extraction: bool = True):
        """
        初始化 QA 提取器
        
        Args:
            enable_qa_extraction: 是否启用 Claude QA 提取
        """
        self.enable_qa_extraction = enable_qa_extraction
        
        # 配置 Bedrock 客户端
        if enable_qa_extraction:
            import boto3
            from botocore.config import Config
            
            config = Config(
                read_timeout=300,
                connect_timeout=60,
                retries={'max_attempts': 3}
            )
            self.bedrock_client = boto3.client(
                'bedrock-runtime', 
                region_name=BEDROCK_REGION, 
                config=config
            )
            self.model_id = BEDROCK_MODEL_ID
            print("✓ Bedrock 客户端已初始化")
        
        # 配置路径：原始输入在 data_prepare，phase 产物统一落到 processed_data
        import sys as _sys
        _proj = Path(__file__).resolve().parents[3]
        _configuring = _proj / "skills" / "configuring-pipeline"
        for _p in (_configuring, _proj):
            if str(_p) not in _sys.path:
                _sys.path.insert(0, str(_p))
        try:
            from pipeline_config_loader import load_config as _load_config
            _cfg = _load_config(ensure_dirs=True)
            self.markdown_dir = Path(_cfg["intermediate"]["markdown"])
            self.qa_pair_dir = Path(_cfg["intermediate"]["qa_pair"])
        except Exception:
            _dp = Path(__file__).resolve().parents[1]
            _pd = _dp / "processed_data"
            self.markdown_dir = _pd / "markdown"
            self.qa_pair_dir = _pd / "qa_pair"
        
        # 创建输出目录
        self.qa_pair_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.markdown_dir.exists():
            print(f"✗ Markdown 目录不存在: {self.markdown_dir}")
            sys.exit(1)

    def _load_processed_asset_meta(self, doc_name: str) -> tuple[dict, dict]:
        """
        读取同名 *_processed.json 中的 metadata / asset_meta。
        只做增强用，不影响现有 QA 提取逻辑。
        """
        processed_path = self.markdown_dir / f"{doc_name}_processed.json"
        if not processed_path.exists():
            return {}, {}
        try:
            data = json.loads(processed_path.read_text(encoding="utf-8"))
            return data.get("metadata") or {}, data.get("asset_meta") or {}
        except Exception:
            return {}, {}
    
    def call_claude(self, prompt: str, max_tokens: int = 8000) -> str:
        """调用 Claude API"""
        try:
            print(f"  调用 Claude (max_tokens={max_tokens}, prompt_size={len(prompt):,} 字符)...")
            response = self.bedrock_client.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": max_tokens, "temperature": 0.3}
            )
            result = response['output']['message']['content'][0]['text']
            print(f"  ✓ Claude 响应成功 (响应大小={len(result):,} 字符)")
            return result
        except Exception as e:
            print(f"  ✗ Claude 调用失败: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def extract_qa_from_chunk(self, chunk: str, chunk_index: int) -> List[Dict]:
        """从文本块提取 QA 对"""
        prompt = f"""Extract Q&A pairs from the charging station manual content below.

CRITICAL Requirements:
1. Extract key information: installation, operation, maintenance, troubleshooting, specs, safety
2. **Use SAME LANGUAGE as document** (English if doc is English, Chinese if Chinese)
3. Questions from user perspective
4. Answers: clear, complete, concise
5. **MUST preserve ALL image tags**: Keep EVERY ![xxx](image_xxx.png) in answers
6. **MUST preserve ALL document references**: Keep EVERY [[DOC_REF name="..."]] in answers
7. Each Q&A independent

Output JSON array only:
```json
[
  {{
    "question": "Question text",
    "answer": "Answer with ![image](image_015.png) and [[DOC_REF name=\"document_name\"]]",
    "category": "Category",
    "keywords": ["key1", "key2"]
  }}
]
```

Content:
{chunk}

JSON only, no explanation."""

        try:
            response = self.call_claude(prompt, max_tokens=8000)
            
            if not response:
                print(f"  ✗ Claude 返回空响应")
                return []
            
            # 打印响应的前 200 字符用于调试
            print(f"  Claude 响应预览: {response[:200]}...")
            
            # 提取 JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                json_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1).strip()
                else:
                    json_match = re.search(r'\[\s*\{.*?\}\s*\]', response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0).strip()
                    else:
                        json_str = response.strip()
            
            qa_pairs = json.loads(json_str)
            
            if not isinstance(qa_pairs, list):
                print(f"  ✗ 响应不是列表类型: {type(qa_pairs)}")
                return []
            
            return qa_pairs
            
        except json.JSONDecodeError as e:
            print(f"  ✗ JSON 解析失败: {e}")
            print(f"  尝试解析的内容: {json_str[:500] if 'json_str' in locals() else 'N/A'}...")
            return []
        except Exception as e:
            print(f"  ✗ 提取失败: {type(e).__name__}: {e}")
            return []
    
    def extract_qa_from_markdown(self, md_path: Path) -> tuple:
        """
        从 Markdown 文件提取 QA 对
        
        Returns:
            (qa_md_path, qa_json_path, qa_count)
        """
        doc_name = md_path.stem
        processed_meta, upstream_asset_meta = self._load_processed_asset_meta(doc_name)
        knowledge_layer = upstream_asset_meta.get("knowledge_layer") or "normative"
        
        print(f"\n{'='*80}")
        print(f"提取 QA 对: {doc_name}")
        print(f"{'='*80}")
        
        if not self.enable_qa_extraction:
            print(f"⚠ QA 提取已禁用")
            return None, None, 0
        
        # 读取 Markdown
        content = md_path.read_text(encoding='utf-8')
        content_size = len(content)
        
        print(f"文档大小: {content_size:,} 字符")
        
        # 智能分块
        if content_size < 30000:
            target_chunks = 1 if content_size < 15000 else 2
            chunk_size = content_size // target_chunks
        elif content_size < 80000:
            target_chunks = 4
            chunk_size = 20000
        else:
            target_chunks = 8
            chunk_size = 15000
        
        print(f"目标分块数: {target_chunks}, 每块约 {chunk_size:,} 字符")
        
        # 按章节分块
        sections = re.split(r'\n## ', content)
        if len(sections) == 1:
            sections = re.split(r'\n# ', content)
            header_prefix = '\n# '
        else:
            header_prefix = '\n## '
        
        print(f"找到 {len(sections)} 个章节")
        
        chunks = []
        current_chunk = ""
        
        for i, section in enumerate(sections):
            section_with_header = f"{header_prefix}{section}" if i > 0 else section
            
            if len(current_chunk) + len(section_with_header) < chunk_size:
                current_chunk += section_with_header
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = section_with_header
        
        if current_chunk:
            chunks.append(current_chunk)
        
        print(f"章节分块后: {len(chunks)} 个块")
        
        # 如果分块不够细，强制按大小分块
        max_chunk_size = max(len(chunk) for chunk in chunks) if chunks else 0
        if len(chunks) < 2 or max_chunk_size > chunk_size * 1.5:
            print(f"⚠ 章节分块不够细（最大块: {max_chunk_size:,} 字符），改用强制大小分块")
            chunks = []
            lines = content.split('\n')
            current_chunk = ""
            
            for line in lines:
                if len(current_chunk) + len(line) + 1 < chunk_size:
                    current_chunk += line + '\n'
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = line + '\n'
            
            if current_chunk:
                chunks.append(current_chunk)
        
        print(f"最终分为 {len(chunks)} 个块")
        for i, chunk in enumerate(chunks, 1):
            print(f"  块 {i}: {len(chunk):,} 字符")
        
        # 提取 QA 对
        all_qa_pairs = []
        
        for i, chunk in enumerate(chunks, 1):
            print(f"\n处理块 {i}/{len(chunks)} ({len(chunk):,} 字符)...")
            qa_pairs = self.extract_qa_from_chunk(chunk, i)
            
            if qa_pairs is None:
                print(f"⚠ 块 {i} 返回 None，继续处理下一块")
                continue
            
            if len(qa_pairs) == 0:
                print(f"⚠ 块 {i} 未提取到 QA 对")
            else:
                print(f"✓ 块 {i} 提取了 {len(qa_pairs)} 个问答对")
                all_qa_pairs.extend(qa_pairs)
            
            # 避免 API 限流
            if i < len(chunks):
                event = threading.Event()
                event.wait(timeout=3.0)
        
        print(f"\n✓ 共提取 {len(all_qa_pairs)} 个问答对")
        
        # 生成 QA Markdown（输出到 qa_pair 目录）
        qa_md_path = self.qa_pair_dir / f"{doc_name}_qa.md"
        qa_lines = []
        
        for i, qa in enumerate(all_qa_pairs, 1):
            qa_lines.append(f"## Q{i}: {qa['question']}")
            qa_lines.append(f"**Category:** {qa.get('category', 'N/A')}")
            qa_lines.append(f"\n**Answer:**\n{qa['answer']}")
            qa_lines.append("\n---\n")
        
        qa_md_path.write_text("\n".join(qa_lines), encoding='utf-8')
        
        # 保存 JSON（输出到 qa_pair 目录，供 phase3_text_QA_vectorize 读取）
        qa_json_path = self.qa_pair_dir / f"{doc_name}_qa.json"
        qa_body = {
            "metadata": {
                "source": doc_name,
                "source_type": "document_qa",
                "source_path": processed_meta.get("source_path", ""),
                "total": len(all_qa_pairs),
                "knowledge_layer": knowledge_layer,
            },
            "qa_pairs": all_qa_pairs
        }
        qa_body["asset_meta"] = build_asset_record(
            asset_type="qa_dataset",
            knowledge_layer=knowledge_layer,
            display_name=doc_name,
            source_name=processed_meta.get("source_raw") or doc_name,
            source_path=processed_meta.get("source_path") or "",
            storage_path=qa_json_path,
            version=stable_version_from_mapping(qa_body),
            created_at=processed_meta.get("processed_at"),
            updated_at=processed_meta.get("processed_at"),
            pipeline_stage="phase2",
            is_source_of_truth=False,
            stats={"qa_count": len(all_qa_pairs)},
            attributes={
                "markdown_path": processed_meta.get("markdown_path", ""),
                "source_type": "document_qa",
            },
        ).to_dict()
        with open(qa_json_path, 'w', encoding='utf-8') as f:
            json.dump(qa_body, f, indent=2, ensure_ascii=False)
        
        print(f"✓ QA Markdown 已保存: {qa_md_path}")
        print(f"✓ QA JSON 已保存: {qa_json_path}")
        
        return qa_md_path, qa_json_path, len(all_qa_pairs)
    
    def generate_metadata(self, md_path: Path) -> Path:
        """
        生成 metadata.json
        
        Args:
            md_path: 原始 .md 文件路径或 _qa.md 文件路径
        
        Returns:
            metadata.json 文件路径
        """
        # 获取文档名（去掉 _qa 后缀）
        doc_name = md_path.stem
        if doc_name.endswith('_qa'):
            doc_name = doc_name[:-3]
        
        print(f"\n{'='*80}")
        print(f"生成 metadata: {doc_name}")
        print(f"{'='*80}")
        
        metadata = {
            "metadataAttributes": {
                "product": doc_name,
                "image_prefix": f"images/{doc_name}/"
            }
        }
        
        # metadata 始终输出到 qa_pair 目录
        metadata_path = self.qa_pair_dir / f"{doc_name}_qa.md.metadata.json"
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Metadata 已保存: {metadata_path}")
        print(f"  - product: {doc_name}")
        print(f"  - image_prefix: images/{doc_name}/")
        
        return metadata_path
    
    def process_single_file(self, md_path: Path):
        """处理单个 Markdown 文件"""
        from datetime import datetime
        
        doc_name = md_path.stem
        file_start = datetime.now()
        
        print(f"\n{'#'*80}")
        print(f"# 处理文件: {doc_name}")
        print(f"# 开始: {file_start.strftime('%H:%M:%S')}")
        print(f"{'#'*80}")
        
        try:
            # 步骤 5: 提取 QA 对
            qa_md_path, qa_json_path, qa_count = self.extract_qa_from_markdown(md_path)
            
            # 步骤 6: 生成 metadata
            if qa_md_path:
                metadata_path = self.generate_metadata(qa_md_path)
            else:
                # 如果禁用了 QA 提取，基于原始文件生成 metadata
                metadata_path = self.generate_metadata(md_path)
            
            file_end = datetime.now()
            file_duration = file_end - file_start
            
            print(f"\n{'='*80}")
            print(f"✓ {doc_name} 处理完成！")
            if qa_count > 0:
                print(f"✓ 提取了 {qa_count} 个 QA 对")
            print(f"✓ 耗时: {file_duration}")
            print(f"{'='*80}")
            
        except Exception as e:
            print(f"\n✗ 处理 {doc_name} 时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def process_all_files(self):
        """处理所有 Markdown 文件"""
        from datetime import datetime
        
        start_time = datetime.now()
        print(f"\n开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"输入目录: {self.markdown_dir}")
        print(f"输出目录: {self.qa_pair_dir}")
        
        # 从 markdown 文件夹查找所有 .md 文件（排除 _qa.md、_processed 等中间文件）
        all_md = list(self.markdown_dir.glob("*.md"))
        md_files = [f for f in all_md if not f.stem.endswith("_qa") and "_processed" not in f.stem]
        
        if not md_files:
            print(f"✗ 在 {self.markdown_dir} 中没有找到 Markdown 文件")
            return
        
        print(f"\n找到 {len(md_files)} 个 Markdown 文件")
        for f in md_files:
            print(f"  - {f.name}")
        
        for i, md_file in enumerate(md_files, 1):
            print(f"\n\n{'*'*80}")
            print(f"* 进度: {i}/{len(md_files)}")
            print(f"{'*'*80}")
            
            self.process_single_file(md_file)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n\n{'#'*80}")
        print(f"# 全部完成！")
        print(f"# 共处理 {len(md_files)} 个 Markdown 文件")
        print(f"# 输入目录: {self.markdown_dir}")
        print(f"# 输出目录: {self.qa_pair_dir}")
        print(f"# 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"# 结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"# 总耗时: {duration}")
        print(f"{'#'*80}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='从 Markdown 文件提取 QA 对并生成 metadata',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 处理所有 markdown 文件（从 data_prepare/markdown 读取，输出到 qa_pair）
  python data_prepare/phase2_extract_qa_from_md.py
  
  # 只处理指定文件
  python data_prepare/phase2_extract_qa_from_md.py --file "HD480离线问题.md"
  
  # 禁用 QA 提取（只生成 metadata）
  python data_prepare/phase2_extract_qa_from_md.py --no-qa
        """
    )
    
    parser.add_argument(
        '--file',
        help='只处理指定的 Markdown 文件（从 data_prepare/markdown 下查找）'
    )
    
    parser.add_argument(
        '--no-qa',
        action='store_true',
        help='禁用 QA 提取（只生成 metadata）'
    )
    
    args = parser.parse_args()
    
    # 创建提取器
    extractor = QAExtractor(enable_qa_extraction=not args.no_qa)
    
    # 处理文件
    if args.file:
        data_prepare_dir = Path(__file__).resolve().parents[1]
        md_path = data_prepare_dir / "processed_data" / "markdown" / args.file.lstrip("/\\")
        if not md_path.exists():
            print(f"✗ 文件不存在: {md_path}")
            sys.exit(1)
        extractor.process_single_file(md_path)
        n_processed = 1
    else:
        extractor.process_all_files()
        n_processed = len(list(extractor.markdown_dir.glob("*.md"))) if getattr(extractor, "markdown_dir", None) else None

    try:
        from pipeline_run_logger import append_run_record
        append_run_record(
            step_id="phase2_qa_md",
            script="phase2_extract_qa_from_md.py",
            status="success",
            files_processed=n_processed if n_processed is not None else 0,
            detail={"no_qa": args.no_qa},
        )
    except Exception as e:
        print(f"[run_log] 写入运行记录失败: {e}")


if __name__ == "__main__":
    main()
