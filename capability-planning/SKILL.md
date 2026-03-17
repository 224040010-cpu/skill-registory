---
name: capability-planning
meta_skill: true
bundle_scope: platform
risk_level: L1
description: |
  Decomposes a broad user requirement into atomic capability units, classifies each
  as skill / tool / workflow_step using structured decision criteria, runs a
  self-critique pass to prevent skill explosion, and produces a structured
  capability plan as the authoritative input to skill generation.
  Use when a user says "我想做一个agent", "帮我设计这个功能", "我需要实现XXX流程",
  "这个需求要几个skill", or when the requirement is broad enough that it is
  unclear how many skills it should produce. Use BEFORE guiding-skill-authoring —
  do NOT generate a SKILL.md until this planning phase is complete and reviewed.
  Do NOT use when the user has already defined one clear single-purpose skill and
  only needs authoring or validation help.
---

# Purpose

This skill is **Phase 0** of the platform skill pipeline. It sits before
`guiding-skill-authoring` and prevents the two most damaging failure modes of
unguided skill generation:

| Failure mode | What happens | This skill prevents it by |
|---|---|---|
| **Skill explosion** | 1 business goal → 15 micro-skills | Classifying atomic actions as tools, merging over-split skills |
| **Fake skills** | A step inside a workflow becomes a standalone skill | Classifying non-trigger-able units as `workflow_step` |

**Output**: a `capability_plan.json` that is the mandatory input for the next
phase. `guiding-skill-authoring` must NOT be started without a reviewed plan.

---

# Trigger

**Use this Skill when:**
- User describes a business goal that might require multiple capabilities
  ("我要做一个从业务描述生成BPMN的功能")
- User asks "这需要几个skill?" or "帮我拆分一下"
- User submits a skill bundle with unexpectedly many skills (≥ 5)
- Pre-authoring planning for a new agent or capability area
- Reviewing an existing skill set for over-fragmentation

**Do NOT use this Skill when:**
- User already presents one focused, clearly-scoped skill for authoring
  → go directly to `guiding-skill-authoring`
- User wants to validate or fix an existing SKILL.md
  → go to `guiding-skill-authoring` Phase 3
- User asks general platform questions
  → answer directly

---

# Workflow

## Phase 1: Capture Requirement

[ ] Step 1: Elicit the full business goal
    - Ask if not already stated:
      ```
      1. 用一句话描述你想构建的完整功能（动词 + 宾语）
      2. 用户说什么话会触发这个功能？（举 2-3 个例子）
      3. 最终交付物是什么？（报告 / BPMN文件 / 工单 / 状态更新 / 语音播报）
      4. 涉及哪些外部系统或数据源？
      ```
    - Do NOT proceed to Phase 2 until all four questions are answered.

[ ] Step 2: Restate the requirement in structured form
    Output a one-paragraph scope summary:
    > "该功能的目标是：[verb] [object]，触发条件是 [trigger]，
    > 最终产物为 [output]，涉及系统 [systems]。"

    If the summary requires "并且" or "同时" to connect two independent goals →
    treat them as separate capability clusters and plan each independently.

---

## Phase 2: Capability Decomposition

[ ] Step 3: Break the requirement into atomic capabilities
    Decompose until each capability has **one verb + one noun**. Stop when
    further split would produce units with no independent value.

    Output format:
    ```json
    {
      "capabilities": [
        {
          "id": "cap-01",
          "name": "<verb>-<noun>",
          "description": "One sentence — what it does and what it produces.",
          "input": "What data/context it needs",
          "output": "What it returns"
        }
      ]
    }
    ```

    **Decomposition rules:**
    - Each capability must be expressible as `<verb> <noun>` with no "and"
    - If two capabilities always run together and share state → merge them
    - If a capability is "check if X then do Y" → keep as one capability
    - If a capability is "do X, then do Y, then do Z" → three capabilities

---

## Phase 3: Capability Classification

