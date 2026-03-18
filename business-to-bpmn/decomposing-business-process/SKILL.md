---
name: decomposing-business-process
bundle_scope: bpmn-agent
risk_level: L2
description: |
  Takes a natural language business description and produces a structured process
  plan: ordered steps with BPMN element hints, a dependency DAG, and annotated
  parallel groups. Use when a user wants to break down a business process into
  structured steps before building a BPMN diagram, or to review and validate the
  process logic independently of XML generation. Trigger on: "把这个流程拆成步骤",
  "帮我规划一下这个业务流程", "拆解一下这个需求", "生成流程步骤", "流程分解",
  "process decomposition", "process planning", or explicit requests to understand
  the structure of a specific business process without needing BPMN XML output.
  Do NOT use when the user wants the final BPMN XML file — use converting-business-to-bpmn instead.
  Do NOT use when the user already has steps and only needs BPMN element mapping.
---

# Purpose

Produces a structured process plan from a natural language business description.
The plan is the intermediate artifact between a user's requirement and a full
BPMN diagram — useful for review, estimation, discussion, or as input to
`converting-business-to-bpmn`.

**Output**: `process_plan.json` containing:
- Ordered steps with BPMN element type hints
- Dependency DAG (nodes + directed edges)
- Parallel groups (steps that can run concurrently)
- Ambiguity flags requiring clarification

This skill does NOT produce BPMN XML. For the full conversion, use
`converting-business-to-bpmn`.

---

# Trigger

**Use this Skill when:**
- User asks "把这个业务描述拆成步骤" or "规划一下这个流程"
- User wants to review process logic before committing to BPMN generation
- User provides a business description and asks what the process structure looks like
- Pre-planning before BPMN generation: user wants to iterate on the process plan first

**Do NOT use this Skill when:**
- User wants the final `.bpmn` file → use `converting-business-to-bpmn`
- User already has a complete step list and wants BPMN elements only
- User wants to validate an existing BPMN file → use `validating-bpmn-compliance`

---

# Workflow

## Phase 1: Understand the Requirement

[ ] Step 1: Parse business intent
    - Call `bpmn-tools:parse_business_intent(user_description)` → intent
    - If `goal` is empty or `business_type` is undefined, ask one clarifying question
      before continuing (do not ask all questions at once)
    - Error path: if description is too short (<20 chars) → "请提供更详细的业务流程描述"

[ ] Step 2: Extract process entities
    - Call `bpmn-tools:extract_process_entities(user_description, intent)` → entities
    - If no roles or systems found → ask: "这个流程涉及哪些角色或系统？"

[ ] Step 3: Check for ambiguities
    - Call `bpmn-tools:detect_description_ambiguity(intent, entities)` → ambiguity_result
    - If `has_ambiguity: true`:
      - Present `clarification_questions` to user (one at a time)
      - Wait for responses, then re-run Steps 1–2 with updated description
    - If `has_ambiguity: false`: proceed to Phase 2

## Phase 2: Build the Process Plan

[ ] Step 4: Check for a matching template
    - Call `bpmn-tools:match_bpmn_template(intent)` → template_result
    - If `best_match.similarity_score ≥ 0.8`:
      - Inform user: "匹配到模板：[template_name]，将以此为基础规划步骤"
      - Use template steps as base → skip Step 5
    - If no match (`best_match: null` or score < 0.5):
      - Continue to Step 5

[ ] Step 5: Decompose into ordered steps
    - Call `bpmn-tools:decompose_process_steps(goal, entities, template_hint?)` → steps
    - Each step has: `id`, `name`, `type`, `bpmn_hint`, `actor`, `preconditions`, `description`
    - Error path: if steps list is empty → retry once; if still empty → "无法拆解流程，请提供更详细描述"

[ ] Step 6: Build dependency graph
    - Call `bpmn-tools:resolve_step_dependencies(steps)` → dag
    - Edges typed as: `sequence`, `conditional` (with condition), `loop_back`

[ ] Step 7: Identify parallel opportunities
    - Call `bpmn-tools:identify_parallel_steps(steps, dag)` → parallel_result
    - Annotate steps with `parallel_group_id` where applicable

## Phase 3: Output

[ ] Step 8: Assemble and present process_plan.json

    ```json
    {
      "business_type": "...",
      "goal": "...",
      "constraints": [...],
      "steps": [
        {
          "id": "s1",
          "name": "...",
          "type": "event|action|decision|subprocess",
          "bpmn_hint": "startEvent|serviceTask|exclusiveGateway|...",
          "actor": "...",
          "preconditions": [],
          "parallel_group_id": null,
          "description": "..."
        }
      ],
      "dag": {
        "nodes": [...],
        "edges": [{"from": "s1", "to": "s2", "type": "sequence"}]
      },
      "parallel_groups": [["s3", "s4"], ["s5", "s6"]],
      "template_used": null,
      "ambiguities_resolved": true
    }
    ```

[ ] Step 9: Present a readable summary table

    | Step | Name | Type | Actor | BPMN Hint | Parallel Group |
    |------|------|------|-------|-----------|----------------|
    | s1   | ...  | event| ...   | startEvent| —              |

    Call out any steps flagged as `decision` and confirm branching conditions
    with the user if they were not explicit in the original description.

[ ] Step 10: Offer next action
    - "如需生成完整 BPMN XML，请使用 converting-business-to-bpmn 并传入此 process_plan"
    - "如需修改某步骤，请告知修改内容，我将更新 process_plan 并重新生成"

---

# Constraints

- NEVER generate BPMN XML in this skill — that is `converting-business-to-bpmn`'s job
- If ambiguity is detected in Step 3, NEVER proceed to Phase 2 without resolution
- Step decomposition must always start with a `startEvent` and end with an `endEvent`
- Decision steps (`type: decision`) must have at least 2 outgoing conditions named
- All steps must have at least one `actor` assigned from the entity list
- Maximum 20 steps in a single plan — if decomposition exceeds 20 steps, split into sub-processes and mark them as `type: subprocess`

---

# References

- Tool catalog: `../tools/tool-catalog.md` — all tools used by this skill
- Orchestrating skill: `../SKILL.md` (converting-business-to-bpmn) — uses this skill's output
- BPMN validation: `../validating-bpmn-compliance/SKILL.md`
