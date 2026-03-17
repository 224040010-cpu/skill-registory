# Governance Policy

Rules applied by `governance_audit.py` during each scheduled audit.

---

## Check 1: Repo Consistency

| Condition | Code | Severity |
|-----------|------|----------|
| Skill in registry but SKILL.md directory missing | `missing_in_fs` | HIGH |
| SKILL.md directory exists but not in registry | `missing_in_registry` | WARNING |
| SKILL.md frontmatter name ≠ registry skill_name | `metadata_drift` | WARNING |

---

## Check 2: Metadata Health

| Condition | Code | Severity |
|-----------|------|----------|
| Required registry field missing | `missing_fields` | HIGH |
| `purpose` field < 20 characters | `description_degraded` | WARNING |
| `purpose` contains vague terms | `description_degraded` | WARNING |
| `skill_name` violates naming convention | `naming_violation` | WARNING |
| `bundle_scope` not in approved list | `missing_fields` | WARNING |
| `status` not a valid lifecycle state | `missing_fields` | WARNING |
| eval_status=pending + last_reviewed > 90 days | `eval_stale` | WARNING |
| eval_status=failing | `needs_fix` | HIGH |

**Required registry fields**: skill_name, owner_team, version, status, risk_level, bundle_scope, eval_status

---

## Check 3: Conflict Drift

| Condition | Code | Severity |
|-----------|------|----------|
| Pairwise purpose Jaccard > 0.65 | `overlap_candidate` | HIGH |
| Pairwise purpose Jaccard 0.45–0.65 | `overlap_candidate` | WARNING |
| Naming family `verb-*` has ≥ 5 skills in same scope | `family_overload` | WARNING |

---

## Check 4: Lifecycle Governance

| Condition | Code | Severity |
|-----------|------|----------|
| last_reviewed > 180 days ago | `review_overdue` | WARNING |
| L4 skill + security_review=pending > 30 days | `security_review_overdue` | CRITICAL |
| eval_status=failing + last_reviewed > 90 days + status=approved | `deprecated_candidate` | HIGH |
| status=approved + last_reviewed > 365 days | `review_overdue` | WARNING |

---

## Severity Definitions

| Severity | Meaning | Destination |
|----------|---------|-------------|
| CRITICAL | Immediate action required — platform risk | manual_review_queue.json |
| HIGH | Should be resolved in next sprint | manual_review_queue.json |
| WARNING | Should be addressed in next review cycle | governance_report only |
| INFO | Informational, no action required | governance_report only |

---

## Permitted Auto-Actions

The governance agent may **only** perform these writes automatically:
- Update `last_audited` timestamp in skill-registry.yaml (with `--update-timestamp` flag)

The governance agent must **NOT** automatically:
- Delete any skill or directory
- Modify skill descriptions, purpose, or metadata
- Change risk_level, bundle_scope, or owner_team
- Approve or deprecate any skill
- Modify SKILL.md content

All HIGH/CRITICAL findings go into `manual_review_queue.json` for human action.

---

## Suggested Human Actions by Code

| Code | Suggested Action |
|------|-----------------|
| `missing_in_fs` | Restore skill directory or remove registry entry |
| `missing_in_registry` | Register skill as draft or remove directory |
| `metadata_drift` | Align SKILL.md frontmatter name with registry skill_name |
| `missing_fields` | Add missing field to registry entry |
| `description_degraded` | Improve purpose field — clear, specific, ≥ 40 chars |
| `naming_violation` | Rename skill to match verb-ing-object[-qualifier] pattern |
| `eval_stale` | Run evals or create evals.json and update last_reviewed |
| `needs_fix` | Fix failing evals before next deployment |
| `overlap_candidate` | Review pair — merge or explicitly differentiate scope |
| `family_overload` | Consolidate naming family or introduce sub-scopes |
| `review_overdue` | Perform governance review, update last_reviewed |
| `security_review_overdue` | Escalate to security team for L4 review |
| `deprecated_candidate` | Set status: deprecated or fix evals + update last_reviewed |
