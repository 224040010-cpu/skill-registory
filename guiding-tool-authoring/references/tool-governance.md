# Tool Governance Reference

Rules and policies for the platform tool lifecycle. All tools registered in
`tool-registry.yaml` and `mcp-tool-catalog.md` must comply with these rules.

---

## 1. Risk Level Matrix

| Level | `side_effects` | `idempotent` | Requires approval | Examples |
|---|---|---|---|---|
| **L0** | `none` | `true` | No | XML serializer, JSON formatter, math calculator |
| **L1** | `read` | `true` | No | DB query, cache read, vector search |
| **L2** | `read` | `true` or `false` | No | LLM inference, complex analysis |
| **L3** | `write` | Either | Yes (for new tools) | Create record, send notification, update status |
| **L4** | `external` | `false` | Yes (every call) | Device command, payment, OTA push |

**Consistency rules (enforced by `validate_tool.py`):**
- `L0` → `side_effects` MUST be `none`
- `L1` → `side_effects` MUST be `read`
- `L3/L4` → `side_effects` MUST be `write` or `external`
- `side_effects: write` or `external` → `risk_level` MUST be ≥ L3
- `side_effects: external` → `requires_approval: true` MUST be set

---

## 2. Naming Rules

| Rule | Correct | Incorrect |
|---|---|---|
| `kebab-case` only | `parse-business-intent` | `ParseBusinessIntent`, `parse_intent` |
| `verb-noun` pattern | `extract-entities`, `validate-bpmn-xml` | `entity-extractor`, `bpmn-checker` |
| No generic single-word names | `serialize-bpmn-model` | `serializer`, `parser` |
| No domain prefix repetition | `parse-business-intent` | `bpmn-parse-business-intent` |
| Max 48 characters | `classify-bpmn-task-subtype` | ✅ (27 chars) |

**Anti-patterns to reject:**
- Names ending in `-er`, `-or`, `-tor` (e.g., `processor`, `resolver`) → too vague
- Names starting with `get-`, `do-`, `run-` (e.g., `get-data`, `do-analysis`) → not descriptive
- Names that duplicate an existing tool with only a minor qualifier difference

---

## 3. Schema Requirements

### Input schema
- MUST be `type: object`
- `properties` MUST be non-empty
- Every property MUST have `type` and `description`
- `required` list MUST be present even if empty `[]`
- Use `enum` for parameters with fixed value sets
- Avoid `type: any` — use `oneOf` or `union` types if needed

### Output schema
- MUST be `type: object`
- `properties` MUST be non-empty
- Every property MUST have `type` and `description`
- If the output is a list, use `type: array` with `items` schema defined
- Null responses are not allowed — always return a structured object

### Error contract
- Minimum **2 error codes** (input validation failure + system failure)
- `code` MUST be `UPPER_SNAKE_CASE`
- `message` MUST be human-readable (not a stack trace)
- `retryable: false` for input/validation errors
- `retryable: true` for transient failures (network, timeout, service unavailable)

---

## 4. Idempotency Rules

A tool is idempotent if calling it multiple times with the same input always
produces the same output and has no cumulative side effects.

| Scenario | idempotent |
|---|---|
| Serializer / formatter | `true` |
| DB query by unique key | `true` |
| LLM inference call | `false` (non-deterministic) |
| Create record | `false` (creates duplicates) |
| Upsert record by unique ID | `true` |
| Send notification | `false` |

**Rule:** If `idempotent: true` is claimed but `side_effects: write`, the
validator will warn unless the write is an `upsert` operation (noted in
`implementation.notes`).

---

## 5. Tool Admission Gate Checklist

Run before merging any new TOOL.md to `main`:

**Schema integrity**
- [ ] All required fields present in TOOL.md
- [ ] Input schema: all properties have `type` + `description`
- [ ] Output schema: all properties have `type` + `description`
- [ ] At least 2 error codes with `retryable` flag

**Risk consistency**
- [ ] `risk_level` consistent with `side_effects` (see matrix above)
- [ ] `idempotent` consistent with `side_effects`
- [ ] L3/L4 tools have `requires_approval: true`

**Duplicate detection**
- [ ] `tool_name` not already in `tool-registry.yaml`
- [ ] No existing tool with >70% description overlap (semantic duplicate)
- [ ] No existing tool that subsumes this tool's functionality

**Reusability signal**
- [ ] `called_by_skills` lists ≥ 1 skill (or has a pending skill that will call it)
- [ ] Tool is not a one-time-use implementation detail (can be used by ≥ 2 skills)

---

## 6. Tool Lifecycle

```
draft ──► submitted ──► approved ──► deprecated ──► retired
                  ↑              ↑
           (validate_tool.py  (engineering
            passes ≥ 40/50)    review)
```

| Status | Meaning | Callable by skills? |
|---|---|---|
| `draft` | In authoring | No |
| `submitted` | Awaiting engineering review | No |
| `approved` | Registered in MCP catalog | Yes |
| `deprecated` | Still callable, replacement exists | Yes (with warning) |
| `retired` | Removed from MCP catalog | No |

---

## 7. What Disqualifies a Capability from Being a Tool

If any of these apply, the capability is NOT a tool:

| Disqualifier | What it is instead |
|---|---|
| Has a user-facing trigger sentence | Skill |
| Requires multi-step reasoning or conditional branching | Skill |
| Calls other tools in sequence (orchestration) | Skill or Workflow |
| Output depends on conversation history | Skill |
| Never reused by more than one skill | Inline logic in the skill's workflow |
| Requires human approval at every invocation | L4 tool (add `requires_approval: true`) |

---

## 8. Tool Categories: Decision Guide

| If the tool... | Category |
|---|---|
| Converts unstructured text → structured data | `parsing` |
| Converts one structured format → another structured format | `transformation` |
| Checks validity/correctness of a data structure | `validation` |
| Reads from a database, API, index, or external service | `retrieval` |
| Creates, updates, or deletes data in a system | `execution` |
| Performs algorithmic calculation with no I/O | `computation` |
