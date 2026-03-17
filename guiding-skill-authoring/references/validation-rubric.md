# Skill Validation Rubric — 7 Dimensions

Total: 70 points
- ≥ 60: Approved (minor suggestions only)
- 45–59: Conditionally approved (required changes before merge)
- 30–44: Major revision required
- < 30: Rewrite required

---

## Dimension 1: Trigger Clarity (10 pts)

**What this checks:** Can the router reliably decide when to invoke this skill?
A skill with a vague description is never triggered. A skill with an overly
broad description conflicts with neighbors.

**Checklist:**
- [ ] Description is written in third person
- [ ] Contains `Use when` with specific trigger phrases or scenarios
- [ ] Contains `Do NOT use when` with at least one exclusion condition
- [ ] Trigger phrases do not overlap with any existing skill in `skill-registry.yaml`
- [ ] Trigger content in `Trigger` section of body matches description

**Scoring:**

| Score | Condition |
|-------|-----------|
| 10 | Third person + `Use when` with specifics + `Do NOT use when` + no neighbor conflict |
| 7 | Clear and specific, but missing exclusion conditions |
| 4 | Vague or overly broad (e.g., "Use when user asks about chargers") |
| 0 | No trigger conditions defined |

**EV domain example:**

```
❌ Score 4 — Too broad:
"Handles charger issues. Use when user mentions a charger."

✅ Score 10 — Specific + exclusions:
"Diagnoses EV charger faults by retrieving device telemetry, analyzing
alarm codes, and recommending repair actions. Use when user reports an
error code, charging failure, device offline, or abnormal session.
Do NOT use when user only asks about charging protocols (use
analyzing-charger-protocols) or wants to create a work order without
an active fault (use dispatching-work-orders)."
```

---

## Dimension 2: Workflow Executability (10 pts)

**What this checks:** Can an agent execute the workflow without improvising?
Every step must name the tool it uses and describe what to do with the result.

**Checklist:**
- [ ] Workflow has a clear start, middle, and end
- [ ] Every step calls a specific MCP tool in `server:tool_name` format
- [ ] At least one error/failure path is defined
- [ ] No step contains vague language like "process the data" or "handle appropriately"
- [ ] Decision branches are explicit (e.g., "If fault_code not found → search knowledge base")

**Scoring:**

| Score | Condition |
|-------|-----------|
| 10 | All steps name tools + error paths defined + no ambiguous steps |
| 7 | Main flow complete and tool-specific, but error paths missing |
| 4 | Steps exist but some are ambiguous or untooled |
| 0 | No workflow defined, or only describes the outcome not the steps |

**EV domain example:**

```
❌ Score 4 — Ambiguous:
"Step 2: Get device information and check for problems."

✅ Score 10 — Specific:
"[ ] Step 2: Retrieve fault history
    - Call device-status-mcp:get_fault_history(device_id, days=30)
    - Count occurrences of same fault_code in response
    - If count >= 3 → mark as recurring_fault = true
    - If fault_code not in references/fault-code-table.md →
      call knowledge-base-mcp:search_knowledge_base(query=fault_code,
      collection='fault_cases', top_k=5)"
```

---

## Dimension 3: MCP Tool Compliance (10 pts)

**What this checks:** Are all tool references valid, properly named, and
used at the appropriate risk level?

**Checklist:**
- [ ] All tools are listed in `references/mcp-tool-catalog.md`
- [ ] All tools use `server-name:tool_name` fully-qualified format
- [ ] L4 (device control) operations include a `verify-gate-mcp:request_approval` step
- [ ] No tool is used beyond its intended scope (e.g., write tools used for read-only skill)
- [ ] Risk level declared in registry matches the highest-risk tool used

**Scoring:**

| Score | Condition |
|-------|-----------|
| 10 | All tools registered + correct format + risk level matches + Verify Gate present if L4 |
| 7 | All tools registered and correctly formatted, but risk level may be understated |
| 4 | 1–2 unregistered tools, or Verify Gate missing for L4 operation |
| 0 | Multiple unregistered tools, or L4 operation with no Verify Gate |

**Risk level quick check:**

| Tools used | Minimum risk level |
|------------|-------------------|
| Only `device-status-mcp`, `knowledge-base-mcp` | L1 or L2 |
| `ticket-system-mcp` (create/update), `notification-mcp` | L3 |
| `verify-gate-mcp` + any control tool | L4 |

---

## Dimension 4: Input/Output Contract (10 pts)

**What this checks:** Are the skill's inputs and outputs defined clearly enough
that an agent can call this skill and consume its output without ambiguity?

**Checklist:**
- [ ] Required parameters listed with type and description
- [ ] Optional parameters listed with defaults
- [ ] Output format defined (JSON schema / natural language / file type)
- [ ] If voice-enabled: output examples contain no markdown, no raw error codes, ≤100 chars/segment
- [ ] Output fields defined in `Constraints` section or `assets/` schema file

