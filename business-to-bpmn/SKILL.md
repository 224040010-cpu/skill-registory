---
name: converting-business-to-bpmn
bundle_scope: bpmn-agent
risk_level: L2
description: |
  将用户自然语言业务描述直接转化为符合 BPMN 2.0 标准的工作流 XML（含泳道、消息流、自动布局与视觉美化），可在 bpmn.io 或 Camunda 中直接打开。
  Use when the user describes a business scenario and wants a BPMN workflow — including phrases like "生成BPMN", "业务转工作流", "设计流程", "把需求转成BPMN", "审批流程", "自动化流程", "SOP转BPMN", "生成.bpmn文件", or requests that describe business scenarios to convert business descriptions into BPMN 2.0 XML. Also trigger on "帮我画个流程", "工作流标准化", "业务流程建模", "流程自动化", "我有个业务场景想变成工作流", even without explicitly mentioning "BPMN".
  Do NOT use when the user only wants a process breakdown without BPMN XML — use decomposing-business-process instead.
  Do NOT use when the user wants to validate an existing BPMN file — use validating-bpmn-compliance instead.
---

# Purpose

End-to-end orchestration skill: takes a natural language business description
and produces a complete `.bpmn` file. Internally orchestrates 13 atomic tools
across 5 pipeline layers.

**This skill is the entry point.** Two related skills exist for specific subtasks:
- `decomposing-business-process` — for process planning only (no XML output)
- `validating-bpmn-compliance` — for validating any BPMN file

---

# Trigger

**Use this Skill when:**
- User provides business scenario description and wants a BPMN workflow file
- User asks for "生成BPMN", "业务转工作流", "SOP转BPMN", "生成.bpmn文件"
- User describes a business process: approvals, alerts, data sync, order processing

**Do NOT use this Skill when:**
- User already has a Mermaid flowchart to convert to BPMN (different domain)
- User only wants a JSON/YAML workflow definition without BPMN format
- User wants to edit or debug an existing `.bpmn` file
- User only wants the process steps without the BPMN XML → use `decomposing-business-process`

---

# Architecture

5 pipeline layers, 13 tools:

```
User Business Description
    │
[Layer 1: 理解层]
    ├── T-01 parse-business-intent
    ├── T-02 extract-process-entities
    └── T-03 detect-description-ambiguity ──► clarify if needed, re-run layer
    │
[Layer 2: 规划层]
    ├── T-04 match-bpmn-template
    └── if no template: T-05 decompose-process-steps
                      → T-06 resolve-step-dependencies
                      → T-07 identify-parallel-steps
    │
[Layer 3: BPMN建模层]
    ├── T-08 map-steps-to-bpmn-elements
    ├── T-09 classify-bpmn-task-types
    ├── T-11 assign-bpmn-participants
    └── T-10 assemble-bpmn-model
    │
[Layer 4: BPMN渲染层]
    ├── T-12 serialize-bpmn-xml
    └── T-13 optimize-bpmn-layout
    │
[Layer 5: 验证层]
    └── validating-bpmn-compliance (skill) ──► if errors: fix and re-run
    │
Output: .bpmn file
```

---

# Workflow

[ ] Step 1: **理解层** — Parse intent, extract entities, check ambiguity
    - Call `bpmn-tools:parse_business_intent(user_description)` → intent
    - Call `bpmn-tools:extract_process_entities(user_description, intent)` → entities
    - Call `bpmn-tools:detect_description_ambiguity(intent, entities)` → ambiguity check
    - If `has_ambiguity: true`: present clarification questions to user, wait for response,
      then re-run Step 1 with updated description
    - If `has_ambiguity: false`: proceed to Step 2
    - Error path: if parse fails (empty/non-business description) → return
      "无法识别业务描述，请提供更具体的流程说明"

[ ] Step 2: **规划层** — Choose template shortcut or decompose from scratch
    - Call `bpmn-tools:match_bpmn_template(intent)` → template match result
    - If `best_match.similarity_score ≥ 0.8`:
      - Use template step structure as the starting steps → skip Steps 2b–2d
    - If no match (`best_match: null` or score < 0.5):
      - Call `bpmn-tools:decompose_process_steps(goal, entities)` → steps
      - Call `bpmn-tools:resolve_step_dependencies(steps)` → dag
      - Call `bpmn-tools:identify_parallel_steps(steps, dag)` → annotated steps

