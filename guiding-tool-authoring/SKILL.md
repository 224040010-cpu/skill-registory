---
name: guiding-tool-authoring
meta_skill: true
bundle_scope: platform
risk_level: L2
description: |
  Guides authors through the full lifecycle of defining, validating, and registering
  an atomic MCP Tool for the platform. Use when a capability has been classified
  as type "tool" by capability-planning, when a skill's workflow references a
  tool that does not yet exist in the MCP catalog, or when an engineer wants to
  formalize an existing implementation into a platform-registered TOOL.md spec.
  Trigger on: "我要写一个tool", "帮我定义这个工具的接口", "这个能力应该是tool",
  "注册一个MCP tool", "tool spec", "定义tool的入参出参".
  Do NOT use when the capability requires multi-step reasoning or has an independent
  user trigger — use guiding-skill-authoring instead.
  Do NOT use when the capability is a workflow orchestration step — it belongs
  at the agent workflow layer, not as a registered tool.
---

# Purpose

This skill is the authoritative guide for creating production-ready **Tool specs**
on the platform. A Tool is different from a Skill in three fundamental ways:

| Dimension | Tool | Skill |
|---|---|---|
| **Triggering** | Called programmatically by a skill | Triggered by user intent |
| **Steps** | Single atomic operation | Multi-step workflow |
| **Interface** | Strict typed schema | Natural language + structured output |
| **Lifecycle** | Registered in `tool-registry.yaml` + MCP catalog | Registered in `skill-registry.yaml` |

**Output**: a `TOOL.md` file that is the contract between the skill layer and
the implementation layer. Engineers implement against this spec; skills reference
it by `server:tool_name()` format.

---

# Trigger

**Use this Skill when:**
- `capability-planning` has classified a capability as `final_type: "tool"`
- A skill draft references `⚠️ Tool needed: [description]`
- An engineer wants to register an existing backend function as a platform tool
- Reviewing a tool spec draft before submission

**Do NOT use this Skill when:**
- The capability has a user-facing trigger → use `guiding-skill-authoring`
- The capability is multi-step → re-run `capability-planning` first
- The capability is a one-off script, not intended for reuse

---

# Pre-Flight: Is This Actually a Tool?

Before proceeding, apply the mandatory rejection test.

**REJECT** if ANY of the following is true:

```
[ ] The capability requires multi-step reasoning or conditional branching
    → "decide X, then do Y, then check Z" = SKILL, not tool

[ ] The capability has a natural language trigger from a user
    → "帮我分析..." "生成..." = SKILL, not tool

[ ] The capability orchestrates other tools or skills
    → orchestration = SKILL or WORKFLOW, not tool

[ ] The capability's output depends on conversation context across turns
    → stateful reasoning = SKILL, not tool
```

If any box is checked, return:
```json
{
  "decision": "REJECT",
  "reason": "This capability should be a [SKILL / WORKFLOW_STEP] instead of a TOOL.",
  "suggested_path": "guiding-skill-authoring | capability-planning"
}
```

Only proceed if all boxes are **unchecked**.

---

# Workflow

## Phase 1: Capture Tool Specification

[ ] Step 1: Confirm the capability name
    - Must be `kebab-case`, ≤ 48 characters
    - Pattern: `<verb>-<noun>[-<qualifier>]` (e.g., `parse-business-intent`,
      `validate-bpmn-xml`, `serialize-process-model`)
    - Check against `tool-registry.yaml` for naming conflicts
    - If a similar tool already exists → suggest reusing or extending it

[ ] Step 2: Classify the tool category
    Choose exactly one:

    | Category | When to use |
    |---|---|
    | `parsing` | Converts unstructured/text input to structured data |
    | `transformation` | Converts one structured format to another |
    | `validation` | Checks correctness of a data structure |
    | `execution` | Triggers an external action or side effect |
    | `retrieval` | Reads from a database, index, or external service |
    | `computation` | Pure algorithmic calculation, no I/O |

[ ] Step 3: Define risk level and side effects

    | Level | Side effects | When to use |
    |---|---|---|
    | L0 | `none` | Pure computation — no I/O (serializers, formatters, calculators) |
    | L1 | `read` | Reads from a system but does not modify anything |
    | L2 | `read+write` | Analyzes and may write to internal state/cache |
    | L3 | `write` | Creates or modifies records in an external system |
    | L4 | `external` | Triggers real-world actions (device commands, payments, notifications) |

    Also declare:
    - `idempotent: true/false` — calling with same input always gives same output?
    - If L3 or L4: requires explicit `requires_approval: true` in the spec

[ ] Step 4: Define the input schema (JSON Schema format)
    - Every parameter must have: `type`, `description`
    - Mark required vs. optional parameters explicitly
    - Use enum for fields with a fixed set of values
    - Avoid `type: any` — be specific

    Ask:
    ```
    1. 这个 tool 接受什么输入？（列出所有参数，每个参数的类型和含义）
    2. 哪些参数是必填的？
    3. 是否有参数有固定取值范围？（枚举）
    ```

[ ] Step 5: Define the output schema (JSON Schema format)
    - Every field must have: `type`, `description`
    - Success response must be stable (same structure every time)
    - Avoid untyped `object` or `array` without item schema

    Ask:
    ```
    1. 这个 tool 成功时返回什么？（列出所有字段，每个字段的类型和含义）
    2. 输出结构是否稳定？（调用方可以直接解构）
    ```

