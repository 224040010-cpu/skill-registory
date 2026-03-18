---
name: skill-admission-review
meta_skill: true
bundle_scope: platform
risk_level: L2
description: |
  Evaluates whether a proposed skill should be admitted into the platform registry.
  Use when a skill has passed the Authoring Gate (validate_skill.py score ≥ 45) and needs
  a platform-level admission decision. Checks for registry conflicts, agent boundary
  violations, risk level accuracy, routing pollution, and form-factor correctness.
  Do NOT use when authoring or drafting a new skill — use guiding-skill-authoring for that.
  Do NOT use when the skill has not yet passed the Authoring Gate (score < 45).
---

# Purpose

Provides a platform-level admission decision for a skill that has passed local authoring
validation. Stands as the "Admission Gate" — the checkpoint between "can be written" and
"should enter the registry".

This skill produces a structured JSON decision with one of four outcomes:
`PASS`, `PASS_WITH_WARNINGS`, `REQUIRES_REVIEW`, or `REJECT`.

# Trigger

**Use when:**
- A skill has a validate_skill.py score ≥ 45 and is ready for registry admission
- A skill is being re-submitted after a `needs_revision` decision
- Platform team needs a second-opinion check on an existing approved skill

**Do NOT use when:**
- The skill has not yet completed authoring (no SKILL.md, or score < 45)
- The request is to create or improve a skill — use `guiding-skill-authoring` instead
- The request is about ongoing governance of the full registry — use `skill-governance-agent`

# Workflow

## Phase 1: Load Inputs

[ ] Step 1: Accept the candidate skill path and registry path
    - Input: `candidate_skill_path` (path to SKILL.md), `registry_path` (default: skill-registry.yaml)
    - Run: `python skill-admission-review/scripts/admission_gate.py <candidate_skill_path> --registry <registry_path>`

## Phase 2: Run Five Admission Checks

[ ] Step 2: Execute admission_gate.py
    - The script runs all five checks in sequence:
      1. Global conflict check (name similarity, description overlap, trigger collision)
      2. Agent boundary check (bundle_scope validity, cross-agent contamination)
      3. Risk level check (inferred risk vs. declared risk_level)
      4. Routing governance check (description quality, routing pollution risk)
      5. Form factor check (is this a Skill, or should it be a Tool / Workflow node?)
    - If any check returns REJECT → overall decision is REJECT
    - If any check returns REQUIRES_REVIEW → overall decision is REQUIRES_REVIEW (unless already REJECT)
    - If all checks return PASS or WARNING → overall decision is PASS or PASS_WITH_WARNINGS

## Phase 3: Emit Decision

[ ] Step 3: Return structured JSON decision
    - Output includes: decision, reasons[], recommended_actions[], neighbor_skills[]
    - See references/admission-policy.md for full decision criteria

## Phase 4: Update Registry Status

[ ] Step 4: Based on decision, update skill-registry.yaml status field
    - PASS → set status: approved
    - PASS_WITH_WARNINGS → set status: approved (with governance note)
    - REQUIRES_REVIEW → set status: submitted (pending manual review)
    - REJECT → set status: needs_revision

# References

- [Admission Policy](references/admission-policy.md)
- [Platform Constraints](../guiding-skill-authoring/references/platform-constraints.md)
- [Naming Guide](../guiding-skill-authoring/references/naming-guide.md)

# Scripts

Run the admission gate checker:
```bash
python skill-admission-review/scripts/admission_gate.py \
  <path/to/SKILL.md> \
  --registry skill-registry.yaml
```

Output JSON to file:
```bash
python skill-admission-review/scripts/admission_gate.py \
  <path/to/SKILL.md> \
  --registry skill-registry.yaml \
  > admission_result.json
```

# Constraints

- NEVER approve a skill that scores 0 on any validation dimension
- NEVER approve an L4 skill without a verified security_review
- NEVER modify the registry directly — only output a decision; the human owner updates the registry
- This skill is READ-ONLY with respect to the file system
- Scope: platform governance only — does not assess business correctness of skill logic
- Output must include: decision, reasons, recommended_actions, neighbor_skills
