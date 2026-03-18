---
name: skill-governance-agent
meta_skill: true
bundle_scope: platform
risk_level: L1
description: |
  Dual-track continuous governance of both skill-registry.yaml and
  tool-registry.yaml. Runs ten audit checks (S1-S4 for skills, T1-T4
  for tools, X1-X3 for cross-track consistency) to surface registry
  drift, stale metadata, zero-consumer tools, deprecated-tool usage,
  and risk inheritance gaps. Use when performing a governance sweep,
  suspecting registry drift, or preparing a release readiness report.
  Do NOT use when authoring a new skill (use guiding-skill-authoring)
  or for single-asset admission decisions (use skill-admission-review
  or tool-admission-review).
---

# Purpose

Provides **continuous dual-track governance** of the full registry.

Without periodic governance, both registries drift:
- Skills become stale, duplicated, or misrouted
- Tools accumulate with no consumers, wrong risk labels, or dead SKILL references
- Cross-track: a skill may call a deprecated tool, or a tool may list a
  deprecated skill as its only consumer

This skill produces two reports:
- `governance_report_<YYYYMMDD>.json` — full audit with all findings
- `manual_review_queue.json` — HIGH/CRITICAL items requiring human action

All findings are **advisory**. This skill never modifies registry content or
asset status. Human owners act on findings.

---

# Trigger

**Use when:**
- Scheduled daily/weekly governance sweep
- After a batch of new Skills or Tools has been admitted
- When suspecting registry drift, overlap accumulation, or stale data
- Before a platform release to verify full registry health

**Do NOT use when:**
- Authoring or drafting a new skill → use `guiding-skill-authoring`
- Making a single-skill admission decision → use `skill-admission-review`
- Making a single-tool admission decision → use `tool-admission-review`
- Reviewing only one specific asset in isolation

---

# Workflow

## Phase 1: Discover

[ ] Step 1: Scan filesystem and load registries
    ```bash
    # The script handles all discovery automatically
    python skill-governance-agent/scripts/governance_audit.py \
      --registry skill-registry.yaml \
      --tool-registry tool-registry.yaml \
      --skills-root . \
      --output reports/
    ```
    Internally performs:
    - Walk all subdirectories for `*/SKILL.md` files
    - Walk all subdirectories for `*/TOOL.md` files
    - Load skill-registry.yaml and tool-registry.yaml

---

## Phase 2: Run Ten Audit Checks

### Skill Checks (S1–S4)

[ ] Step 2: S1 — Skill repo consistency
    - Compare filesystem skill directories vs. skill-registry.yaml entries
    - Flag: `s1_missing_in_registry`, `s1_missing_in_fs`, `s1_metadata_drift`

[ ] Step 3: S2 — Skill metadata health
    - Validate required fields, description length, naming convention, bundle scope
    - Flag: `s2_missing_fields`, `s2_description_degraded`, `s2_naming_violation`,
      `s2_eval_stale`, `s2_eval_failing`

[ ] Step 4: S3 — Skill conflict drift
    - Compute pairwise purpose similarity across all approved skills
    - Flag: `s3_overlap_candidate` (Jaccard > 0.65 → HIGH, > 0.45 → WARNING),
      `s3_family_overload` (≥5 skills with same verb prefix in same scope)

[ ] Step 5: S4 — Skill lifecycle governance
    - Check review staleness (180-day threshold), eval failures, L4 security review
    - Flag: `s4_review_overdue`, `s4_security_review_overdue` (CRITICAL),
      `s4_deprecated_candidate`, `s4_stale_approved`

### Tool Checks (T1–T4)

[ ] Step 6: T1 — Tool repo consistency
    - Compare TOOL.md files vs. tool-registry.yaml entries
    - Flag: `t1_missing_in_registry`, `t1_missing_in_fs`, `t1_metadata_drift`

[ ] Step 7: T2 — Tool metadata health
    - Validate required fields, naming, category, risk level + side_effects consistency
    - Flag: `t2_missing_fields`, `t2_naming_violation`, `t2_invalid_category`,
      `t2_invalid_risk`, `t2_risk_mismatch`, `t2_invalid_status`

[ ] Step 8: T3 — Tool lifecycle governance
    - Check review staleness; L3/L4 tools flagged at tighter 60-day cadence
    - Flag: `t3_review_overdue`, `t3_high_risk_review_overdue` (HIGH for L3, CRITICAL for L4),
      `t3_stale_approved`

