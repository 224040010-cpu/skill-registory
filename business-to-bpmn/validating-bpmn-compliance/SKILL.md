---
name: validating-bpmn-compliance
bundle_scope: bpmn-agent
risk_level: L2
description: |
  Validates a BPMN 2.0 XML file for structural compliance (namespaces, required
  elements, ID uniqueness) and logical consistency (no deadlocks, no orphan nodes,
  no broken flows). Optionally evaluates intent coverage when original requirements
  are provided. Use when validating any existing or newly generated BPMN file,
  checking if a .bpmn file can be opened in bpmn.io or Camunda, or verifying
  that a generated BPMN covers the original business requirements.
  Trigger on: "校验这个BPMN", "验证XML", "BPMN合规检查", "check BPMN validity",
  "validate BPMN", "BPMN有没有错误", "这个BPMN能在bpmn.io里打开吗",
  "检查需求覆盖度", "BPMN是否覆盖了原始需求".
  Do NOT use when generating BPMN from a description — use converting-business-to-bpmn.
  Do NOT use when the user wants to optimize layout or styling — use the BPMN layout tool.
---

# Purpose

Validates a BPMN 2.0 XML file against two independent but complementary criteria:

1. **Structural Compliance** — Does the XML conform to BPMN 2.0 schema rules?
2. **Logical Consistency** — Is the process flow logically sound (no deadlocks, orphans)?
3. **Intent Coverage** *(optional)* — Does the BPMN cover the original business requirements?

Produces a structured validation report. Does NOT modify the BPMN XML.

---

# Trigger

**Use this Skill when:**
- User provides a `.bpmn` file or BPMN XML string and asks for validation
- After generating BPMN to verify quality before delivery
- User asks "这个BPMN有问题吗", "能在bpmn.io里打开吗", "校验一下"
- User wants to check if the generated BPMN missed any requirements from the original description

**Do NOT use this Skill when:**
- User wants to generate BPMN from scratch → use `converting-business-to-bpmn`
- User wants to fix or modify BPMN → fix based on this skill's error report, then re-validate
- User wants layout/visual improvements only → use `bpmn-diagram-optimizer` tool

---

# Workflow

## Phase 1: Structural + Logical Validation

[ ] Step 1: Run structural and logical checks
    - Call `bpmn-tools:validate_bpmn_structural(bpmn_xml)` → structural_report
    - The tool runs all 12 checks (STRUCT_001–STRUCT_006 and LOGIC_001–LOGIC_006)
    - Error path: if bpmn_xml is not valid XML → "输入不是有效的XML，请确认文件格式"

    **Structural checks performed by tool:**
    - STRUCT_001: Required namespace declarations present
    - STRUCT_002: At least one `<startEvent>` per process
    - STRUCT_003: At least one `<endEvent>` per process
    - STRUCT_004: All element IDs globally unique
    - STRUCT_005: All sequenceFlow sourceRef/targetRef reference valid node IDs
    - STRUCT_006: All participant processRef reference valid process IDs

    **Logical checks performed by tool:**
    - LOGIC_001: All nodes reachable from a startEvent (no orphans)
    - LOGIC_002: All nodes can reach an endEvent (no dead ends)
    - LOGIC_003: ExclusiveGateway has ≥ 2 outgoing flows
    - LOGIC_004: ParallelGateway fork has matching join gateway
    - LOGIC_005: No deadlock patterns (mutually exclusive gateways)
    - LOGIC_006: ExclusiveGateway outgoing flows have conditionExpression (warning)

## Phase 2: Intent Coverage (Optional)

[ ] Step 2: If `original_intent` and `original_entities` are provided by the user
    - Call `bpmn-tools:evaluate_intent_coverage(bpmn_xml, original_intent, original_entities)`
      → coverage_report
    - Flag: `COV_001 — missing_constraint_coverage` if any constraint is unrepresented
    - Flag: `COV_002 — missing_role_coverage` if any role has no lane or task
    - Error path: if intent or entities are malformed → skip coverage check, add warning

## Phase 3: Report

[ ] Step 3 (formerly Step 11): Emit validation report

    ```json
    {
      "valid": true,
      "structural_checks": {
        "passed": 4,
        "failed": 0
      },
      "logical_checks": {
        "passed": 5,
        "failed": 0
      },
      "coverage": {
        "evaluated": false,
        "coverage_score": null,
        "covered_items": [],
        "missing_items": [],
        "recommendations": []
      },
      "errors": [],
      "warnings": [],
      "summary": "BPMN XML passes all structural and logical checks."
    }
    ```

    `valid` is `false` if any item in `errors` has `severity: "error"`.
    `valid` is `true` if only `warnings` are present.

[ ] Step 12: Present findings to user
    - If `valid: true`: "Validation passed. [N warnings if any]."
    - If `valid: false`: List errors grouped by category, suggest fix for each.
    - If coverage evaluated and `coverage_score < 0.8`: list `missing_items`
      and `recommendations`.

---

# Error Code Reference

| Code | Severity | Description |
|------|----------|-------------|
| STRUCT_001 | error | Missing required XML namespace declaration |
| STRUCT_002 | error | Process has no startEvent |
| STRUCT_003 | error | Process has no endEvent |
| STRUCT_004 | error | Duplicate element ID found |
| STRUCT_005 | error | sequenceFlow references non-existent node ID |
| STRUCT_006 | error | Participant references non-existent process ID |
| LOGIC_001 | error | Node not reachable from any startEvent (orphan) |
| LOGIC_002 | error | Node has no path to any endEvent (dead end) |
| LOGIC_003 | error | Gateway has wrong number of outgoing flows |
| LOGIC_004 | error | Parallel gateway fork has no matching join |
| LOGIC_005 | error | Potential deadlock pattern detected |
| LOGIC_006 | warning | ExclusiveGateway outgoing flow missing conditionExpression |
| COV_001 | warning | Business constraint not represented in BPMN |
| COV_002 | warning | Role or system has no corresponding lane or task |

---

# Constraints

- NEVER modify the BPMN XML — this skill only reports, does not fix
- Coverage check (Step 10) is OPTIONAL — only run when `original_intent` and
  `original_entities` are explicitly provided
- `valid: false` must always list at least one `error` item
- All error codes must come from the Error Code Reference table above —
  do not invent new codes
- This skill does NOT call `converting-business-to-bpmn` — it is a read-only validator

---

# References

- Tool catalog: `../tools/tool-catalog.md`
- BPMN generation: `../SKILL.md` (converting-business-to-bpmn)
- Process planning: `../decomposing-business-process/SKILL.md`
