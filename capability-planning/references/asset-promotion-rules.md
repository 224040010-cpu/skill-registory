# Asset Promotion Rules

> This document defines the formal conditions under which a capability asset
> changes its type: `workflow_step ↔ tool ↔ skill`.
>
> These rules are applied by `capability-planning` (Phase 0) during initial
> classification, and re-applied at any time when an existing asset's
> classification is questioned.

---

## The Three-Layer Model

```
Layer 1 — Capability Layer (enters registry)
┌─────────────────────────────────┐
│  TOOL                           │  → tool-registry.yaml
│  Single atomic operation        │  → MCP server endpoint
│  Fixed I/O, no business logic   │
└─────────────────────────────────┘
┌─────────────────────────────────┐
│  SKILL                          │  → skill-registry.yaml
│  Complete user intent           │  → Agent Router
│  Multi-step, independently      │
│  governable                     │
└─────────────────────────────────┘

Layer 2 — Implementation Layer (does not enter registry)
┌─────────────────────────────────┐
│  workflow_step                  │  → parent SKILL's composition_notes
│  Embedded step inside a skill   │  → no independent registration
│  Not independently triggerable  │
└─────────────────────────────────┘
```

---

## Rule 1 — workflow_step → tool (Promotion)

**Trigger**: A step inside a skill is found to be genuinely atomic and reusable.

### Required conditions (all must be true)

| # | Condition |
|---|-----------|
| 1 | Single, deterministic input → single, deterministic output |
| 2 | No conditional branching or multi-step logic inside the operation |
| 3 | No or minimal business logic (data processing, I/O, or computation only) |
| 4 | Has a stable, well-defined schema that is unlikely to change frequently |
| 5 | Used or planned to be used by **≥ 2** skills or agents |

### Process

1. Author writes a `TOOL.md` spec.
2. Run `validate_tool.py` (Phase 2T). Score must be ≥ 45.
3. Run `admission_gate_tool.py` (Phase 4T). Must not REJECT.
4. Add to `tool-registry.yaml` with `status: approved`.
5. Add to `mcp-tool-catalog.md` under the appropriate service.
6. Remove from parent skill's `composition_notes`.
7. Update parent skill's workflow to use `service:tool_name()` format.

### Example

```
workflow_step: "normalise-alarm-codes"
  belongs_to_skill: diagnose-charger-failure
  
  After 6 months, also needed by:
  - generating-maintenance-report
  - handling-payment-failure

→ Meets conditions 1-5 → PROMOTE to tool
→ tool_name: normalise-alarm-codes
→ service: diagnosis-tools
→ category: transformation
→ risk_level: L0
```

---

## Rule 2 — workflow_step → skill (Promotion)

**Trigger**: A step becomes complex enough and independent enough to warrant
full lifecycle governance.

### Required conditions (any 2 of 6)

| # | Condition |
|---|-----------|
| 1 | Reused across **≥ 2 independent skills or agents** |
| 2 | Has a clearly stable, well-defined input/output interface |
| 3 | Contains stable multi-step logic that is tested independently |
| 4 | Needs an **independent owner** or separate release cycle |
| 5 | Needs **independent versioning** (breaking changes must not ripple) |
| 6 | Business stakeholders need to **trigger or reference it directly** |

### Process

1. Treat the step as a new capability.
2. Run a fresh `capability-planning` session for it alone (confirm it
   classifies as `skill`, not `tool`).
3. Route to `guiding-skill-authoring` for a full SKILL.md.
4. Run `validate_skill.py` (Phase 2S). Score must be ≥ 60.
5. Run `admission_gate.py` (Phase 4). Must PASS or PASS_WITH_WARNINGS.
6. Add to `skill-registry.yaml` with `status: draft → submitted → approved`.
7. Remove from parent skill's `composition_notes`.
8. Update parent skill's workflow to call the new skill by name.

### Example

```
workflow_step: "generate-diagnosis-summary"
  belongs_to_skill: diagnose-charger-failure

  After 3 months:
  - generating-maintenance-report also needs it  (condition 1)
  - it needs independent versioning (condition 5)
  - business team wants to trigger it directly (condition 6)

→ Meets conditions 1, 5, 6 (3 of 6) → PROMOTE to skill
→ skill_name: generating-diagnosis-summary
→ bundle_scope: diagnosis-agent
→ risk_level: L2
```

---

## Rule 3 — tool → skill (Promotion)

**Trigger**: A tool starts accumulating business logic, multi-step handling,
or user-facing orchestration that goes beyond atomic operation.

### Required conditions (any 3 of 5)