[ ] Step 9: T4 — Consumer integrity
    - Zero consumers → HIGH (tool is dead weight)
    - Single consumer → WARNING (may be a workflow_step in disguise)
    - Consumer skill not in registry → HIGH
    - Consumer skill is deprecated → WARNING
    - Flag: `t4_no_consumers`, `t4_single_consumer`, `t4_unknown_consumer`,
      `t4_deprecated_consumer`

### Cross-Track Checks (X1–X3)

[ ] Step 10: X1 — Dead tool references
    - Scan all SKILL.md bodies for MCP tool calls (`server:tool_name()`)
    - Flag calls to tools absent from tool-registry.yaml
    - Flag: `x1_dead_tool_reference` (HIGH)

[ ] Step 11: X2 — Deprecated tool usage
    - Same scan; flag calls to tools with status: deprecated or retired
    - Flag: `x2_deprecated_tool_usage` (HIGH)

[ ] Step 12: X3 — Risk inheritance gaps
    - For each tool's `called_by_skills`, verify consuming skill's risk_level ≥ tool risk_level
    - A skill calling an L4 tool must itself be L4
    - Flag: `x3_risk_inheritance_gap` (HIGH)

---

## Phase 3: Emit Reports

[ ] Step 13: Review report structure
    ```json
    {
      "generated_at": "...",
      "summary": {
        "total_findings": 98,
        "by_severity": { "CRITICAL": 0, "HIGH": 14, "WARNING": 84 },
        "by_asset_type": { "skill": 79, "tool": 19, "cross": 0 },
        "by_code": { "s2_missing_fields": 12, "t1_missing_in_fs": 13, ... }
      },
      "findings": [...]
    }
    ```

[ ] Step 14: Action the manual_review_queue.json
    - Review HIGH/CRITICAL findings with asset owners
    - Priority order: CRITICAL → HIGH → WARNING
    - For each finding, decide: fix / accept-with-note / defer

[ ] Step 15: Optionally update last_audited timestamps
    ```bash
    python skill-governance-agent/scripts/governance_audit.py \
      --registry skill-registry.yaml \
      --tool-registry tool-registry.yaml \
      --skills-root . \
      --output reports/ \
      --update-timestamp
    ```
    Only the `last_audited` top-level field in each registry is auto-updated.
    All other fields require human action.

---

# Finding Severity Guide

| Severity | Meaning | Typical action |
|----------|---------|----------------|
| `CRITICAL` | Immediate risk to platform safety or compliance | Fix within 24 hours; escalate to security team |
| `HIGH` | Registry integrity issue blocking governance | Fix in current sprint |
| `WARNING` | Quality / housekeeping issue | Fix in next review cycle |
| `INFO` | Informational note | No action required |

---

# Output Contract

Always produces:
- `reports/governance_report_YYYYMMDD.json` — full audit
- `reports/manual_review_queue.json` — HIGH+CRITICAL items

Exit codes:
- `0` — no HIGH or CRITICAL findings
- `1` — at least one HIGH or CRITICAL finding
- `2` — error loading registry (fatal)

---

# Constraints

- NEVER delete skills, tools, or modify registry status automatically
- NEVER auto-approve or auto-reject assets based on audit findings
- NEVER modify SKILL.md or TOOL.md content
- The ONLY permitted auto-write is updating `last_audited` (with `--update-timestamp`)
- Scope: registry-level health only; does not re-run authoring validation on each asset
- `--skills-only` flag is available to run only S1–S4 when tool-registry.yaml is unavailable

---

# References

| File | When to read |
|------|-------------|
| `references/governance-policy.md` | Governance rules, allowed auto-actions, escalation paths |
| `../skill-admission-review/references/admission-policy.md` | Admission criteria (Skill) |
| `../tool-admission-review/references/tool-admission-policy.md` | Admission criteria (Tool) |
| `../capability-planning/references/asset-promotion-rules.md` | Upgrade/downgrade conditions |
| `../guiding-skill-authoring/references/naming-guide.md` | Naming convention reference |

# Scripts

```bash
# Full dual-track governance audit
python skill-governance-agent/scripts/governance_audit.py \
  --registry skill-registry.yaml \
  --tool-registry tool-registry.yaml \
  --skills-root . \
  --output reports/

# With timestamp update
python skill-governance-agent/scripts/governance_audit.py \
  --registry skill-registry.yaml \
  --tool-registry tool-registry.yaml \
  --skills-root . \
  --output reports/ \
  --update-timestamp

# Skills only (when tool-registry unavailable)
python skill-governance-agent/scripts/governance_audit.py \
  --registry skill-registry.yaml \
  --skills-root . \
  --output reports/ \
  --skills-only
```
