---
name: image-extraction
description: Extract text and knowledge from images, PDFs, screenshots, diagrams, and video frames for RAG. Combines OCR, vision analysis, and captioning. Use for any image-to-text or visual content processing. Triggers on "OCR", "image", "screenshot", "diagram", "PDF", "extract from image", "describe picture", "visual content", or video frame extraction.
bundle_scope: diagnosis-agent
risk_level: L1
---

# Purpose

Extract text and knowledge from visual content for RAG pipelines using OCR, vision analysis, and captioning.

# Trigger

**Use when:**
- User mentions "OCR", "extract text from image"
- User has "screenshots", "diagrams", "PDFs" to process
- User says "describe picture", "analyze image"
- User wants "visual content" converted to text
- User needs to extract "video frames"
- Processing ticket/document attachments that are images

**Do NOT use when:**
- User wants to generate images (use image generation tools)
- User is asking about image formats or compression
- User wants to edit or modify images
- Text content is already available (no extraction needed)

# Processing Types

## 1. Text-Heavy Content (OCR Primary)
**Use for**: scanned docs, PDFs, forms, receipts, text screenshots

```bash
tesseract image.png stdout -l eng+chi_sim
```

## 2. Diagrams & Flowcharts (Vision + OCR)
**Use for**: architecture diagrams, flowcharts, UML, sequence diagrams

Process:
1. OCR for text labels
2. Vision model for structure/relationships
3. Generate: description + extracted text + relationships

## 3. Screenshots (Vision + OCR)
**Use for**: UI screenshots, app interfaces, terminal output

Process:
1. OCR for visible text
2. Vision model for UI analysis
3. Generate: UI description + available actions + text

## 4. Photos (Vision Primary)
**Use for**: equipment photos, product images, scenes

Process:
1. Vision model for description
2. Technical details extraction
3. OCR for any visible text/labels

## 5. Video Frames
**Use for**: video attachments, recordings

Process:
1. Extract frames at intervals (e.g., every 5s)
2. Process each frame as image
3. Include timestamp in metadata

# Workflow

## Step 1: Detect Image Type

```python
IMAGE_TYPES = {
    'diagram': ['flowchart', 'architecture', 'sequence', 'uml'],
    'screenshot': ['ui', 'interface', 'app', 'terminal'],
    'document': ['text', 'table', 'form', 'pdf'],
    'photo': ['product', 'equipment', 'scene'],
    'chart': ['bar', 'line', 'pie', 'graph'],
}
```

## Step 2: Apply Appropriate Processor

1. PDFs → OCR with table detection
2. Images → Classify type → appropriate processor
3. Videos → Frame extraction → process frames
4. Low-confidence → Flag for human review

## Step 3: Output RAG Chunks

```json
{
    "chunk_id": "image:filename:hash",
    "source_type": "image_diagram|image_screenshot|...",
    "title": "Diagram: filename.png",
    "text": "Image type: diagram\n\nDescription: ...\n\nExtracted text: ...",
    "tags": {
        "rag_type": "curated",
        "image_type": "diagram",
        "has_ocr": true,
        "extraction_method": "vision_model+ocr"
    },
    "evidence": ["path/to/image.png"],
    "provenance": {
        "source_path": "...",
        "content_hash": "..."
    }
}
```

# Specialized Extraction

## Table Detection
For tables in images/PDFs:
1. Detect table boundaries
2. Extract row/column structure
3. Output as markdown table AND raw text

## Handwriting Recognition
For handwritten content:
1. Use handwriting-specific OCR
2. Include confidence scores
3. Flag low-confidence for review

# Tools & Dependencies

- Tesseract OCR: Text extraction
- Vision API (OpenAI/Claude): Image analysis
- OpenCV: Video frame extraction
- pdf2image: PDF processing

# Integration with Other Skills

- `ticket-log-join`: Process ticket attachments
- `feishu-doc-crawler`: Extract from Feishu screenshots
- `excel-to-rag`: OCR scanned spreadsheets

# Reporting

When done, report:
- Total images processed
- By type (diagram/screenshot/document/photo/chart)
- OCR success rate
- Vision analysis success rate
- Items flagged for review
- Output chunk count