[ ] Step 4: Classify each capability using the decision tree

    Apply this decision tree to each capability from Step 3:

    ```
    Q1: Can this capability be independently triggered by a user request?
        (i.e., a user might ask for ONLY this, without the surrounding context)
    ├── NO  → workflow_step
    └── YES → Q2

    Q2: Does this capability require multi-step reasoning, context accumulation,
        or conditional branching?
    ├── NO  → tool  (single deterministic operation — implement as MCP Tool)
    └── YES → Q3

    Q3: Is this capability reusable across different user intents or agents?
    ├── NO  → workflow_step  (too context-specific to be a standalone skill)
    └── YES → skill
    ```

    Output format (extend each capability object):
    ```json
    {
      "id": "cap-01",
      "name": "...",
      "description": "...",
      "input": "...",
      "output": "...",
      "independent_trigger": true,
      "multi_step": true,
      "reusable": true,
      "final_type": "skill",
      "classification_rationale": "One sentence explaining the decision."
    }
    ```

    **Type definitions:**

    | Type | Meaning | Next action |
    |---|---|---|
    | `skill` | Independent trigger + multi-step reasoning + reusable | → guiding-skill-authoring |
    | `tool` | Single atomic, deterministic operation | → flag as "MCP Tool Needed" |
    | `workflow_step` | No independent trigger, or too context-specific | → flag as "Agent Workflow Layer" |

---

## Phase 4: Self-Critique

[ ] Step 5: Run the five self-critique checks

    After classification, ask these questions of the full capability set:

    **Check A — Tool masquerading as skill**
    > Are there any `skill` entries that have ≤ 1 workflow step and no error
    > handling path? If yes → reclassify as `tool`.

    **Check B — Over-fragmentation**
    > Are there any two `skill` entries whose descriptions overlap by > 70%?
    > If yes → consider merging. Merged skills must still satisfy Q1–Q3.

    **Check C — Trigger dependency**
    > Are there any `skill` entries that can ONLY be triggered as a
    > consequence of another skill's output (not by a user directly)?
    > If yes → reclassify as `workflow_step`.

    **Check D — Scope creep**
    > Does any `skill` entry touch more than one agent boundary
    > (bundle_scope conflict)? If yes → split by agent boundary.

    **Check E — Combinatorial explosion**
    > Is the total `skill` count > 7 for a single user requirement?
    > If yes → re-examine whether some should be `workflow_step` or `tool`.

    For each check that triggers, output:
    ```json
    {
      "check": "B",
      "affected": ["cap-03", "cap-05"],
      "finding": "Both skills describe entity extraction from text.",
      "action": "merge",
      "merged_name": "extracting-entities-from-text"
    }
    ```

[ ] Step 6: Apply self-critique decisions
    - Reclassify or merge capabilities as determined in Step 5
    - Re-run the decision tree (Step 4) on any merged capability
    - Produce the final updated capability list

---

## Phase 5: Output Capability Plan

[ ] Step 7: Emit `capability_plan.json`

    ```json
    {
      "schema_version": "1.0",
      "source_requirement": "<the restated scope summary from Step 2>",
      "generated_at": "<ISO date>",
      "summary": {
        "total_capabilities": 0,
        "skills": 0,
        "tools": 0,
        "workflow_steps": 0
      },
      "capabilities": [
        {
          "id": "cap-01",
          "name": "...",
          "description": "...",
          "final_type": "skill | tool | workflow_step",
          "suggested_bundle_scope": "...",
          "suggested_risk_level": "L1 | L2 | L3 | L4",
          "classification_rationale": "..."
        }
      ],
      "next_actions": [
        {
          "capability_id": "cap-01",
          "action": "Start guiding-skill-authoring with this capability as input",
          "priority": 1
        },
        {
          "capability_id": "cap-03",
          "action": "File MCP Tool request for: extract entities from text",
          "priority": 2
        }
      ],
      "deferred": [
        {
          "capability_id": "cap-07",
          "type": "workflow_step",
          "note": "Implement at agent workflow layer, not as a standalone skill."
        }
      ]
    }
    ```

[ ] Step 8: Present the plan to the human for review

    Show a concise summary table:

    | ID | Capability | Type | Bundle | Risk | Next Action |
    |----|-----------|------|--------|------|-------------|
    | cap-01 | ... | skill | ... | L2 | → guiding-skill-authoring |
    | cap-03 | ... | tool | ... | L1 | → MCP Tool request |
    | cap-07 | ... | workflow_step | ... | — | → Agent Workflow Layer |

    Wait for human confirmation before handing off to `guiding-skill-authoring`.
    Any `skill`-type capability that the human approves becomes the **input**
    to one `guiding-skill-authoring` session.

---

## Phase 6: Handoff

[ ] Step 9: For each approved `skill`-type capability → route to `guiding-skill-authoring`

    Pass the following as the starting context:
    ```
    Capability: <name>
    Description: <description from plan>
    Input: <input from plan>
    Output: <output from plan>
    Suggested bundle: <bundle_scope>
    Suggested risk level: <risk_level>
    Rationale: <classification_rationale>
    ```

    `guiding-skill-authoring` Phase 1 (intent capture) will use this context
    to skip questions already answered here.

