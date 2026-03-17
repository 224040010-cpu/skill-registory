---
name: <verb-ing>-<object>[-<qualifier>]
# Rules: lowercase + hyphens only, max 64 chars, no underscores, no Chinese
# Pattern: querying-charge-records / diagnosing-charger-faults / generating-inspection-report
# See references/naming-guide.md for 25+ examples

description: |
  <Third-person description of what this skill does and what it produces.>
  Use when <specific trigger scenario — user phrases, keywords, or events>.
  Do NOT use when <exclusion condition — pointer to the correct skill instead>.
# Rules:
# - Third person only (not "I" or "you")
# - Must contain "Use when" clause
# - Must contain "Do NOT use when" clause with pointer to other skill
# - Be specific — vague descriptions mean the skill never triggers
---

# Purpose

<1-2 sentences explaining what this skill enables and why it exists.
What problem does it solve? Who uses it?>

---

# Trigger

**Use this Skill when:**
- <Trigger condition 1 — specific user phrase or situation>
- <Trigger condition 2>
- <Trigger condition 3>
- <Trigger condition 4 — include IoT/event triggers if applicable>

**Do NOT use this Skill when:**
- <Exclusion 1 — what similar request belongs to a different skill, and which one>
- <Exclusion 2>

---

# Workflow

<!-- Each step MUST name the specific MCP tool it calls.
     Use format: mcp-server-name:tool_name(param=value)
     Never write "look up the data" or "process as needed".
     See references/mcp-tool-catalog.md for all registered tools.
     Mark missing tools as: ⚠️ Tool needed: [describe capability] -->

[ ] Step 1: <Action label>
    - Call `<mcp-server>:<tool_name>(<param>=<value>)`
    - <What to do with the result>
    - <Decision: If X → do Y / If Z → do W>

[ ] Step 2: <Action label>
    - Call `<mcp-server>:<tool_name>(<param>=<value>)`
    - <What to do with the result>

[ ] Step 3: <Action label>
    <!-- For L4 skills: this must be the Verify Gate step -->
    <!-- Call `verify-gate-mcp:request_approval(operation, device_id, params, requester_id)` -->
    <!-- If APPROVED → Step 4 | If REJECTED → return rejection reason, stop -->

[ ] Step 4: <Action label>
    - <Final output step — what is returned/produced>

**Error handling:**
- If <error condition 1> → <what to do>
- If <error condition 2> → <what to do>
- If no data found → <what to return — never fail silently>

---

# References

<!-- List every reference file this skill uses, with a note on when to read it.
     Reference files live in this skill's references/ directory.
     Do not duplicate large content here — link to it. -->

- <Description of what's in it>: See `references/<filename>.md`
- <Description of what's in it>: See `references/<filename>.md`

---

# Scripts

<!-- List scripts in this skill's scripts/ directory with usage instructions.
     Scripts should be executed, not read as context.
     Follow the validate → run_main → verify pattern for L4 operations. -->

**<script-name>.py** — <What it does>
- Execute: `python scripts/<script-name>.py <args>`
- Input: <what to pass>
- Output: <what it returns, format>

---

# Constraints

<!-- Explicit boundaries on what this skill DOES NOT do.
     High-risk skills must include safety guards here.
     Required output fields must be listed here or in assets/ schema. -->

- NEVER <prohibited action 1>
- NEVER <prohibited action 2>
- This skill is <READ-ONLY / WRITE / L4 control> — <scope statement>
- Data access is limited to <scope, e.g., "devices associated with the requester's account">
- Output must include ALL of the following fields:
  1. <field 1>
  2. <field 2>
  3. <field 3>
- <Format constraint, e.g., "monetary values must use two decimal places (CNY)">
- <Voice constraint if applicable: "All user-facing text must be TTS-compliant —
    no markdown, ≤100 chars per segment, no raw error codes">

---

<!-- ============================================================
REGISTRY ENTRY — copy this stanza to skill-registry.yaml
Replace all <placeholders> before submitting
============================================================ -->

<!--
- skill_name: <your-skill-name>
  display_name: <中文显示名称>
  purpose: |
    <一段话描述 skill 的职责，中文>
  owner_team: <team-name>
  owner_individual: TBD
  version: v1.0.0
  rollback_version: null
  status: draft
  risk_level: <L1|L2|L3|L4>
  dependencies:
    mcp_servers:
      - <mcp-server-name>
    packages: []
    external_services: []
  supported_models:
    - claude-sonnet-4-6
  surfaces:
    - api
  bundle_scope:
    - <diagnosis-agent|customer-agent|ops-agent|energy-agent>
  eval_status:
    last_eval_date: null
    eval_result: PENDING
    eval_score: null
  security_review:
    status: pending
    reviewer: null
    review_date: null
    checksum: null
-->
