---
name: feishu-doc-crawler
description: Extract structured content from Feishu wiki/docs pages for RAG pipelines. Use this skill when users mention Feishu, Lark, wiki crawling, document extraction, nested docs, multi-block layouts, or converting Feishu content into knowledge chunks. Trigger for "??", "Lark docs", "wiki pages", "linked documents", or any Feishu-related content extraction requests.
---

# Skill: Feishu Document Crawler

## Purpose
Extract content from Feishu wiki and document pages for RAG pipelines, handling:
- Authentication requirements
- Nested/linked documents
- Images and attachments
- Multi-block layouts (text, tables, code blocks)
- Excel spreadsheets with embedded links

## Prerequisites
- Chrome running with `--remote-debugging-port=9222`
- User logged into Feishu in Chrome
- MCP Chrome DevTools server available

## Workflow

### Step 1: Extract Links from Excel Files

```bash
# Run from your feishu-mcp project directory
cd <feishu-mcp-project>/

# Extract all links from Excel files
python3 scripts/extract_excel_links.py \
    --input "download/chrome-scan/**/*.xlsx" \
    --output "download/chrome-scan/extracted_links.json"
```

Output: `extracted_links.json` with all hyperlinks categorized by type:
- `feishu_wiki` - Wiki pages
- `feishu_doc` - Documents
- `feishu_sheet` - Spreadsheets
- `feishu_file` - File attachments

### Step 2: Generate Download Plan

```bash
python3 scripts/download_feishu_links.py \
    --links "download/chrome-scan/feishu_links.json" \
    --output-dir "download/chrome-scan/feishu_docs/" \
    --plan-only
```

Output: `download_plan.json` with URLs and commands for each document.

### Step 3: Download Documents via MCP

Use Chrome DevTools MCP to:

```python
# For each document in the plan:

# 1. Navigate to page
CallMcpTool(
    server="user-chrome-devtools",
    toolName="navigate_page",
    arguments={"type": "url", "url": doc_url, "timeout": 15000}
)

# 2. Take full-page screenshot
CallMcpTool(
    server="user-chrome-devtools", 
    toolName="take_screenshot",
    arguments={"fullPage": True, "filePath": f"screenshots/{doc_id}.png"}
)

# 3. Get text content via accessibility tree
CallMcpTool(
    server="user-chrome-devtools",
    toolName="take_snapshot", 
    arguments={"filePath": f"snapshots/{doc_id}.txt"}
)
```

### Step 4: Export Documents (Optional)

For documents that support export:

1. Click the "..." menu in the document
2. Select "Export" > "Download as .docx" or ".xlsx"
3. Files save to Chrome's download folder

## Output Structure

```
feishu_docs/
??? screenshots/          # Full-page PNG screenshots
??  ??? 000_FAQ.png
??  ??? 001_Installation_Guide.png
??  ??? ...
??? snapshots/            # Text content from a11y tree
??  ??? 000_FAQ.txt
??  ??? 001_Installation_Guide.txt
??  ??? ...
??? exports/              # Downloaded DOCX/XLSX files
??  ??? ...
??? download_plan.json    # Processing metadata
```

## Processing Snapshots for RAG

The snapshot files contain structured text from the accessibility tree. Process them:

```python
def process_snapshot_for_rag(snapshot_path: str) -> dict:
    """Convert snapshot to RAG chunk."""
    with open(snapshot_path, 'r') as f:
        content = f.read()
    
    # Extract title from first heading
    title_match = re.search(r'heading.*?"([^"]+)"', content)
    title = title_match.group(1) if title_match else Path(snapshot_path).stem
    
    # Extract main text content
    text_parts = []
    for line in content.split('\n'):
        if 'StaticText' in line or 'paragraph' in line:
            text_match = re.search(r'"([^"]+)"', line)
            if text_match:
                text_parts.append(text_match.group(1))
    
    text = ' '.join(text_parts)
    
    return {
        'chunk_id': f"feishu:{Path(snapshot_path).stem}",
        'source_system': 'feishu_wiki',
        'source_type': 'wiki_doc',
        'title': title,
        'text': text,
        'language': detect_language(text),
        'tags': {
            'rag_type': 'curated',
            'source': 'feishu'
        }
    }
```

## Handling Images

Screenshots contain visual content. Use the `image-extraction` skill to:
1. OCR text from images
2. Describe diagrams and flowcharts
3. Extract table data from screenshots

```python
# Cross-reference with image-extraction skill
from image_extraction import process_image

for screenshot in screenshots_dir.glob('*.png'):
    image_chunks = process_image(screenshot)
    # Merge with text chunks
```

## Link Types Reference

| Type | Pattern | Example |
|------|---------|---------|
| Wiki | `feishu.cn/wiki/XXX` | Documentation pages |
| Doc | `feishu.cn/docx/XXX` | Rich text documents |
| Sheet | `feishu.cn/sheets/XXX` | Spreadsheets |
| File | `feishu.cn/file/XXX` | Uploaded files |

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| `extracting-excel-to-rag` | Process downloaded XLSX exports |
| `image-extraction` | OCR screenshots for visual content |
| `diagnostic-log-parser` | Parse log files from attachments |

## Files Created

| File | Purpose |
|------|---------|
| `scripts/extract_excel_links.py` | Extract hyperlinks from Excel |
| `scripts/download_feishu_links.py` | Generate download plan |
| `scripts/batch_download_feishu.py` | Batch processing helper |

## Troubleshooting

### Chrome Connection Issues

**macOS:**
```bash
pkill -f "Google Chrome"
sleep 2
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
    --remote-debugging-port=9222 \
    --user-data-dir="/tmp/chrome-debug-profile" &
```

**Windows (PowerShell):**
```powershell
Stop-Process -Name chrome -ErrorAction SilentlyContinue
Start-Sleep 2
Start-Process "chrome" "--remote-debugging-port=9222 --user-data-dir=$env:TEMP\chrome-debug"
```

### Login Required
If page shows login screen:
1. Screenshot shows login page
2. User must manually log in via Chrome
3. Resume crawling after authentication

### Rate Limiting
If Feishu rate-limits requests:
1. Add delay between requests (5-10 seconds)
2. Process in smaller batches
3. Spread across multiple sessions

## Example Usage

```bash
# Full pipeline ? run from your feishu-mcp project directory
cd <feishu-mcp-project>/

# 1. Extract links
python3 scripts/extract_excel_links.py \
    --input "download/**/*.xlsx" \
    --output "download/extracted_links.json"

# 2. Generate plan
python3 scripts/download_feishu_links.py \
    --links "download/feishu_links.json" \
    --output-dir "download/feishu_docs/"

# 3. Use MCP to download (in Cursor)
# Navigate, screenshot, snapshot for each URL

# 4. Process for RAG
python3 scripts/process_feishu_snapshots.py \
    --input "download/feishu_docs/snapshots/" \
    --output "rag_data/feishu_docs.jsonl"
```