[ ] Step 6: Define the error contract
    - At least 2 error codes: one for bad input, one for system/execution failure
    - Each error must have: `code` (UPPER_SNAKE_CASE), `message` (human-readable),
      `retryable: true/false`
    - `retryable: true` = caller can safely retry without side effects
    - `retryable: false` = human intervention needed before retry

    Ask:
    ```
    1. 这个 tool 在什么情况下会失败？
    2. 哪些失败是可以重试的？（网络超时 = 可重试；参数错误 = 不可重试）
    ```

[ ] Step 7: Define usage guidance
    - `when_to_use`: 2-3 concrete scenarios (specific, not generic)
    - `when_not_to_use`: 1-2 anti-patterns
    - `called_by_skills`: list skill_names that call this tool

## Phase 2: Generate TOOL.md

[ ] Step 8: Fill the TOOL.md template
    Copy `assets/tool-template.md` and populate all sections.

    **Hard constraints on the generated spec:**
    - `description` must be ≤ 120 characters, third-person, no vague verbs
      (no "handles", "processes", "deals with")
    - `input_schema` must list all fields with types — no empty `properties: {}`
    - `output_schema` must list all fields with types — no bare `type: object`
    - `errors` must have ≥ 2 entries
    - `implementation.type` must be `mcp | http | internal` (not TBD)

## Phase 3: Validate

[ ] Step 9: Run the automated validator
    ```bash
    python guiding-tool-authoring/scripts/validate_tool.py <path/to/TOOL.md>
    ```
    The validator checks 5 dimensions (50 points total).
    A tool needs **≥ 40/50** to proceed to registration, **≥ 45/50** to be
    approved without required changes.

    **Blocking issues (must fix before registration):**
    - Any dimension scoring 0
    - Missing required fields
    - Risk level inconsistent with side_effects
    - Duplicate tool name in registry

## Phase 4: Register

[ ] Step 10: Add stanza to `tool-registry.yaml`
    ```yaml
    - tool_name: <name>
      display_name: <Human Readable Name>
      category: <category>
      risk_level: <L0|L1|L2|L3|L4>
      side_effects: <none|read|write|external>
      idempotent: <true|false>
      owner_team: <team>
      service: <mcp-server-name>
      status: draft
      path: <relative/path/to/TOOL.md>
      created_at: <ISO date>
      last_reviewed: <ISO date>
      called_by_skills: []
    ```

[ ] Step 11: Register in MCP tool catalog
    Add the tool to `guiding-skill-authoring/references/mcp-tool-catalog.md`
    under the appropriate server section (or create a new server section if
    the service does not exist yet).

    Format: one table row per tool:
    ```
    | `tool_name` | description | key params | returns |
    ```

## Phase 5: Pre-Submission Checklist

- [ ] TOOL.md passes `validate_tool.py` with score ≥ 40/50
- [ ] `tool_name` is unique in `tool-registry.yaml`
- [ ] All input parameters have `type` and `description`
- [ ] All output fields have `type` and `description`
- [ ] At least 2 error codes defined with `retryable` flag
- [ ] `risk_level` matches `side_effects` (L0 = none, L3+ = write/external)
- [ ] `called_by_skills` lists at least one known skill (or "pending" if new)
- [ ] MCP catalog entry added
- [ ] Tool stanza added to `tool-registry.yaml` with `status: draft`

---

# Constraints

- NEVER invent tool names that conflict with existing entries in `tool-registry.yaml`
- NEVER set `risk_level: L0` for a tool that reads from or writes to an external system
- NEVER set `idempotent: true` for a tool with `side_effects: write` or `external`
  unless the operation is genuinely idempotent (e.g., upsert by ID)
- NEVER use `type: any` in input or output schemas — always be specific
- NEVER define only 1 error code — minimum is 2 (input error + system error)
- This skill is READ-ONLY guidance — it does not implement tools, call MCP servers,
  or modify any registry automatically
- A tool spec with `status: draft` is NOT callable by skills until it reaches
  `status: approved` after engineering review

**Meta-skill note:** This skill contains no MCP tool calls by design. It produces
a TOOL.md document, not operational output. `meta_skill: true` exempts Dimensions
2 and 3 from MCP tool compliance checks in `validate_skill.py`.

---

# References

| File | When to read |
|---|---|
| `assets/tool-template.md` | Fillable TOOL.md template — copy this to start |
| `references/tool-governance.md` | Full governance rules, risk matrix, naming guide |
| `../tool-registry.yaml` | Existing tools — check before naming a new tool |
| `../guiding-skill-authoring/references/mcp-tool-catalog.md` | MCP server registry |
| `../capability-planning/SKILL.md` | Phase 0 — run before this skill if scope unclear |

# Scripts

**validate_tool.py** — Automated pre-registration tool validation
```bash
python guiding-tool-authoring/scripts/validate_tool.py <path/to/TOOL.md>
python guiding-tool-authoring/scripts/validate_tool.py <path/to/TOOL.md> --json
```

**Check for naming conflicts:**
```bash
python -c "
import yaml
d = yaml.safe_load(open('tool-registry.yaml', encoding='utf-8'))
names = [t['tool_name'] for t in d['tools']]
print(f'{len(names)} tools registered:')
for n in sorted(names): print(f'  {n}')
"
```
