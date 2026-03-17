#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
governance_audit.py — Skill Registry Governance Audit (Phase 5)

Performs four audit checks across the entire skill registry:
  1. Repo consistency  — filesystem vs. registry alignment
  2. Metadata health   — field completeness, naming, description quality
  3. Conflict drift    — overlap detection, trigger collisions, family overload
  4. Lifecycle         — staleness, eval failures, deprecated candidates

Usage:
    python governance_audit.py \\
        --registry skill-registry.yaml \\
        --skills-root . \\
        --output reports/ \\
        [--update-timestamp]

Outputs:
    reports/governance_report_YYYYMMDD.json   — full audit
    reports/manual_review_queue.json          — human intervention queue

Exit codes:
    0 — No HIGH/CRITICAL findings
    1 — One or more HIGH/CRITICAL findings exist
    2 — Error loading registry or skills root
"""

import sys
import re
import json
import argparse
from pathlib import Path
from datetime import datetime, date

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]{1,62}[a-z0-9]$")

VALID_BUNDLE_SCOPES = {
    "diagnosis-agent", "customer-agent", "ops-agent",
    "energy-agent", "bpmn-agent", "platform",
}

VALID_STATUSES = {
    "draft", "submitted", "approved", "restricted",
    "needs_revision", "deprecated", "retired",
}

VAGUE_DESC_WORDS = [
    "manages", "handles", "general", "various", "deals with",
    "helps with", "provides support", "works with",
]

REQUIRED_REGISTRY_FIELDS = [
    "skill_name", "owner_team", "version", "status",
    "risk_level", "bundle_scope", "eval_status",
]

# Governance thresholds (days)
REVIEW_OVERDUE_DAYS = 180
EVAL_STALE_DAYS = 90
SECURITY_OVERDUE_DAYS = 30
DEPRECATED_CANDIDATE_DAYS = 90  # no review + failing evals


# ─────────────────────────────────────────────
# Loaders
# ─────────────────────────────────────────────

def load_registry(registry_path: Path) -> list[dict]:
    try:
        import yaml
        with open(registry_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("skills", [])
    except ImportError:
        return _load_registry_fallback(registry_path)
    except (OSError, Exception) as e:
        print(f"ERROR loading registry: {e}", file=sys.stderr)
        return []


def _load_registry_fallback(registry_path: Path) -> list[dict]:
    """Minimal YAML parser for skill-registry.yaml without PyYAML."""
    skills = []
    try:
        content = registry_path.read_text(encoding="utf-8")
    except OSError:
        return []

    current_skill: dict | None = None
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("- skill_name:"):
            if current_skill:
                skills.append(current_skill)
            val = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            current_skill = {"skill_name": val}
            continue
        if current_skill and ":" in stripped and not stripped.startswith("-"):
            key, _, val = stripped.partition(":")
            val = val.strip().strip('"').strip("'")
            current_skill[key.strip()] = val
    if current_skill:
        skills.append(current_skill)
    return skills


def discover_skill_files(skills_root: Path) -> list[dict]:
    """Scan filesystem for all SKILL.md files. Returns list of {path, dir_name}."""
    found = []
    for skill_md in skills_root.rglob("SKILL.md"):
        # Skip hidden/system directories
        parts = skill_md.parts
        if any(p.startswith(".") for p in parts):
            continue
        dir_name = skill_md.parent.name
        found.append({"path": skill_md, "dir_name": dir_name})
    return found


def try_read_frontmatter(path: Path) -> dict | None:
    """Attempt to read SKILL.md frontmatter. Returns None if encrypted/binary."""
    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None

    if not content.startswith("---"):
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    frontmatter = {}
    current_key = None
    current_value_lines = []
    for line in parts[1].strip().splitlines():
        if line and not line.startswith(" ") and ":" in line:
            if current_key:
                frontmatter[current_key] = " ".join(current_value_lines).strip()
            key, _, val = line.partition(":")
            current_key = key.strip()
            current_value_lines = [val.strip()] if val.strip() else []
        elif current_key:
            current_value_lines.append(line.strip())
    if current_key:
        frontmatter[current_key] = " ".join(current_value_lines).strip()

    return frontmatter


# ─────────────────────────────────────────────
# Similarity helper
# ─────────────────────────────────────────────

def _jaccard(text_a: str, text_b: str) -> float:
    words_a = set(re.findall(r"\b\w{3,}\b", text_a.lower()))
    words_b = set(re.findall(r"\b\w{3,}\b", text_b.lower()))
    if not words_a and not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def _days_since(date_str: str) -> int | None:
    """Return days since a date string (YYYY-MM-DD). None if unparseable."""
    try:
        d = date.fromisoformat(date_str[:10])
        return (date.today() - d).days
    except (ValueError, TypeError):
        return None


# ─────────────────────────────────────────────
# Finding builder
# ─────────────────────────────────────────────

def finding(skill_name: str, code: str, severity: str, message: str, action: str = "") -> dict:
    """Severity: INFO | WARNING | HIGH | CRITICAL"""
    return {
        "skill_name": skill_name,
        "code": code,
        "severity": severity,
        "message": message,
        "action": action,
    }


# ─────────────────────────────────────────────
# Check 1: Repo consistency
# ─────────────────────────────────────────────

def check_repo_consistency(
    fs_skills: list[dict],
    registry: list[dict],
) -> list[dict]:
    findings = []
    reg_names = {s["skill_name"] for s in registry}
    fs_dir_names = {s["dir_name"] for s in fs_skills}

    # Registry entries without corresponding filesystem directories
    for rname in reg_names:
        if rname not in fs_dir_names:
            # Some skills have paths that differ from dir_name (e.g., business-to-bpmn root)
            reg_entry = next((s for s in registry if s["skill_name"] == rname), {})
            path = reg_entry.get("path", "")
            findings.append(finding(
                rname, "missing_in_fs", "HIGH",
                f"Skill '{rname}' is in registry (path: {path}) but directory not found in filesystem",
                "Verify the skill directory exists or update/remove the registry entry",
            ))

    # Filesystem directories without registry entry
    for fs in fs_skills:
        dname = fs["dir_name"]
        if dname not in reg_names:
            findings.append(finding(
                dname, "missing_in_registry", "WARNING",
                f"Directory '{dname}' has a SKILL.md but is not in skill-registry.yaml",
                "Register this skill with status: draft or remove the directory",
            ))

    # Version/status drift (only for readable frontmatter)
    for fs in fs_skills:
        fm = try_read_frontmatter(fs["path"])
        if fm is None:
            continue  # encrypted/binary — skip field comparison
        reg_entry = next((s for s in registry if s["skill_name"] == fs["dir_name"]), None)
        if reg_entry is None:
            continue
        fm_name = fm.get("name", "")
        if fm_name and fm_name != reg_entry["skill_name"]:
            findings.append(finding(
                reg_entry["skill_name"], "metadata_drift", "WARNING",
                f"SKILL.md name '{fm_name}' differs from registry skill_name '{reg_entry['skill_name']}'",
                "Align the name field in SKILL.md frontmatter with skill_name in registry",
            ))

    return findings


# ─────────────────────────────────────────────
# Check 2: Metadata health
# ─────────────────────────────────────────────

def check_metadata_health(registry: list[dict]) -> list[dict]:
    findings = []

    for skill in registry:
        name = skill.get("skill_name", "<unknown>")

        # Required fields
        for field in REQUIRED_REGISTRY_FIELDS:
            if not skill.get(field):
                findings.append(finding(
                    name, "missing_fields", "HIGH",
                    f"Required registry field '{field}' is missing or empty",
                    f"Add '{field}' to the skill's registry entry",
                ))

        # Description/purpose quality
        purpose = skill.get("purpose", "")
        if len(purpose) < 20:
            findings.append(finding(
                name, "description_degraded", "WARNING",
                f"Registry 'purpose' is too short ({len(purpose)} chars) — router quality will suffer",
                "Expand the 'purpose' field to describe the skill's function clearly",
            ))
        for vague in VAGUE_DESC_WORDS:
            if vague in purpose.lower():
                findings.append(finding(
                    name, "description_degraded", "WARNING",
                    f"Registry 'purpose' contains vague term '{vague}'",
                    "Replace vague terms with specific trigger conditions",
                ))
                break

        # Naming convention
        skill_name = skill.get("skill_name", "")
        if skill_name and not NAME_PATTERN.match(skill_name):
            findings.append(finding(
                name, "naming_violation", "WARNING",
                f"skill_name '{skill_name}' violates naming convention (verb-ing-object[-qualifier])",
                "Rename to match pattern: all-lowercase, hyphens only, verb-ing prefix",
            ))

        # Bundle scope
        scope = skill.get("bundle_scope", "")
        if scope and scope not in VALID_BUNDLE_SCOPES:
            findings.append(finding(
                name, "missing_fields", "WARNING",
                f"bundle_scope '{scope}' is not in approved scope list",
                f"Set bundle_scope to one of: {', '.join(sorted(VALID_BUNDLE_SCOPES))}",
            ))

        # Status validity
        status = skill.get("status", "")
        if status and status not in VALID_STATUSES:
            findings.append(finding(
                name, "missing_fields", "WARNING",
                f"status '{status}' is not a valid lifecycle state",
                f"Set status to one of: {', '.join(sorted(VALID_STATUSES))}",
            ))

        # Eval staleness
        eval_status = skill.get("eval_status", "pending")
        last_reviewed = skill.get("last_reviewed", "")
        days = _days_since(last_reviewed) if last_reviewed else None

        if eval_status == "pending" and days is not None and days > EVAL_STALE_DAYS:
            findings.append(finding(
                name, "eval_stale", "WARNING",
                f"eval_status=pending and last_reviewed was {days} days ago (threshold: {EVAL_STALE_DAYS})",
                "Run evals and update eval_status, or create evals/evals.json",
            ))

        if eval_status == "failing":
            findings.append(finding(
                name, "needs_fix", "HIGH",
                "eval_status=failing — skill is producing incorrect outputs",
                "Investigate and fix failing evals before next release",
            ))

    return findings


# ─────────────────────────────────────────────
# Check 3: Conflict drift
# ─────────────────────────────────────────────

def check_conflict_drift(registry: list[dict]) -> list[dict]:
    findings = []
    approved = [s for s in registry if s.get("status") in ("approved", "submitted", "restricted")]

    # Pairwise description similarity
    for i, skill_a in enumerate(approved):
        for skill_b in approved[i + 1:]:
            name_a = skill_a.get("skill_name", "")
            name_b = skill_b.get("skill_name", "")
            purpose_a = skill_a.get("purpose", "")
            purpose_b = skill_b.get("purpose", "")
            sim = _jaccard(purpose_a, purpose_b)

            if sim > 0.65:
                findings.append(finding(
                    name_a, "overlap_candidate", "HIGH",
                    f"High description similarity with '{name_b}' (Jaccard={sim:.2f})",
                    f"Review both skills — consider merging or explicitly differentiating scope",
                ))
            elif sim > 0.45:
                findings.append(finding(
                    name_a, "overlap_candidate", "WARNING",
                    f"Moderate description similarity with '{name_b}' (Jaccard={sim:.2f})",
                    "Verify these skills have clearly distinct trigger conditions",
                ))

    # Naming family overload: same bundle_scope prefix family
    scope_families: dict[str, list[str]] = {}
    for skill in approved:
        scope = skill.get("bundle_scope", "other")
        scope_families.setdefault(scope, []).append(skill.get("skill_name", ""))

    for scope, names in scope_families.items():
        # Group by verb prefix (first segment of name)
        prefixes: dict[str, list[str]] = {}
        for n in names:
            prefix = n.split("-")[0] if "-" in n else n
            prefixes.setdefault(prefix, []).append(n)
        for prefix, group in prefixes.items():
            if len(group) >= 5:
                findings.append(finding(
                    scope, "family_overload", "WARNING",
                    f"Naming family '{prefix}-*' in scope '{scope}' has {len(group)} skills: "
                    f"{', '.join(group[:5])}{'...' if len(group) > 5 else ''}",
                    "Consider consolidating or using sub-scopes to reduce cognitive overhead",
                ))

    return findings


# ─────────────────────────────────────────────
# Check 4: Lifecycle governance
# ─────────────────────────────────────────────

def check_lifecycle(registry: list[dict]) -> list[dict]:
    findings = []
    today_str = date.today().isoformat()

    for skill in registry:
        name = skill.get("skill_name", "<unknown>")
        status = skill.get("status", "")
        risk_level = skill.get("risk_level", "L1")
        eval_status = skill.get("eval_status", "pending")
        security_review = skill.get("security_review", "not_required")
        last_reviewed = skill.get("last_reviewed", "")

        # Skip retired skills
        if status == "retired":
            continue

        days = _days_since(last_reviewed) if last_reviewed else None

        # Review overdue
        if days is not None and days > REVIEW_OVERDUE_DAYS:
            findings.append(finding(
                name, "review_overdue", "WARNING",
                f"Skill has not been reviewed in {days} days (threshold: {REVIEW_OVERDUE_DAYS})",
                "Schedule a governance review and update last_reviewed",
            ))

        # L4 security review overdue
        if risk_level == "L4" and security_review == "pending":
            sec_days = _days_since(last_reviewed) if last_reviewed else SECURITY_OVERDUE_DAYS + 1
            if sec_days is not None and sec_days > SECURITY_OVERDUE_DAYS:
                findings.append(finding(
                    name, "security_review_overdue", "CRITICAL",
                    f"L4 skill has security_review=pending for {sec_days} days "
                    f"(threshold: {SECURITY_OVERDUE_DAYS})",
                    "Escalate to security team — L4 skills require approved security review",
                ))

        # Deprecated candidate: failing evals + no review in 90+ days
        if (
            eval_status == "failing"
            and days is not None
            and days > DEPRECATED_CANDIDATE_DAYS
            and status == "approved"
        ):
            findings.append(finding(
                name, "deprecated_candidate", "HIGH",
                f"Skill has eval_status=failing and no review in {days} days — "
                "candidate for deprecation",
                f"Either fix evals + update last_reviewed, or set status: deprecated",
            ))

        # Stale approved skills (very long, no activity)
        if status == "approved" and days is not None and days > 365:
            findings.append(finding(
                name, "review_overdue", "WARNING",
                f"Skill has been approved but not reviewed in over a year ({days} days)",
                "Perform a yearly review — verify the skill is still relevant and functional",
            ))

    return findings


# ─────────────────────────────────────────────
# Auto-update timestamp (only permitted auto-write)
# ─────────────────────────────────────────────

def update_registry_timestamp(registry_path: Path) -> None:
    """Update the top-level last_audited field in skill-registry.yaml."""
    try:
        content = registry_path.read_text(encoding="utf-8")
        today = date.today().isoformat()
        updated = re.sub(
            r"^last_audited:.*$",
            f'last_audited: "{today}"',
            content,
            flags=re.MULTILINE,
        )
        registry_path.write_text(updated, encoding="utf-8")
    except OSError as e:
        print(f"WARNING: Could not update last_audited: {e}", file=sys.stderr)


# ─────────────────────────────────────────────
# Report writer
# ─────────────────────────────────────────────

def write_reports(findings: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat().replace("-", "")

    # Count by severity
    counts = {"INFO": 0, "WARNING": 0, "HIGH": 0, "CRITICAL": 0}
    for f in findings:
        counts[f.get("severity", "INFO")] = counts.get(f.get("severity", "INFO"), 0) + 1

    # Count by code
    codes: dict[str, int] = {}
    for f in findings:
        codes[f["code"]] = codes.get(f["code"], 0) + 1

    report = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_findings": len(findings),
            "by_severity": counts,
            "by_code": codes,
        },
        "findings": findings,
    }

    report_path = output_dir / f"governance_report_{today}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Manual review queue: HIGH + CRITICAL only
    queue_findings = [f for f in findings if f.get("severity") in ("HIGH", "CRITICAL")]
    queue = {
        "generated_at": datetime.now().isoformat(),
        "requires_human_action": len(queue_findings),
        "queue": queue_findings,
    }
    queue_path = output_dir / "manual_review_queue.json"
    with open(queue_path, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)

    print(f"Report written: {report_path}")
    print(f"Review queue:   {queue_path}")
    print(
        f"Summary: {len(findings)} findings — "
        f"{counts['CRITICAL']} CRITICAL, {counts['HIGH']} HIGH, "
        f"{counts['WARNING']} WARNING, {counts['INFO']} INFO"
    )


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Skill Registry Governance Audit")
    parser.add_argument("--registry", default="skill-registry.yaml",
                        help="Path to skill-registry.yaml")
    parser.add_argument("--skills-root", default=".",
                        help="Root directory to scan for SKILL.md files")
    parser.add_argument("--output", default="reports",
                        help="Output directory for reports")
    parser.add_argument("--update-timestamp", action="store_true",
                        help="Auto-update last_audited in skill-registry.yaml")
    args = parser.parse_args()

    registry_path = Path(args.registry)
    skills_root = Path(args.skills_root)
    output_dir = Path(args.output)

    if not registry_path.exists():
        print(f"ERROR: Registry not found: {registry_path}", file=sys.stderr)
        return 2

    registry = load_registry(registry_path)
    if not registry:
        print("ERROR: Registry is empty or could not be loaded", file=sys.stderr)
        return 2

    fs_skills = discover_skill_files(skills_root)

    print(f"Loaded {len(registry)} registry entries, found {len(fs_skills)} SKILL.md files")
    print("Running four governance checks...")

    all_findings: list[dict] = []
    all_findings.extend(check_repo_consistency(fs_skills, registry))
    all_findings.extend(check_metadata_health(registry))
    all_findings.extend(check_conflict_drift(registry))
    all_findings.extend(check_lifecycle(registry))

    write_reports(all_findings, output_dir)

    if args.update_timestamp:
        update_registry_timestamp(registry_path)
        print(f"Updated last_audited in {registry_path}")

    has_critical = any(f.get("severity") in ("HIGH", "CRITICAL") for f in all_findings)
    return 1 if has_critical else 0


if __name__ == "__main__":
    sys.exit(main())