**Scoring:**

| Score | Condition |
|-------|-----------|
| 10 | Inputs fully typed + output schema/format defined + voice-compliant if applicable |
| 7 | Inputs defined but output format loosely described |
| 4 | Only casual description ("needs device ID", "returns status") |
| 0 | No input/output definition |

**Voice compliance check (if TTS output):**

```
❌ Not voice-compliant:
"**诊断结果**：ERR_MODULE_TEMP_HIGH，温度：89.3°C，建议：[停止充电](action:stop)"

✅ Voice-compliant:
"充电桩温度过高，当前89.3度，超过安全上限。建议立即停止充电，是否确认？"
```

---

## Dimension 5: Constraints & Safety Boundaries (10 pts)

**What this checks:** Does the skill explicitly define what it will NOT do,
and are high-risk operations protected?

**Checklist:**
- [ ] At least one explicit "NEVER" or "Do not" constraint in the `Constraints` section
- [ ] Scope boundary stated (e.g., "This skill is READ-ONLY — never execute control commands")
- [ ] L4 skills: user confirmation required before execution
- [ ] Data access scoped appropriately (e.g., "only query devices accessible to the requesting user")
- [ ] Output content constraints defined (required fields, format rules)

**Scoring:**

| Score | Condition |
|-------|-----------|
| 10 | Explicit DO-NOTs + high-risk protection + data scope + output constraints |
| 7 | Some constraints defined but not comprehensive |
| 4 | Only implicit constraints (no explicit Constraints section) |
| 0 | No constraints defined |

**EV domain example:**

```
✅ Good Constraints section:
- NEVER skip Step 1 (device state collection) — diagnosis without current state is unreliable
- This skill is READ-ONLY — never call any tool that modifies device state
- Fault severity must be taken from fault-code-table.md, never estimated ad hoc
- Data access is limited to devices associated with the requester's account
- Required output fields: fault_summary, device_id, severity, root_cause, recommended_action
```

---

## Dimension 6: Single Responsibility (10 pts)

**What this checks:** Does this skill do one coherent job? Multi-purpose
skills are hard to route, hard to test, and hard to maintain.

**One-sentence test:** Describe the skill in one sentence without "and also",
"as well as", or "additionally".

**Branching test:** Does the skill have fundamentally different workflow
branches that produce completely different output types? If yes → split.

**Scoring:**

| Score | Condition |
|-------|-----------|
| 10 | One-sentence description is clean, no hidden secondary jobs |
| 7 | Primarily single-purpose with minor attached logic (e.g., suggests a follow-up action) |
| 4 | Clearly doing 2 different things that could be separate skills |
| 0 | Is a "mega skill" that handles multiple unrelated scenarios |

**EV domain examples:**

```
❌ Score 0 — Multiple responsibilities:
"Skill: handling-charger-issues"
→ Queries status, diagnoses faults, creates work orders, notifies technicians,
  and sends customer SMS — this is 4 separate skills.

✅ Score 10 — Single responsibility:
"Skill: diagnosing-charger-faults"
→ Collects telemetry, analyzes fault codes, identifies root cause, returns
  structured diagnosis. Work order creation is a separate skill.
```

---

## Dimension 7: Testability (10 pts)

**What this checks:** Can someone verify the skill works correctly by looking
at the input/output examples?

**Checklist:**
- [ ] At least 1 normal-flow example (input → expected output)
- [ ] At least 1 edge/error case example
- [ ] Examples are in `references/examples.md` or in a `tests/` directory
- [ ] Expected outputs are specific enough to verify (not "returns some status info")
- [ ] `evals/evals.json` exists with at least 2 test prompts (for automated testing)

**Scoring:**

| Score | Condition |
|-------|-----------|
| 10 | Normal example + error example + specific expected outputs + evals.json |
| 7 | Only normal flow example, no error case |
| 4 | Examples described in text but no structured test cases |
| 0 | No examples or test cases |

---

## Scoring Summary Template

Use this when reviewing a skill draft:

```
Skill name: <name>
Reviewer:   <name>
Date:       <YYYY-MM-DD>

Dimension                    Score   Issues
─────────────────────────────────────────────────────
1. Trigger clarity           /10
2. Workflow executability    /10
3. MCP tool compliance       /10
4. Input/output contract     /10
5. Constraints & safety      /10
6. Single responsibility     /10
7. Testability               /10
─────────────────────────────────────────────────────
Total                        /70

Rating: [ ] Approved  [ ] Conditional  [ ] Major revision  [ ] Rewrite

Blocking issues (must fix):
-

Suggestions (non-blocking):
-
```
