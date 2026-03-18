# Tool Admission Policy

> **Phase 4T** — platform-side gate for MCP Tool registration.
> This policy answers: **"Should this tool exist as a platform asset?"**
> `validate_tool.py` (Phase 2T) already answered: "Is this tool spec well-formed?"

---

## Why Tool Admission Matters

Skills have two quality layers:
1. **Authoring Gate** (Phase 2S) — is the skill well-written?
2. **Admission Gate** (Phase 4) — should the skill be in the platform?

Tools currently only have Phase 2T. Without an admission gate, the system
trades **skill explosion** for **tool explosion**:

- Duplicate tools with different names
- Tools that should be workflow_steps inside a skill
- Tools with no real consumers (premature abstraction)
- Risk levels that understate actual side effects
- Fragmented MCP services with 1-2 tools each

---

## The Five Admission Checks

### Check 1 — Global Duplication

**Question**: Is there already a tool that does this?

| Finding | Decision |
|---------|---------|
| Exact name match | REJECT — use existing tool |
| Name edit distance ≤ 2 | REJECT — near-identical name |
| Name edit distance 3–4 | WARNING — verify distinctness |
| Description Jaccard ≥ 65% | REQUIRES_REVIEW — possible duplicate function |
| Input schema field overlap ≥ 70% | REQUIRES_REVIEW — possible duplicate interface |

**Why it matters**: Tool naming collisions cause routing ambiguity in MCP servers.
Functionally identical tools fragment implementation and testing effort.

---

### Check 2 — Service Assignment

**Question**: Does this tool belong to the right MCP service?

| Finding | Decision |
|---------|---------|
| `service` field missing | REJECT |
| Service not in registered platform services | WARNING — register service first |
| Would be the only tool in a new service | WARNING — plan ≥ 3 tools before creating a new service |
| Similar tools exist in a different service | REQUIRES_REVIEW — verify correct service home |

**Principle**: MCP services represent logical capability domains. A single-tool
service creates unnecessary infrastructure overhead and signals unclear
domain boundaries.

**Registered platform services** (as of 2026-03-17):

| Service | Domain | Typical tool count |
|---------|--------|-------------------|
| `bpmn-tools` | BPMN process modeling | 15 |
| `diagnosis-tools` | Charger fault diagnosis | TBD |
| `customer-tools` | Customer account/billing | TBD |
| `ops-tools` | Fleet operations | TBD |
| `energy-tools` | Energy management | TBD |

---

### Check 3 — Risk Consistency

**Question**: Does the declared risk correctly reflect the tool's actual behavior?

The platform enforces a strict risk matrix:

| Level | side_effects | idempotent | requires_approval | Typical use |
|-------|-------------|-----------|------------------|-------------|
| L0 | none | **true** (required) | false | Pure computation, serialization, math |
| L1 | read | true (expected) | false | DB queries, status reads, index lookup |
| L2 | read | may vary | false | LLM inference, non-deterministic analysis |
| L3 | write | must declare | **recommended** | Create/update records, send notifications |
| L4 | external | must declare | **true** (required) | Device commands, payments, OTA push |

**Common misclassification patterns**:

- `L0` + `side_effects: read` → REJECT (L0 is pure, no I/O)
- `L1` + `side_effects: write` → REJECT (L1 is read-only)
- `L4` + `requires_approval: false` → REJECT (L4 always needs approval)
- `L3` + no `idempotent` declaration → WARNING (retryability is ambiguous)

---

### Check 4 — Reuse Justifiability

**Question**: Is this tool actually reusable, or is it a workflow_step that escaped?

| `called_by_skills` | Decision |
|--------------------|---------|
| Empty or missing | REJECT — no consumer = premature abstraction |
| Exactly 1 skill | WARNING — single-consumer tool may be a workflow_step |
| ≥ 2 skills | PASS |

**Decision guide for single-consumer tools**:

```
Is this tool likely to be reused by other skills within 1 release cycle?
├── YES → Keep as tool, annotate TOOL.md with planned future consumers
└── NO  → Consider downgrading to workflow_step inside the consuming skill
          Upgrade criteria: see asset-promotion-rules.md
```

**Why zero consumers = REJECT**:
A tool registered with no consumers is a maintenance liability. It will
never receive usage-driven validation, never be tested in integration,
and will drift out of sync with the rest of the platform.

---

### Check 5 — Form Appropriateness

**Question**: Should this be a tool, or is it actually a skill or workflow_step?

**Signals that it should NOT be a tool**:

| Signal | Implication | Decision |
|--------|------------|---------|
| Name ends in `manager`, `handler`, `coordinator`, `orchestrator` | Coordinating role, not atomic | REJECT |
| Description contains `orchestrate`, `manage`, `pipeline`, `workflow` | Multi-step logic | REQUIRES_REVIEW |
| Description has sequential step language (`first...then...finally`) | Should be a skill | REQUIRES_REVIEW |
| Both orchestration + `execution` category | Very likely a skill | REQUIRES_REVIEW |
| Description > 250 characters | Too complex to be atomic | WARNING |

**Quick atomicity test** (all must be YES to be a valid tool):

```
[ ] Single, clearly-named input object → single, clearly-named output object?
[ ] No conditional branching described in the tool's own description?
[ ] No references to "calling other tools" in description?
[ ] Callable as a standalone function without context accumulation?
[ ] Deterministic for the same input (or explicitly marked non-deterministic at L2)?
```

---

## Admission Decisions

| Decision | Meaning | Registry action |
|----------|---------|----------------|
| `PASS` | Tool is ready to enter registry | Set `status: approved` |
| `PASS_WITH_WARNINGS` | Tool can enter, warnings noted | Set `status: approved`, track warnings |
| `REQUIRES_REVIEW` | Human review needed before admission | Set `status: needs_revision` |
| `REJECT` | Tool must not enter registry yet | Keep `status: draft`, return findings |

---

## Relationship to Asset Promotion Rules

The admission gate interacts with the asset lifecycle:

- A **workflow_step** that passes all 5 checks can be promoted to a **tool**
  (see `capability-planning/references/asset-promotion-rules.md`)
- A **tool** that fails Check 4 (single consumer) may be demoted to a
  **workflow_step** inside the consuming skill
- A **tool** that fails Check 5 (orchestration language) may be upgraded to
  a **skill** via a new guiding-skill-authoring session

The admission gate does not automatically trigger promotions or demotions —
it flags them for human decision.