[ ] Step 10: For each approved `tool`-type capability → route to `guiding-tool-authoring`

    Pass the following as the starting context:
    ```
    Capability: <name>
    Description: <description from plan>
    Category: <parsing|transformation|validation|execution|retrieval|computation>
    Input: <input from plan>
    Output: <output from plan>
    Suggested risk: <L0|L1|L2|L3|L4>
    Suggested service: <mcp-server-name>
    Called by: <skill_names that will use this tool>
    ```

    `guiding-tool-authoring` Pre-Flight and Phase 1 will use this context to
    skip the capability type validation and start directly at Step 1 (naming).

    If `guiding-tool-authoring` is not yet available, emit a tool request stub:
    ```markdown
    ## MCP Tool Request
    - **Tool name**: <kebab-case verb-noun>
    - **Capability**: <description>
    - **Input**: <input fields>
    - **Output**: <output fields>
    - **Estimated risk**: <L0-L4>
    - **Needed by skill**: <skill_name>
    ```

[ ] Step 11: For each `workflow_step`-type capability, emit a workflow note
    ```markdown
    ## Agent Workflow Note
    - **Step name**: <name>
    - **Purpose**: <description>
    - **Placement**: After <cap-X>, before <cap-Y>
    - **Note**: Implement at agent workflow layer — not a standalone skill or tool.
    ```

---

# Output Contract

This skill always produces:
- `capability_plan.json` — the authoritative structured plan
- A summary table for human review
- Zero SKILL.md drafts — that is `guiding-skill-authoring`'s job

**The separation is strict:**
- This skill = PLAN (what to build and why)
- `guiding-skill-authoring` = BUILD (how to write one skill)

---

# Constraints

- NEVER generate a SKILL.md draft during this phase — planning and drafting are
  separate phases
- NEVER skip Phase 4 (self-critique) — it is the primary anti-fragmentation gate
- NEVER accept a requirement that cannot be restated in one scope summary sentence
  (Step 2) — clarify until it can be
- All capability names must follow `<verb>-<noun>` format (no "and", no articles)
- Maximum 7 skills per planning session — if more, re-examine classification
- The capability plan must be human-reviewed (Step 8) before any skill generation
  begins — do NOT auto-proceed
- This skill produces no side effects: no files are written, no registry is
  modified, no tools are called

**Required output fields — `capability_plan.json` is only valid when it contains:**
- `schema_version` (string)
- `source_requirement` (string, the scope summary from Step 2)
- `generated_at` (ISO date string)
- `summary.total_capabilities`, `summary.skills`, `summary.tools`, `summary.workflow_steps` (integers)
- `capabilities[]` each with: `id`, `name`, `description`, `final_type`, `classification_rationale`
- `next_actions[]` (may be empty array, but field must be present)
- `deferred[]` (may be empty array, but field must be present)

**Edge cases:**
- If the requirement cannot be scoped in one sentence after 3 clarifying rounds →
  treat it as two separate planning sessions; return to Step 1 for each
- If ALL capabilities classify as `tool` or `workflow_step` (zero skills) →
  this is valid; present the plan and note that no SKILL.md authoring is needed
- If a capability sits ambiguously between `skill` and `tool` → prefer `tool`
  (conservative default: skills are more expensive to maintain)

**Meta-skill note:** This skill contains no MCP tool calls by design. It is a
structural reasoning skill that produces a planning document, not operational
output. The `meta_skill: true` frontmatter exempts Dimensions 2 and 3 from MCP
tool compliance checks in `validate_skill.py`.

---

# References

| File | When to read |
|------|-------------|
| `references/classification-guide.md` | Extended examples of skill vs tool vs workflow_step decisions with real platform cases |
| `references/anti-patterns.md` | Common over-fragmentation patterns and how to recognize them |
| `../guiding-skill-authoring/SKILL.md` | The next phase — start here after the plan is approved |
| `../skill-admission-review/references/admission-policy.md` | Admission criteria to anticipate during planning |
| `../skill-registry.yaml` | Existing skill names to check for overlap before planning new ones |

# Scripts

Check if a proposed capability set is within bounds before planning:
```bash
python -c "
import yaml
d = yaml.safe_load(open('skill-registry.yaml'))
names = [s['skill_name'] for s in d['skills']]
print(f'Registry has {len(names)} skills')
print('Existing bundles:', set(s['bundle_scope'] for s in d['skills']))
"
```
