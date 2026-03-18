---
name: guiding-skill-authoring
meta_skill: true
bundle_scope: platform
risk_level: L2
description: |
  Guides users through the full lifecycle of creating, validating, and submitting
  skills for the EV charging station agent platform — from intent capture and
  workflow design to MCP tool compliance and registry entry. Use when anyone asks
  to create a skill, write a skill, design a skill, validate a skill draft, check
  whether a workflow can become a skill, or wants to know what a good skill looks
  like on this platform. Also trigger on: "我要写一个skill", "帮我设计一个skill",
  "这个流程能做成skill吗", "skill怎么写", "skill模板", "skill检查", "提交skill".
  Do NOT use when user asks how a specific existing skill works (e.g., how does
  diagnosing-charger-faults behave), or when user wants to invoke an existing skill.
---

# Purpose

This skill is the authoritative guide for creating production-ready skills on
the EV charging station agent platform. It covers the full authoring lifecycle:

- **Intent capture** — structured interview to define what the skill does
- **Skill drafting** — fill the standard template with platform-specific rules
- **Validation** — 7-dimension quality check before engineering review
- **Registry entry** — prepare the `skill-registry.yaml` stanza
- **Submission checklist** — final gate before handing off

If you already have a draft skill and only need validation, jump to [Phase 3](#phase-3-validate).

---

# Trigger

**Use this Skill when:**
- User wants to create, design, or write a new skill for the platform
- User asks "我要写一个skill"、"帮我设计一个skill"、"这个流程能做成skill吗"
- User needs to validate a skill draft or check if it meets platform standards
- User asks for "skill模板"、"skill检查"、"skill怎么写"、"提交skill"
- User asks about naming conventions, trigger format, or MCP tool usage rules
- User wants to know whether a workflow is suitable to become a skill

**Do NOT use this Skill when:**
- User asks about how a specific existing skill works (e.g., how does `diagnosing-charger-faults` diagnose)
- User wants to invoke or execute an existing skill (route to that skill instead)
- User asks general questions about Agent architecture not related to authoring

---

# Platform Quick Reference

> Full details in `references/platform-constraints.md`. Read it before drafting any skill.

| Rule | Requirement |
|------|-------------|
| **MCP tools** | Only tools from registered MCP servers. Use fully-qualified `server:tool_name` format. See `references/mcp-tool-catalog.md`. |
| **Risk levels** | Every skill must declare a risk level: L1 (read-only) → L2 (analysis) → L3 (writes/creates) → L4 (device control). L4 requires Verify Gate. |
| **Device control** | Any operation that restarts, stops, or modifies a device MUST route through the Verify Gate node. Skill workflow must include a Verify Gate step. |
| **Skill isolation** | Skills are leaf nodes. A skill MUST NOT call or trigger another skill. Orchestration belongs to the Agent/Workflow layer. |
| **Agent boundary** | Each skill belongs to one `bundle_scope` agent. Cross-agent workflows must be split into separate skills. |
| **Voice output** | If the skill's response is delivered via TTS, all output text must follow TTS rules — no markdown, ≤100 chars per segment, no error codes. |

---

# Workflow

## Phase 1: Capture Intent

Ask the skill author these questions. Adapt to Chinese if the user prefers.
Extract answers from existing conversation before asking — do not re-ask what
is already known.

```
1. 用一句话描述这个 skill 做什么？（动词 + 宾语 格式）
2. 用户说什么话或做什么操作会触发这个 skill？（给 2-3 个例子）
3. 哪些相似请求不应该触发这个 skill？（给 1-2 个排除场景）
4. 这个 skill 需要哪些信息才能工作？（必填参数、选填参数）
5. 这个 skill 完成后交付什么？（语音回复 / 文件 / 工单 / 状态更新）
6. 这个 skill 会控制设备吗？（重启、断电、改参数 → 需要 Verify Gate）
7. 这个 skill 输出会通过 TTS 播报吗？（是 → 语音约束生效）
8. 这个 skill 属于哪个 Agent？（见 references/platform-constraints.md → Agent 边界）
```

When all questions are answered, confirm the scope in one sentence:
> "这个 skill 的职责是：[动词] [宾语]，在 [触发场景] 时触发，输出 [产物]，属于 [Agent]，风险等级 [L1-L4]。"

If this summary requires "并且" to connect two separate jobs → split into two skills.

---

## Phase 2: Draft the Skill

Copy `assets/skill-template.md` and fill in each section.

### Naming rules

Pattern: `<verb-ing>-<object>[-<qualifier>]`

| Good ✅ | Bad ❌ |
|---------|-------|
| `querying-charge-records` | `chargeRecordQuery` |
| `diagnosing-charger-faults` | `fault_diagnosis` |
| `generating-inspection-report` | `EV_skill_001` |
| `notifying-maintenance-alert` | `notify` |
| `processing-refund-request` | `退款处理` |

See `references/naming-guide.md` for 25+ domain-specific examples.

### Description formula

```
[Third-person description of what the skill does and what it produces].
Use when [trigger scenario / user intent / specific keywords or phrases].
Do NOT use when [exclusion conditions].
```

The description is the primary routing signal. Being too vague = skill never triggers.
Being too broad = skill conflicts with neighbors. See naming guide for examples.

### Workflow steps

Each step must name the exact MCP tool it calls:

```
[ ] Step N: [Action label]
    - Call `mcp-server:tool_name(param=value)`
    - [What to do with the result]
    - [Decision branch if applicable]
```

Never write "look up the data" or "process as needed" — name the tool.
If no registered tool exists for a step → flag it: `⚠️ Tool needed: [describe capability]`

---

## Phase 3: Validate

Run the automated validation script first:

```bash
python skills/guiding-skill-authoring/scripts/validate_skill.py \
  skills/<your-skill-name>/SKILL.md
```

Then apply the 7-dimension rubric from `references/validation-rubric.md`.
A skill needs **≥ 45/70** to proceed to engineering review, **≥ 60/70** to be
approved without required changes.

**Blocking issues (must fix before submission):**
- Any dimension scoring 0–3
- Tools referenced that are not in `references/mcp-tool-catalog.md`
- Device control operations with no Verify Gate step
- TTS output containing markdown (if voice-enabled)
- A skill that calls or triggers another skill

---

## Phase 4: Prepare Registry Entry

Every new skill requires a `skill-registry.yaml` stanza. Use this template:

```yaml
- skill_name: <your-skill-name>
  display_name: <Chinese display name>
  purpose: |
    <One paragraph describing what this skill does, in Chinese>
  owner_team: <team-name>
  owner_individual: TBD
  version: v1.0.0
  rollback_version: null
  status: draft                        # Always start as draft
  risk_level: <L1|L2|L3|L4>
  dependencies:
    mcp_servers:
      - <mcp-server-name>              # List all MCP servers used
    packages: []
    external_services: []
  supported_models:
    - claude-sonnet-4-6
  surfaces:
    - api
  bundle_scope:
    - <agent-name>                     # Which agent bundle this skill belongs to
  eval_status:
    last_eval_date: null
    eval_result: PENDING
    eval_score: null
  security_review:
    status: pending
    reviewer: null
    review_date: null
    checksum: null
```

---

## Phase 5: Pre-Submission Checklist

Confirm every item before opening a PR:

**Structure**
- [ ] `SKILL.md` is present and passes `validate_skill.py` with score ≥ 45/70
- [ ] `assets/` contains any schemas or templates the skill references
- [ ] `scripts/` contains any pre-built scripts mentioned in the workflow
- [ ] `references/` contains any knowledge files linked from the body

**Naming & Description**
- [ ] `name` follows `verb-ing-object[-qualifier]` pattern, lowercase + hyphens only
- [ ] `name` is ≤ 64 characters
- [ ] `description` is written in third person
- [ ] `description` contains `Use when` and `Do NOT use when` clauses
- [ ] No naming conflicts with existing skills in `skill-registry.yaml`

**Workflow**
- [ ] Every step names a specific MCP tool in `server:tool_name` format
- [ ] All MCP tools are registered in `references/mcp-tool-catalog.md`
- [ ] No step says "call another skill" or "use the X skill"
- [ ] Abnormal/error paths are defined (not just the happy path)

**Platform Compliance**
- [ ] Risk level declared and matches actual operations
- [ ] Device control operations include a Verify Gate step (L4 skills)
- [ ] TTS output sections contain no markdown, ≤100 chars per segment (if voice)
- [ ] `bundle_scope` correctly identifies the owning agent

**Registry**
- [ ] New stanza added to `skill-registry.yaml` with `status: draft`
- [ ] All MCP server dependencies listed under `dependencies.mcp_servers`
- [ ] `supported_models` tested manually

---

# Constraints

- NEVER invent MCP tool names — only reference tools listed in `references/mcp-tool-catalog.md`
- This skill is READ-ONLY guidance — it does not modify the registry, create files on its own, or invoke other skills
- NEVER skip Phase 1 (intent capture) — drafting without a clear scope produces unusable output
- All generated skill drafts must use the structure from `assets/skill-template.md`, not free-form layout
- All generated skill drafts must be run through `validate_skill.py` and reach ≥ 45/70 before submission
- Do not generate a full draft before Phase 1 is complete — confirm scope summary first

**Meta-skill note:** This skill contains no MCP tool calls by design. It is a guidance skill
that produces documentation outputs (SKILL.md drafts, validation reports, registry stanzas),
not operational outputs. The `meta_skill: true` frontmatter field exempts Dimensions 2 and 3
from MCP tool compliance checks in `validate_skill.py`.

---

# References

| File | When to read |
|------|-------------|
| `references/platform-constraints.md` | Full TTS rules, Verify Gate flow, Agent boundary definitions, skill isolation rules |
| `references/mcp-tool-catalog.md` | All registered MCP servers and tools with risk levels and signatures |
| `references/validation-rubric.md` | Full 7-dimension scoring rubric with EV-domain examples and scoring guidance |
| `references/naming-guide.md` | Verb taxonomy, 25+ naming examples, description formula examples |
| `assets/skill-template.md` | Fillable SKILL.md template — copy this to start a new skill |

# Scripts

**validate_skill.py** — Automated pre-submission skill validation
- Execute: `python skills/guiding-skill-authoring/scripts/validate_skill.py <path/to/SKILL.md>`
- Output: Validation report with dimension scores, blocking issues, and suggestions
- Meta-skills (with `meta_skill: true` in frontmatter) receive adjusted scoring for Dimensions 2 and 3
- Always run this before opening a PR