| # | Condition |
|---|-----------|
| 1 | The tool now requires **conditional branching** inside its own logic |
| 2 | It is being triggered **directly by user intent**, not just called by a skill |
| 3 | It has **error handling paths** that require judgment, not just retryable flags |
| 4 | It calls or coordinates other tools internally |
| 5 | It has grown to require **context accumulation** across multiple inputs |

### Warning signs in existing TOOL.md

- `description` contains: "first checks...", "if X then Y", "orchestrates"
- `errors[]` has > 4 entries with complex recovery descriptions
- `usage.when_to_use` sounds like a user intent trigger, not a programmatic call

### Process

1. Deprecate the existing `tool-registry.yaml` entry (`status: deprecated`).
2. Run `capability-planning` for the expanded capability (confirm `skill`).
3. Route to `guiding-skill-authoring`.
4. The old tool endpoint can remain as a thin MCP wrapper while the skill
   takes over the orchestration layer. Eventually retire the tool.

### Example

```
tool: parse-business-intent (L1, parsing)

After iteration:
- Now checks for ambiguous input and requests clarification  (condition 3)
- Coordinates extract-process-entities internally  (condition 4)
- Users sometimes trigger it directly via a command  (condition 2)

→ Meets conditions 2, 3, 4 (3 of 5) → PROMOTE to skill
→ skill_name: interpreting-business-intent
→ The raw parsing API remains as tool: parse-business-intent (L1)
→ The skill orchestrates it with disambiguation logic on top
```

---

## Rule 4 — skill → tool (Demotion)

**Trigger**: A skill is found to be doing a single transformation with no
real business logic — it should never have been a skill.

### Required conditions (all must be true)

| # | Condition |
|---|-----------|
| 1 | The skill has only **1 workflow step** (or effectively 1 operation) |
| 2 | **No conditional branching** — same output structure for all inputs |
| 3 | **Not independently user-triggered** — only called by other skills |
| 4 | No unique business error handling beyond "retry on failure" |
| 5 | Reusable as a direct API call with fixed schema |

### Warning signs in existing SKILL.md

- Workflow section has only 1 `[ ] Step` with no branching
- Trigger section has no user-facing trigger phrases
- No `Constraints` section (nothing complex to constrain)
- `validate_skill.py` score consistently < 50 across all dimensions

### Process

1. Write a `TOOL.md` for the equivalent capability.
2. Run `validate_tool.py` (Phase 2T). Score must be ≥ 45.
3. Run `admission_gate_tool.py` (Phase 4T). Must PASS.
4. Add to `tool-registry.yaml`.
5. Set skill's `status: deprecated` in `skill-registry.yaml`.
6. Update all skills that called this skill to use the tool directly
   via `service:tool_name()` format.

### Example

```
skill: normalising-bpmn-xml (L0, bpmn-agent)
  workflow:
  - [ ] Step 1: Call xml-formatter library → return formatted XML

→ Meets all 5 conditions → DEMOTE to tool
→ Deprecate skill entry
→ tool_name: normalise-bpmn-xml
→ service: bpmn-tools
→ category: transformation
→ risk_level: L0
```

---

## Rule 5 — tool → workflow_step (Demotion)

**Trigger**: A tool has no consumers and is unlikely to gain them — it was
a premature abstraction.

### Required conditions (any 2 of 3)

| # | Condition |
|---|-----------|
| 1 | `called_by_skills` has been empty for ≥ 1 release cycle |
| 2 | The tool's only plausible consumer is a single skill |
| 3 | The tool's logic is tightly coupled to one skill's context |

### Process

1. Remove from `tool-registry.yaml` (or set `status: retired`).
2. Remove from `mcp-tool-catalog.md`.
3. Add the logic as a `composition_notes` entry in the parent skill.
4. Update `capability-planning` reference docs if this was used as a
   canonical example.

---

## Summary Matrix

| From | To | Trigger | Key condition |
|------|----|---------|--------------|
| workflow_step | tool | Found to be atomic + reusable | ≥ 2 skill consumers |
| workflow_step | skill | Becomes complex + independent | Any 2 of 6 governance criteria |
| tool | skill | Accumulates business logic | Any 3 of 5 orchestration signals |
| skill | tool | Found to be single-step + non-user-triggered | All 5 atomicity conditions |
| tool | workflow_step | No consumers, tightly coupled | Any 2 of 3 coupling conditions |

---

## Governance Cadence

These rules should be applied:

1. **At authoring time**: `capability-planning` Phase 0 classification
2. **At admission time**: `admission_gate_tool.py` Check 4 and Check 5
3. **At governance review**: `governance_audit.py` quarterly scan should flag
   candidates for promotion/demotion based on `called_by_skills` drift and
   skill complexity changes
4. **At bundle submission**: reviewer checks `capability_plan.json` to ensure
   the author applied the decision tree correctly