[ ] Step 3: **BPMN建模层** — Map, classify, assign, assemble
    - Call `bpmn-tools:map_steps_to_bpmn_elements(steps, dag)` → element_map
    - Call `bpmn-tools:classify_bpmn_task_types(element_map, steps)` → classified_elements
    - Call `bpmn-tools:assign_bpmn_participants(classified_elements, entities)` → participants, lanes
    - Call `bpmn-tools:assemble_bpmn_model(classified_elements, participants, lanes, message_flows)`
      → process_model
    - Error path: if element_map is empty → return "步骤列表为空，无法建模，请重新描述业务流程"

[ ] Step 4: **BPMN渲染层** — Serialize and optimize
    - Call `bpmn-tools:serialize_bpmn_xml(process_model, participants, lanes, message_flows)`
      → raw_bpmn_xml
    - Call `bpmn-tools:optimize_bpmn_layout(raw_bpmn_xml)` → optimized_bpmn_xml
    - Error path: if serialization fails (invalid model structure) → log error and return
      raw_bpmn_xml without layout optimization

[ ] Step 5: **验证层** — Validate compliance and intent coverage
    - Call `bpmn-tools:validate_bpmn_structural(optimized_bpmn_xml)` → structural_report
    - Call `bpmn-tools:evaluate_intent_coverage(optimized_bpmn_xml, intent, entities)`
      → coverage_report
    - If structural_report has severity `error`:
      - Identify error layer (structural → re-run Step 4; logical → re-run Step 3)
      - Retry maximum 2 times; if still failing return bpmn_xml with error report appended
    - If `coverage_report.coverage_score < 0.7`:
      - Add missing_items as additional steps, re-run Steps 3–4–5 once
    - If validation passes: write `.bpmn` file to output directory

[ ] Step 6: **Output** — Deliver result to user
    - Write `<process_name>.bpmn` to the requested output path (default: current directory)
    - Present summary:
      - Total elements (tasks, gateways, events)
      - Lanes and participants
      - Validation: passed / N warnings
      - Intent coverage score
    - If any warnings remain: list them for the user's awareness

---

# Examples

**Example 1 — 充电桩告警处理流程:**

Input:
> 设计一个充电桩告警诊断与自恢复流程：设备端检测到异常后上报告警，云端Agent分析告警类型，低风险的自动执行恢复命令，高风险的转人工确认后再执行，执行后验证恢复结果并生成报告

Output: `charging-alarm.bpmn`
- 10 elements: startEvent, 5× serviceTask, userTask, exclusiveGateway, endEvent
- 2 lanes: 设备端, 云端Agent
- Validation: passed

**Example 2 — 工单审批流程:**

Input:
> 员工提交工单，主管审批，不通过则退回修改，通过后系统自动分配工程师

Output: `work-order.bpmn`
- 7 elements: startEvent, 2× userTask, exclusiveGateway, serviceTask, endEvent
- Loop-back path: 退回→重新提交
- Validation: passed

---

# Constraints

- Layer 1 must complete before Layer 2 — intent and entities are required by all downstream tools
- Ambiguity must be resolved before planning — never skip the T-03 ambiguity check
- Maximum 2 retry attempts on validation failure — if still failing after 2 retries, return the partial BPMN with the full error report appended
- All tool calls use `bpmn-tools:` server prefix — do NOT invent tool names outside `tools/tool-catalog.md`
- Output is a `.bpmn` file (BPMN 2.0 XML) — never deliver raw JSON or YAML as the primary output
- This skill is WRITE-ONLY for `.bpmn` files — it does not modify any registry, database, or platform state
- Output path defaults to current working directory if not specified by user
- NEVER invoke `decomposing-business-process` or `validating-bpmn-compliance` skills as sub-skills — call their underlying tools directly (`bpmn-tools:validate_bpmn_structural`, etc.)

**Required output fields:**
- File path of the generated `.bpmn` file
- Summary: element count, lane count, validation status, coverage score

---

# References

- Tool catalog: `tools/tool-catalog.md` — all 13 tool definitions and I/O schemas
- Process planning only: `decomposing-business-process/SKILL.md`
- BPMN validation: `validating-bpmn-compliance/SKILL.md`
- Bundle overview: `references/overview.md`
- Error handling guide: `references/troubleshooting.md`
