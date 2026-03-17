---
name: evidence-fusion
description: Combine evidence from multiple sources into diagnostic results. Use for root cause analysis, action recommendation, ticket generation. Triggers on "fuse evidence", "combine results", "root cause analysis", "generate diagnosis", "create ticket from evidence", or when you have retrieval results that need analysis.
---

# Skill: Evidence Fusion

Combine evidence from retrieval into actionable diagnosis with root causes, actions, and tickets.

## When to Use

| Scenario | Use This Skill |
|----------|----------------|
| Have retrieval results, need diagnosis | YES |
| Need root cause analysis | YES |
| Auto-generate support ticket | YES |
| Just searching for information | NO - use retrieval |
| Need step-by-step troubleshooting | NO - use `ev-charger-troubleshoot` |

## Quick Start

```python
from src.fusion import EvidenceFuser
from src.retrieval import RetrievalRouter, RetrievalExecutor

# Pipeline: Retrieve → Fuse
router = RetrievalRouter()
executor = RetrievalExecutor()
fuser = EvidenceFuser()

plan = router.route("Error 0x3001 on BMW iX")
retrieval = executor.execute(plan)
fusion = fuser.fuse(retrieval)

# Results
print(fusion.problem_summary)
print(fusion.primary_root_cause)
print(fusion.is_remote_fixable())
```

## Output Structure

```python
FusionResult:
├── problem_summary: str          # Brief problem description
├── problem_category: enum        # hardware|software|firmware|...
├── root_cause_candidates: list   # Ranked by confidence
│   └── RootCauseCandidate:
│       ├── cause_summary: str
│       ├── confidence: float     # 0.0-1.0
│       ├── supporting_evidence: list[str]
│       └── related_error_codes: list[str]
├── recommended_actions: list     # Prioritized
│   └── RecommendedAction:
│       ├── action_summary: str
│       ├── action_type: enum     # remote_fix|hardware_check|...
│       ├── priority: enum        # immediate|high|medium|low
│       └── requires_onsite: bool
├── ticket_payload: TicketPayload # For JIRA/ticket system
└── missing_information: list     # What we couldn't determine
```

## Confidence Levels

| Level | Score | Meaning |
|-------|-------|---------|
| HIGH | ≥80% | Strong evidence, can act |
| MEDIUM | 50-80% | Partial evidence, verify |
| LOW | <50% | Weak evidence, investigate |

## Action Priorities

| Priority | When |
|----------|------|
| IMMEDIATE | Safety issue, charger down |
| HIGH | Functional issue, do today |
| MEDIUM | Minor issue, this week |
| LOW | Can wait |

## Key Methods

```python
# Check if remotely fixable
fusion.is_remote_fixable()  # True if no onsite needed

# Check if needs site visit
fusion.requires_onsite()

# Get primary action
fusion.get_primary_action()

# Get JIRA fields
fusion.ticket_payload.to_jira_fields()
```

## Configuration

```python
from src.fusion import FusionConfig

config = FusionConfig(
    use_llm_fusion=True,      # Enable LLM analysis
    max_root_causes=3,        # Limit output
    generate_ticket=True,     # Auto-generate ticket
)
```

## Related Skills

| Need | Skill |
|------|-------|
| Search for evidence | `case-search`, `log-analyzer` |
| Step-by-step diagnosis | `ev-charger-troubleshoot` |
| Vehicle-specific | `vehicle-compatibility-rag` |
| Hardware issues | `hardware-diagnostics` |

## Reference Files

| File | Contents |
|------|----------|
| `reference.md` | Full API, enums, code examples |
| `docs/17_evidence_fusion.md` | Architecture documentation |
