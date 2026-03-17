---
name: skill-governance-agent
meta_skill: true
description: |
  Audits the full skill registry for consistency, metadata health, conflict drift,
  and lifecycle issues. Use when performing a daily or weekly governance sweep of
  the skill registry, when suspecting registry drift, or when preparing a governance
  report for review. Do NOT use when authoring a new skill — use guiding-skill-authoring.
  Do NOT use for single-skill admission decisions — use skill-admission-review instead.
---

# Purpose

Provides continuous governance of the skill registry. Scans all SKILL.md files and
`skill-registry.yaml` to surface inconsistencies, stale metadata, naming violations,
overlap drift, and lifecycle signals (deprecated/retired candidates).

Produces two outputs:
- `governance_report_<YYYYMMDD>.json` — full audit report
- `manual_review_queue.json` — skills requiring human intervention

This skill does NOT modify skill content, descriptions, risk levels, or registry status.
All findings are advisory; human owners act on them.

# Trigger

**Use when:**
- Scheduled daily/weekly governance sweep
- After a batch of new skills have been admitted
- When suspecting registry drift or overlap accumulation
- Before a platform release to verify registry health

**Do NOT use when:**
- Authoring or drafting a new skill
- Making a single-skill admission decision
- Reviewing only one specific skill in isolation

# Workflow

## Phase 1: Discover

[ ] Step 1: Scan filesystem for all SKILL.md files
    - Walk all subdirectories of the registry root looking for `*/SKILL.md` files
    - Build a list of `{path, skill_name (from directory name)}`

[ ] Step 2: Load skill-registry.yaml
    - Parse all registered skills with their metadata

## Phase 2: Run Four Audit Checks

[ ] Step 3: Repo consistency check
    - Compare filesystem skills vs. registry entries
    - Flag: `missing_in_registry`, `missing_in_fs`, `metadata_drift`

[ ] Step 4: Metadata health check
    - Validate each registered skill's description length, required fields, naming
    - Flag: `description_degraded`, `missing_fields`, `naming_violation`, `eval_stale`

[ ] Step 5: Conflict drift detection
    - Compute pairwise description similarity across all registered skills
    - Flag: `overlap_candidate`, `trigger_collision`, `family_overload`

[ ] Step 6: Lifecycle governance
    - Check last_reviewed age, eval_status, security_review staleness
    - Flag: `review_overdue`, `needs_fix`, `security_review_overdue`, `deprecated_candidate`

## Phase 3: Emit Reports

[ ] Step 7: Write governance_report_<YYYYMMDD>.json
    - Full structured audit findings per skill

[ ] Step 8: Write manual_review_queue.json
    - Skills requiring human intervention (severity: HIGH or CRITICAL)

[ ] Step 9: Optionally update last_audited in skill-registry.yaml
    - Only the `last_audited` top-level field may be auto-updated
    - All skill-level fields require human approval

# References

- [Governance Policy](references/governance-policy.md)
- [Admission Policy](../skill-admission-review/references/admission-policy.md)
- [Naming Guide](../guiding-skill-authoring/references/naming-guide.md)

# Scripts

Run a full governance audit:
```bash
python skill-governance-agent/scripts/governance_audit.py \
  --registry skill-registry.yaml \
  --skills-root . \
  --output reports/
```

Run with auto-update of last_audited timestamp:
```bash
python skill-governance-agent/scripts/governance_audit.py \
  --registry skill-registry.yaml \
  --skills-root . \
  --output reports/ \
  --update-timestamp
```

# Constraints

- NEVER delete skills, modify descriptions, change risk_level, or change bundle_scope automatically
- NEVER auto-approve or auto-reject skills based on audit findings
- NEVER modify skill content — this skill is governance-only, not content-editing
- Scope: registry-level health only — does not re-run authoring validation on each skill
- Output must include: summary counts, per-skill findings, manual_review_queue
- The only auto-write permitted is updating `last_audited` in skill-registry.yaml (with --update-timestamp flag)
