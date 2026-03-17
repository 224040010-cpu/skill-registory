# Platform Constraints — Full Reference

---

## 1. MCP Tool Naming Convention

All tool calls in skill workflows must use the fully-qualified format:

```
<mcp-server-name>:<tool_name>(param=value, ...)
```

Examples:
```
device-status-mcp:get_device_status(device_id="A003")
knowledge-base-mcp:search_knowledge_base(query="OCPP error E07", collection="fault_cases", top_k=5)
ticket-system-mcp:create_work_order(station_id="A003", issue_type="hardware", priority="HIGH")
```

Never invent tool names. If the tool you need does not exist in
`references/mcp-tool-catalog.md`, flag it in the skill draft:

```
⚠️ Tool needed: [describe the capability — e.g., "query billing records by session_id"]
```

Engineering will evaluate whether to add the tool or work around it.

---

## 2. Risk Level Taxonomy

Every skill must declare one risk level. Assign the highest level that applies.

| Level | Name | Characteristics | Example skills |
|-------|------|-----------------|----------------|
| **L1** | Read-only | No writes, no side effects, fully idempotent | `querying-realtime-status` |
| **L2** | Analysis | Read-only but triggers knowledge retrieval or generates reports | `analyzing-charger-protocols`, `generating-maintenance-reports` |
| **L3** | Write / Create | Creates records, sends notifications, dispatches work orders | `dispatching-work-orders` |
| **L4** | Device Control | Modifies device state, restarts hardware, changes power config | Any restart / stop / config skill |

**L4 skills require:**
1. A Verify Gate step in the workflow (see Section 3)
2. Explicit user confirmation before execution
3. A verify step after execution to confirm the operation succeeded
4. Security review before promotion to `approved` status

---

## 3. Verify Gate (L4 Skills)

The Verify Gate is the platform's safety interception layer for device control
operations. It validates:
- Is the requesting user authorized for this operation?
- Is the device in a safe state for this operation?
- Is there a concurrent operation already in progress?

### Required workflow pattern for L4 skills

```
[ ] Step N:   Validate inputs and collect device state
[ ] Step N+1: Prepare operation parameters
[ ] Step N+2: Submit to Verify Gate
              - Call `verify-gate-mcp:request_approval(operation, device_id, params, requester_id)`
              - If APPROVED → proceed to Step N+3
              - If REJECTED → return rejection reason via voice/API response, stop
[ ] Step N+3: Execute the control operation
              - Call `<control-tool>(device_id, params)`
[ ] Step N+4: Verify execution result
              - Call `device-status-mcp:get_device_status(device_id)` to confirm state change
              - If verification fails → log anomaly, alert operator
[ ] Step N+5: Report result to user
```

### Skills that skip the Verify Gate will be REJECTED in security review.

---

## 4. TTS / Voice Output Rules

The platform's voice channel synthesizes all responses via TTS. Skills that
produce voice-facing output (any skill with surfaces including `voice`) must
comply with these rules.

Even non-voice skills should write user-facing messages with TTS in mind,
because the same response may be surfaced through voice in the future.

### Prohibited in voice output

| Prohibited | Reason | Fix |
|------------|--------|-----|
| Markdown syntax (`#`, `**`, `_`, `>`, `-`, `[ ]`) | TTS reads punctuation literally | Rewrite as plain sentences |
| Code blocks / backticks | Unreadable | Remove or paraphrase |
| Raw error codes (`ERR_MODULE_TEMP_HIGH`) | Not user-friendly | Explain in plain language |
| URLs or file paths | Unreadable | Say "file has been generated" instead |
| Tables | Unparseable | Convert to spoken summary |
| Bullet lists | Spoken as "dash item" | Convert to "第一…第二…第三…" |

### Required for voice output

- **Plain sentences only** — no structured formatting
- **Segment length** — ≤ 100 characters per logical response unit
  - Split longer content across multiple segments
- **Error messages** — always user-friendly, never raw system codes
  - ❌ `"返回码 ERR_CHARGER_OFFLINE_403"`
  - ✅ `"该充电桩当前离线，请检查网络连接后重试"`
- **Confirmation prompts** — clear yes/no framing
  - ✅ `"即将重启充电桩 A003，是否确认？请回答是或否。"`
- **Numbers** — cardinal numbers are fine; avoid symbols like `°C`, `kW`
  - ❌ `"当前温度 89.3°C，阈值 85°C"`
  - ✅ `"当前温度89.3度，超过安全上限85度"`

### Voice output example

```
❌ Bad:
"**故障诊断结果**：
- 错误码：ERR_MODULE_TEMP_HIGH
- 温度读数：89.3°C（阈值：85°C）
- 建议：[立即停止充电](action:stop_charging)"

✅ Good:
"充电桩模块温度过高。当前温度89.3度，已超过安全上限85度。
建议立即停止充电，请问是否现在停止？"
```

---

## 5. Skill Isolation Rules

Skills are **leaf nodes** in the execution tree. Orchestration — the logic
that decides which skills to call in which order — belongs to the Agent
or Workflow layer, not inside a skill.

### Prohibited

- Calling or triggering another skill from within a skill's workflow steps
- Writing instructions like `"使用 diagnosing-charger-faults skill 获取诊断结果后..."`
- Designing a skill that waits for output from another skill
- Referencing skill names as execution dependencies

### Correct pattern when two skills need to share data

Instead of Skill A calling Skill B:

```
Agent Orchestrator
  ├── Call Skill B with input params
  │     └── Returns: diagnosis_result
  └── Call Skill A with (input params + diagnosis_result)
```

### Signal that your design needs to be a Workflow, not a Skill

If you find yourself writing any of these patterns, escalate to engineering
as a workflow design request:

- "先用 X skill，再用 Y skill"
- "根据诊断结果决定调哪个 skill"
- "这个 skill 需要另一个 skill 的输出"

---

## 6. Agent Boundary Definitions

Each skill belongs to one agent bundle (`bundle_scope`). Shared skills can
belong to multiple bundles. Routing from user request to skill happens at
the Agent layer.

| Agent | `bundle_scope` value | Owns |
|-------|---------------------|------|
| **Intelligent O&M Agent** | `diagnosis-agent` | Fault diagnosis, work order dispatch, on-site guidance, protocol analysis, maintenance reports, reliability evaluation, maintenance planning |
| **Customer Service Agent** | `customer-agent` | Customer queries, billing questions, account status, charging session Q&A |
| **Operations Agent** | `ops-agent` | Fleet management, capacity planning, operator-facing reporting |
| **Energy Agent** | `energy-agent` | Energy consumption analysis, peak/valley optimization, carbon reporting |

**Shared skills** (e.g., `querying-realtime-status`) may appear in multiple
`bundle_scope` entries.

### Boundary check before authoring

Ask: "Which agent would a user be talking to when they need this skill?"

If the answer is "depends on the user type" → likely a shared skill, or
the scope needs to be narrowed.

If the answer spans two different agent types → split the skill.

---

## 7. Single Responsibility Check

A skill should do **one coherent job**. Use this test:

**One-sentence test:** Can you describe this skill's job in one sentence
without using "and also", "as well as", or "additionally"?

- ✅ `"查询充电桩当前运行状态并返回摘要"`
- ❌ `"查询充电桩状态，如果有故障就诊断，然后创建工单"`
  → This is three skills (query + diagnose + dispatch)

**Trigger uniqueness test:** If a user said the trigger phrase for this
skill, would it be unambiguous which skill they need?

If two skills have overlapping trigger conditions, one of them is too broad.
Check `skill-registry.yaml` before finalizing your description.
