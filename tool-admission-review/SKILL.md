---
name: tool-admission-review
meta_skill: true
bundle_scope: platform
risk_level: L1
description: |
  Phase 4T platform admission gate for MCP Tools. Evaluates whether a
  proposed tool should be admitted into tool-registry.yaml by running five
  checks: global duplication, service assignment, risk consistency, reuse
  justifiability, and form appropriateness. Use after validate_tool.py
  (Phase 2T) has passed. Use BEFORE updating tool status to 'approved'.
  Do NOT use as a substitute for validate_tool.py — the two gates are
  complementary (authoring quality vs. platform fit).
---

# Purpose

This skill is **Phase 4T** of the platform tool pipeline. It sits after
`guiding-tool-authoring` / `validate_tool.py` and before a tool's status
is changed from `draft` to `approved` in `tool-registry.yaml`.

| Gate | Question it answers | Tool analogue |
|------|--------------------|----|
| Phase 2T `validate_tool.py` | Is this tool spec well-formed? | Phase 2S for skills |
| **Phase 4T `admission_gate_tool.py`** | **Should this tool be a platform asset?** | Phase 4 for skills |

**Without this gate**, the system trades skill explosion for tool explosion:
duplicate tools, single-consumer dead weight, mis-scoped services, and
risk levels that understate actual side effects.

---

# Trigger

**Use this Skill when:**
- A new TOOL.md has been submitted and `validate_tool.py` scored ≥ 45
- A tool is being proposed for `status: approved` in `tool-registry.yaml`
- A reviewer suspects a registered tool might be a duplicate or misclassified

**Do NOT use this Skill when:**
- `validate_tool.py` scored < 45 — fix authoring quality first
- The tool is already `approved` and no changes have been made
- User is asking for help writing a TOOL.md — use `guiding-tool-authoring`

---

# Workflow

## Phase 1: Pre-flight

[ ] Step 1: Confirm Phase 2T has passed
    - Run `validate_tool.py` if not yet done:
      ```bash
      python guiding-tool-authoring/scripts/validate_tool.py <tool>/TOOL.md
      ```
    - If score < 45 → STOP. Return to `guiding-tool-authoring`.
    - If score ≥ 45 → proceed.

[ ] Step 2: Identify the tool under review
    - Parse `TOOL.md` frontmatter: `tool_name`, `service`, `risk.level`,
      `risk.side_effects`, `usage.called_by_skills`.
    - Load current `tool-registry.yaml` for duplicate comparison.

---

## Phase 2: Run the Five Checks

[ ] Step 3: Execute the admission gate script
    ```bash
    python tool-admission-review/scripts/admission_gate_tool.py \
      <tool>/TOOL.md \
      --registry tool-registry.yaml \
      --json
    ```

    The script runs all five checks automatically. Review the JSON output:

    ```json
    {
      "tool_name": "...",
      "decision": "PASS | PASS_WITH_WARNINGS | REQUIRES_REVIEW | REJECT",
      "checks": {
        "check1_global_duplication": { "status": "...", "findings": [...] },
        "check2_service_assignment":  { "status": "...", "findings": [...] },
        "check3_risk_consistency":    { "status": "...", "findings": [...] },
        "check4_reuse_justifiability":{ "status": "...", "findings": [...] },
        "check5_form_appropriateness":{ "status": "...", "findings": [...] }
      },
      "reasons": ["..."],
      "recommended_actions": ["..."],
      "neighbor_tools": ["..."]
    }
    ```

[ ] Step 4: Interpret the decision
    | Decision | Action |
    |----------|--------|
    | `PASS` | Proceed to Phase 3 — update registry to `approved` |
    | `PASS_WITH_WARNINGS` | Document warnings in TOOL.md, proceed to Phase 3 |
    | `REQUIRES_REVIEW` | Discuss findings with tool author; do not admit yet |
    | `REJECT` | Return TOOL.md to author with specific findings; do not admit |

---

## Phase 3: Registry Update (only if PASS or PASS_WITH_WARNINGS)

[ ] Step 5: Update `tool-registry.yaml`
    Change the tool's `status` field:
    ```yaml
    - tool_name: <tool_name>
      status: approved          # was: draft or submitted
      last_reviewed: "<today>"
    ```

[ ] Step 6: Update `mcp-tool-catalog.md` if the tool's service is new
    - Add the tool's entry under its service section in
      `guiding-skill-authoring/references/mcp-tool-catalog.md`
    - Ensure `validate_skill.py`'s `REGISTERED_MCP_SERVERS` dict is updated

[ ] Step 7: Notify consuming skills
    - For each skill in `called_by_skills`, verify their SKILL.md references
      the tool in `server:tool_name()` format
    - If not referenced yet, open a follow-up task for the skill author

---

## Phase 4: Rejection Handling

[ ] Step 8: If REJECT or REQUIRES_REVIEW — emit structured feedback

    For each REJECT finding:
    ```markdown
    ## Tool Admission: REJECTED — <tool_name>

    **Finding**: <check_name> — <finding text>
    **Required action**: <specific fix>
    **Reference**: tool-admission-review/references/tool-admission-policy.md
    ```

    For REQUIRES_REVIEW:
    ```markdown
    ## Tool Admission: REQUIRES_REVIEW — <tool_name>

    Human review needed for the following:
    - <finding 1>
    - <finding 2>

    Reviewer decision:
    [ ] APPROVE WITH NOTE: <justification>
    [ ] REQUEST REVISION: <specific change>
    [ ] REJECT: <reason>
    ```

---

# Output Contract

This skill produces one of:
- A registry update (`tool-registry.yaml` `status: approved`)
- A rejection report with findings and required actions
- A REQUIRES_REVIEW report for human escalation

This skill does NOT modify TOOL.md content. TOOL.md changes are the
responsibility of `guiding-tool-authoring`.

---

# Constraints

- NEVER approve a tool that has 0 declared `called_by_skills` — this is an
  unconditional REJECT regardless of other check results
- NEVER override a REJECT from Check 3 (risk consistency) without explicit
  sign-off from a platform security reviewer
- NEVER admit a tool whose `validate_tool.py` score is < 45 (Phase 2T must
  pass before Phase 4T runs)
- This skill is read-only on TOOL.md — it reads but never modifies the spec
- All admission decisions must be recorded in `reports/` directory

---

# References

| File | When to read |
|------|-------------|
| `references/tool-admission-policy.md` | Full policy rationale for each check |
| `../guiding-tool-authoring/SKILL.md` | Use this first — authoring quality gate |
| `../guiding-tool-authoring/scripts/validate_tool.py` | Phase 2T — run before this |
| `../tool-registry.yaml` | Current tool inventory for duplicate detection |
| `../capability-planning/references/asset-promotion-rules.md` | Upgrade/downgrade paths |

# Scripts

```bash
# Run full admission gate (human-readable)
python tool-admission-review/scripts/admission_gate_tool.py \
  <tool>/TOOL.md \
  --registry tool-registry.yaml

# Run full admission gate (JSON output for CI)
python tool-admission-review/scripts/admission_gate_tool.py \
  <tool>/TOOL.md \
  --registry tool-registry.yaml \
  --json

# Check current registry size before admission
python -c "
import yaml
d = yaml.safe_load(open('tool-registry.yaml', encoding='utf-8'))
tools = d['tools']
print(f'Registry has {len(tools)} tools')
services = {}
for t in tools:
    services.setdefault(t['service'], []).append(t['tool_name'])
for svc, names in services.items():
    print(f'  {svc}: {len(names)} tools')
"
```
