# Skill Registry

## Global Skills (~/.cursor/skills/)

| Skill | Domain | Created | Author | Projects |
|-------|--------|---------|--------|----------|
| ev-charger-knowledge | EV Charger | Feb 2024 | cloud-agent | All |
| ev-charger-troubleshoot | EV Charger | Feb 2024 | cloud-agent | All |
| log-analyzer | EV Charger | Feb 2024 | cloud-agent | All |
| diagnostic-log-parser | RAG/ETL | Feb 2024 | cloud-agent | All |
| case-search | EV Charger | Feb 2024 | cloud-agent | All |
| vehicle-compatibility-rag | EV Charger | Feb 2024 | cloud-agent | All |
| hardware-diagnostics | EV Charger | Feb 2024 | cloud-agent | All |
| agent-workflow | EV Charger | Feb 2024 | cloud-agent | All |
| failure-analytics | EV Charger | Feb 2024 | cloud-agent | All |
| installation-checklist | EV Charger | Feb 2024 | cloud-agent | All |
| preventive-maintenance | EV Charger | Feb 2024 | cloud-agent | All |
| extracting-excel-to-rag | RAG/ETL | Feb 2024 | cloud-agent | All |
| feishu-doc-crawler | RAG/ETL | Feb 2024 | cloud-agent | All |
| image-extraction | RAG/ETL | Feb 2024 | cloud-agent | All |
| ticket-log-join | RAG/ETL | Feb 2024 | cloud-agent | All |
| rag-chunk-deduplicator | RAG/ETL | Mar 2024 | cloud-agent | All |
| incremental-embeddings | RAG/ETL | Mar 2024 | cloud-agent | All |
| knowledge-package-exporter | RAG/ETL | Feb 2024 | cloud-agent | All |
| skill-creator | Meta | Mar 2024 | cloud-agent | All |
| web-ui-demo | UI/Demo | Mar 2024 | cloud-agent | All |
| evidence-fusion | EV Charger | Mar 2024 | cloud-agent | All |
| diagnosing-cellular-logs | EV Charger | Mar 2024 | cloud-agent | All |
| transforming-knowledge-packages | RAG/ETL | Mar 2024 | cloud-agent | All |

## Skill Categories

### EV Charger Domain (For cloud-agent project)
- ev-charger-knowledge
- ev-charger-troubleshoot
- log-analyzer
- case-search
- vehicle-compatibility-rag
- hardware-diagnostics
- agent-workflow
- failure-analytics
- installation-checklist
- preventive-maintenance
- evidence-fusion
- diagnosing-cellular-logs

### RAG/ETL Pipeline (General purpose)
- diagnostic-log-parser
- extracting-excel-to-rag
- feishu-doc-crawler
- image-extraction
- ticket-log-join
- rag-chunk-deduplicator
- incremental-embeddings
- knowledge-package-exporter
- transforming-knowledge-packages

### Meta/Tools
- skill-creator
- web-ui-demo

## Making Skills Project-Specific

To make a skill private to one project, move it:

```bash
# Move from global to project-specific
mv ~/.cursor/skills/my-skill /path/to/project/.cursor/skills/
```

## Recommended Structure

```
~/.cursor/skills/           # Shared utilities (RAG, ETL, meta)
project/.cursor/skills/     # Domain-specific skills
```
