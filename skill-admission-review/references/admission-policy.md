# Admission Policy

Policy rules applied by `admission_gate.py` for each of the five checks.

---

## Check 1: Global Conflict

| Condition | Decision |
|-----------|----------|
| Exact name match in registry | REJECT |
| Name edit-distance ≤ 2 from existing skill | WARNING |
| Description Jaccard similarity > 0.65 with existing skill | REQUIRES_REVIEW |
| Description Jaccard similarity 0.45–0.65 with existing skill | WARNING |

**Purpose**: Prevent registry pollution from duplicate or near-duplicate skills.

---

## Check 2: Agent Boundary

| Condition | Decision |
|-----------|----------|
| Missing `bundle_scope` | REJECT |
| `bundle_scope` not in approved list | REJECT |
| Text contains vocabulary from ≥ 2 other agent domains | REQUIRES_REVIEW |
| Text contains vocabulary from 1 other agent domain | WARNING |

**Approved bundle_scope values**:
- `diagnosis-agent` — fault diagnosis, hardware, log analysis
- `customer-agent` — customer queries, billing, vehicle compatibility
- `ops-agent` — fleet management, knowledge, RAG pipelines
- `energy-agent` — energy consumption, grid optimization
- `bpmn-agent` — business process, BPMN conversion
- `platform` — meta-skills, governance tools

---

## Check 3: Risk Level Accuracy

| Condition | Decision |
|-----------|----------|
| Device control vocabulary detected + risk_level < L4 | REJECT |
| L4 without `verify-gate-mcp:request_approval` step | REJECT |
| Write-operation vocabulary + risk_level < L3 | REQUIRES_REVIEW |
| Declared L4 but no control vocabulary found | WARNING |

**Risk level taxonomy**:
- `L1` — Read-only operations, no side effects
- `L2` — Analysis and computation, no external writes
- `L3` — Creates/modifies records (work orders, notifications, knowledge)
- `L4` — Direct device control (restart, stop, disable, set limits)

---

## Check 4: Routing Governance

| Condition | Decision |
|-----------|----------|
| Description length < 40 characters | WARNING |
| Missing "Use when" clause | WARNING |
| Description contains vague routing words | WARNING |
| Description has ≥ 2 overly-broad signals ("all", "any", "always") | REQUIRES_REVIEW |

**Purpose**: Ensures the description can be used reliably by the skill router
without causing false positives or missing triggers.

---

## Check 5: Form Factor

| Condition | Decision |
|-----------|----------|
| Skill references/calls another skill | REJECT |
| ≤ 2 workflow steps AND no error handling | WARNING |
| Description uses conjunction overload | REQUIRES_REVIEW |

**Form factor guidance**:
- If a task is a single atomic function call → register as MCP Tool, not a Skill
- If a task orchestrates multiple other skills → move to Agent/Workflow layer
- If a task mixes two distinct responsibilities → split into two skills

---

## Decision Aggregation

The overall decision is the highest severity across all five checks:

```
PASS < WARNING < REQUIRES_REVIEW < REJECT
```

Mapped to output decisions:
- `PASS` → `PASS`
- `WARNING` → `PASS_WITH_WARNINGS`
- `REQUIRES_REVIEW` → `REQUIRES_REVIEW`
- `REJECT` → `REJECT`

---

## Registry Status Mapping

| Admission Decision | Registry Status |
|-------------------|-----------------|
| PASS | approved |
| PASS_WITH_WARNINGS | approved (with governance note) |
| REQUIRES_REVIEW | submitted (pending manual review) |
| REJECT | needs_revision |
