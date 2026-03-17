# Cursor Skills - EV Charger AI Team

Shared skills for AI-assisted development with Cursor IDE.

## Quick Install

```bash
git clone https://github.com/lowerbbq/ev-charger-skills.git
cd ev-charger-skills
./setup.sh
```

## Documentation

| Doc | Purpose |
|-----|---------|
| [Onboarding](docs/ONBOARDING.md) | New team member guide |
| [Contributing](docs/CONTRIBUTING.md) | How to create/update skills |

## What Are Skills?

Skills are knowledge packages that help Claude (in Cursor) understand our domain better:
- Project conventions and best practices
- Domain knowledge (FMEA, error codes, protocols)
- Workflow patterns

## Available Skills (17)

| Skill | Description |
|-------|-------------|
| `ev-charger-ai-agent` | **Start here** - Project overview |
| `cloud-ops-agent` | Ops platform integration |
| `edge-rag` | Edge device diagnosis |
| `cloud-rag-creation` | RAG system creation |
| `error-code-mapper` | **NEW** - Vendor code to KB mapping |
| `knowledge-relationship-mapping` | FMEA-ErrorCode linking |
| `log-signal-analysis` | Modem log interpretation |
| `ticket-triage` | Ticket priority & routing |
| `multi-source-rag-query` | Multi-RAG orchestration |
| `rag-case-cards` | Network issue case cards |
| `rule-engine` | Deterministic diagnosis |
| `edge-decision-tree` | Edge decision trees |
| `ev-charger-recovery` | Recovery procedures |
| `acmp-protocol` | ACMP communication protocol |
| `hallucination-detection` | AI response validation |
| `source-code` | Codebase analysis |
| `skill-creator` | Creating new skills |

## How to Use

Skills activate automatically in Cursor when you ask relevant questions:

```
"How does the RAG system work?"
→ Triggers cloud-rag-creation skill

"Help me understand error code 604B"
→ Triggers multi-source-rag-query skill
```

## Updating Skills

```bash
# Pull latest
cd ~/cursor-skills  # or wherever you cloned
git pull
./setup.sh
```

## Contributing

1. Edit skill in `~/.cursor/skills/`
2. Copy back: `cp -r ~/.cursor/skills/SKILL_NAME ./`
3. Commit and push
4. Notify team

## Questions?

Ask the AI in Cursor: "What skills are available for this project?"
