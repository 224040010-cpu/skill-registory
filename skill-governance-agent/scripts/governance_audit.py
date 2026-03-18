#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
governance_audit.py — Dual-Track Registry Governance Audit (Phase 5)

Audits both skill-registry.yaml and tool-registry.yaml, plus cross-track
consistency between them.

Ten audit checks in three groups:

  Skill checks (S1–S4):
    S1. Repo consistency  — filesystem vs. skill-registry alignment
    S2. Metadata health   — field completeness, naming, description quality
    S3. Conflict drift    — purpose overlap, trigger collisions, family overload
    S4. Lifecycle         — staleness, eval failures, deprecated candidates

  Tool checks (T1–T4):
    T1. Tool repo consistency   — filesystem vs. tool-registry alignment
    T2. Tool metadata health    — required fields, naming, description
    T3. Tool lifecycle          — staleness, L3/L4 review cadence
    T4. Consumer integrity      — zero/single consumers, orphaned references

  Cross-track checks (X1–X3):
    X1. Dead tool references    — skills call tools not in tool-registry
    X2. Deprecated tool usage   — skills call deprecated/retired tools
    X3. Orphaned consumer refs  — tools list skills that don't exist / are deprecated

Usage:
    python governance_audit.py \\
        --registry skill-registry.yaml \\
        --tool-registry tool-registry.yaml \\
        --skills-root . \\
        --output reports/ \\
        [--update-timestamp]

Outputs:
    reports/governance_report_YYYYMMDD.json   — full dual-track audit
    reports/manual_review_queue.json          — human intervention queue

Exit codes:
    0 — No HIGH/CRITICAL findings
    1 — One or more HIGH/CRITICAL findings exist
    2 — Error loading registries
"""

import sys
import io
import re
import json
import argparse
from pathlib import Path
from datetime import datetime, date

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

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

VALID_TOOL_CATEGORIES = {
    "parsing", "transformation", "validation",
    "execution", "retrieval", "computation",
}

VALID_RISK_LEVELS = {"L0", "L1", "L2", "L3", "L4"}

RISK_SIDE_EFFECTS_MATRIX = {
    "L0": "none", "L1": "read", "L2": "read",
    "L3": "write", "L4": "external",
}

VAGUE_DESC_WORDS = [
    "manages", "handles", "general", "various", "deals with",
    "helps with", "provides support", "works with",
]

REQUIRED_SKILL_FIELDS = [
    "skill_name", "owner_team", "version", "status",
    "risk_level", "bundle_scope", "eval_status",
]

REQUIRED_TOOL_FIELDS = [
    "tool_name", "category", "risk_level", "side_effects",
    "owner_team", "service", "status",
]

# MCP tool call pattern: server:tool_name(
MCP_CALL_PATTERN = re.compile(r"\b([\w][\w-]+):([\w][\w_]+)\(")

# Governance thresholds (days)
REVIEW_OVERDUE_DAYS = 180
EVAL_STALE_DAYS = 90
SECURITY_OVERDUE_DAYS = 30
DEPRECATED_CANDIDATE_DAYS = 90
TOOL_L34_REVIEW_DAYS = 60    # L3/L4 tools reviewed at higher cadence


# ─────────────────────────────────────────────
# Loaders
# ─────────────────────────────────────────────

def load_skill_registry(registry_path: Path) -> list[dict]:
    try:
        import yaml
        with open(registry_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("skills", [])
    except ImportError:
        return _load_registry_fallback(registry_path, key="skill_name")
    except (OSError, Exception) as e:
        print(f"ERROR loading skill registry: {e}", file=sys.stderr)
        return []


def load_tool_registry(registry_path: Path) -> list[dict]:
    try:
        import yaml
        with open(registry_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("tools", [])
    except ImportError:
        return _load_registry_fallback(registry_path, key="tool_name")
    except (OSError, Exception) as e:
        print(f"ERROR loading tool registry: {e}", file=sys.stderr)
        return []


def _load_registry_fallback(registry_path: Path, key: str = "skill_name") -> list[dict]:
    """Minimal key:value YAML parser without PyYAML."""
    assets = []
    try:
        content = registry_path.read_text(encoding="utf-8")
    except OSError:
        return []
    current: dict | None = None
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith(f"- {key}:"):
            if current:
                assets.append(current)
            val = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            current = {key: val}
            continue
        if current and ":" in stripped and not stripped.startswith("-"):
            k, _, v = stripped.partition(":")
            current[k.strip()] = v.strip().strip('"').strip("'")
    if current:
        assets.append(current)
    return assets


def discover_skill_files(skills_root: Path) -> list[dict]:
    """Scan filesystem for all SKILL.md files."""
    found = []
    for skill_md in skills_root.rglob("SKILL.md"):
        parts = skill_md.parts
        if any(p.startswith(".") for p in parts):
            continue
        found.append({"path": skill_md, "dir_name": skill_md.parent.name})
    return found


def discover_tool_files(skills_root: Path) -> list[dict]:
    """Scan filesystem for all TOOL.md files."""
    found = []
    for tool_md in skills_root.rglob("TOOL.md"):
        parts = tool_md.parts
        if any(p.startswith(".") for p in parts):
            continue
        found.append({"path": tool_md, "dir_name": tool_md.parent.name})
    return found


def try_read_frontmatter(path: Path) -> dict | None:
    """Read SKILL.md or TOOL.md frontmatter. Returns None if unreadable."""
    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None

    # TOOL.md may be pure YAML without fences
    if not content.startswith("---"):
        try:
            import yaml
            data = yaml.safe_load(content)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    frontmatter: dict = {}
    current_key = None
    current_value_lines: list[str] = []
    for line in parts[1].strip().splitlines():
        if line and not line.startswith(" ") and ":" in line:
            if current_key:
                frontmatter[current_key] = " ".join(current_value_lines).strip()
            k, _, v = line.partition(":")
            current_key = k.strip()
            current_value_lines = [v.strip()] if v.strip() else []
        elif current_key:
            current_value_lines.append(line.strip())
    if current_key:
        frontmatter[current_key] = " ".join(current_value_lines).strip()
    return frontmatter


def read_skill_body(path: Path) -> str:
    """Read the body text of a SKILL.md (after frontmatter)."""
    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""
    if not content.startswith("---"):
        return content
    parts = content.split("---", 2)
    return parts[2] if len(parts) >= 3 else ""


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _jaccard(text_a: str, text_b: str) -> float:
    words_a = set(re.findall(r"\b\w{3,}\b", text_a.lower()))
    words_b = set(re.findall(r"\b\w{3,}\b", text_b.lower()))
    if not words_a and not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def _days_since(date_str: str) -> int | None:
    try:
        d = date.fromisoformat(str(date_str)[:10])
        return (date.today() - d).days
    except (ValueError, TypeError):
        return None


def finding(
    asset_name: str,
    code: str,
    severity: str,
    message: str,
    action: str = "",
    asset_type: str = "skill",
) -> dict:
    """severity: INFO | WARNING | HIGH | CRITICAL"""
    return {
        "asset_type": asset_type,
        "asset_name": asset_name,
        # backward-compat alias
        "skill_name": asset_name,
        "code": code,
        "severity": severity,
        "message": message,
        "action": action,
    }


# ─────────────────────────────────────────────
# S1: Skill repo consistency
# ─────────────────────────────────────────────

def check_s1_repo_consistency(
    fs_skills: list[dict],
    registry: list[dict],
) -> list[dict]:
    findings = []
    reg_names = {s["skill_name"] for s in registry}
    fs_dir_names = {s["dir_name"] for s in fs_skills}

    for rname in reg_names:
        if rname not in fs_dir_names:
            reg_entry = next((s for s in registry if s["skill_name"] == rname), {})
            findings.append(finding(
                rname, "s1_missing_in_fs", "HIGH",
                f"Skill '{rname}' is in registry (path: {reg_entry.get('path', '?')}) "
                "but directory not found in filesystem",
                "Verify the skill directory exists or remove/update the registry entry",
            ))

    for fs in fs_skills:
        dname = fs["dir_name"]
        if dname not in reg_names:
            findings.append(finding(
                dname, "s1_missing_in_registry", "WARNING",
                f"Directory '{dname}' has a SKILL.md but is not in skill-registry.yaml",
                "Register this skill with status: draft, or remove the directory",
            ))

    for fs in fs_skills:
        fm = try_read_frontmatter(fs["path"])
        if fm is None:
            continue
        reg_entry = next((s for s in registry if s["skill_name"] == fs["dir_name"]), None)
        if reg_entry is None:
            continue
        fm_name = fm.get("name", "")
        if fm_name and fm_name != reg_entry["skill_name"]:
            findings.append(finding(
                reg_entry["skill_name"], "s1_metadata_drift", "WARNING",
                f"SKILL.md name '{fm_name}' differs from registry skill_name '{reg_entry['skill_name']}'",
                "Align the name field in SKILL.md frontmatter with skill_name in registry",
            ))

    return findings


# ─────────────────────────────────────────────
# S2: Skill metadata health
# ─────────────────────────────────────────────

def check_s2_metadata_health(registry: list[dict]) -> list[dict]:
    findings = []
    for skill in registry:
        name = skill.get("skill_name", "<unknown>")

        for field in REQUIRED_SKILL_FIELDS:
            if not skill.get(field):
                findings.append(finding(
                    name, "s2_missing_fields", "HIGH",
                    f"Required registry field '{field}' is missing or empty",
                    f"Add '{field}' to the skill's registry entry",
                ))

        purpose = skill.get("purpose", "")
        if len(purpose) < 20:
            findings.append(finding(
                name, "s2_description_degraded", "WARNING",
                f"Registry 'purpose' is too short ({len(purpose)} chars)",
                "Expand the 'purpose' field to describe the skill's function clearly",
            ))
        for vague in VAGUE_DESC_WORDS:
            if vague in purpose.lower():
                findings.append(finding(
                    name, "s2_description_degraded", "WARNING",
                    f"Registry 'purpose' contains vague term '{vague}'",
                    "Replace vague terms with specific trigger conditions",
                ))
                break

        skill_name = skill.get("skill_name", "")
        if skill_name and not NAME_PATTERN.match(skill_name):
            findings.append(finding(
                name, "s2_naming_violation", "WARNING",
                f"skill_name '{skill_name}' violates naming convention",
                "Rename to match pattern: all-lowercase, hyphens only",
            ))

        scope = skill.get("bundle_scope", "")
        if scope and scope not in VALID_BUNDLE_SCOPES:
            findings.append(finding(
                name, "s2_invalid_scope", "WARNING",
                f"bundle_scope '{scope}' is not in approved scope list",
                f"Set bundle_scope to one of: {', '.join(sorted(VALID_BUNDLE_SCOPES))}",
            ))

        status = skill.get("status", "")
        if status and status not in VALID_STATUSES:
            findings.append(finding(
                name, "s2_invalid_status", "WARNING",
                f"status '{status}' is not a valid lifecycle state",
                f"Set status to one of: {', '.join(sorted(VALID_STATUSES))}",
            ))

        eval_status = skill.get("eval_status", "pending")
        last_reviewed = skill.get("last_reviewed", "")
        days = _days_since(last_reviewed) if last_reviewed else None
        if eval_status == "pending" and days is not None and days > EVAL_STALE_DAYS:
            findings.append(finding(
                name, "s2_eval_stale", "WARNING",
                f"eval_status=pending and last_reviewed was {days} days ago",
                "Run evals or create evals/evals.json",
            ))
        if eval_status == "failing":
            findings.append(finding(
                name, "s2_eval_failing", "HIGH",
                "eval_status=failing — skill is producing incorrect outputs",
                "Investigate and fix failing evals before next release",
            ))

    return findings


# ─────────────────────────────────────────────
# S3: Skill conflict drift
# ─────────────────────────────────────────────

def check_s3_conflict_drift(registry: list[dict]) -> list[dict]:
    findings = []
    approved = [s for s in registry if s.get("status") in ("approved", "submitted", "restricted")]

    for i, skill_a in enumerate(approved):
        for skill_b in approved[i + 1:]:
            name_a = skill_a.get("skill_name", "")
            name_b = skill_b.get("skill_name", "")
            sim = _jaccard(
                skill_a.get("purpose", ""),
                skill_b.get("purpose", ""),
            )
            if sim > 0.65:
                findings.append(finding(
                    name_a, "s3_overlap_candidate", "HIGH",
                    f"High description similarity with '{name_b}' (Jaccard={sim:.2f})",
                    "Review both skills — consider merging or explicitly differentiating scope",
                ))
            elif sim > 0.45:
                findings.append(finding(
                    name_a, "s3_overlap_candidate", "WARNING",
                    f"Moderate description similarity with '{name_b}' (Jaccard={sim:.2f})",
                    "Verify these skills have clearly distinct trigger conditions",
                ))

    scope_families: dict[str, list[str]] = {}
    for skill in approved:
        scope = skill.get("bundle_scope", "other")
        scope_families.setdefault(scope, []).append(skill.get("skill_name", ""))
    for scope, names in scope_families.items():
        prefixes: dict[str, list[str]] = {}
        for n in names:
            prefix = n.split("-")[0] if "-" in n else n
            prefixes.setdefault(prefix, []).append(n)
        for prefix, group in prefixes.items():
            if len(group) >= 5:
                findings.append(finding(
                    scope, "s3_family_overload", "WARNING",
                    f"Naming family '{prefix}-*' in scope '{scope}' has {len(group)} skills",
                    "Consider consolidating or using sub-scopes",
                ))

    return findings


# ─────────────────────────────────────────────
# S4: Skill lifecycle
# ─────────────────────────────────────────────

def check_s4_lifecycle(registry: list[dict]) -> list[dict]:
    findings = []
    for skill in registry:
        name = skill.get("skill_name", "<unknown>")
        status = skill.get("status", "")
        risk_level = skill.get("risk_level", "L1")
        eval_status = skill.get("eval_status", "pending")
        security_review = skill.get("security_review", "not_required")
        last_reviewed = skill.get("last_reviewed", "")

        if status == "retired":
            continue

        days = _days_since(last_reviewed) if last_reviewed else None

        if days is not None and days > REVIEW_OVERDUE_DAYS:
            findings.append(finding(
                name, "s4_review_overdue", "WARNING",
                f"Skill not reviewed in {days} days (threshold: {REVIEW_OVERDUE_DAYS})",
                "Schedule a governance review and update last_reviewed",
            ))

        if risk_level == "L4" and security_review == "pending":
            sec_days = days if days is not None else SECURITY_OVERDUE_DAYS + 1
            if sec_days > SECURITY_OVERDUE_DAYS:
                findings.append(finding(
                    name, "s4_security_review_overdue", "CRITICAL",
                    f"L4 skill has security_review=pending for {sec_days} days",
                    "Escalate to security team — L4 skills require approved security review",
                ))

        if eval_status == "failing" and days is not None and days > DEPRECATED_CANDIDATE_DAYS and status == "approved":
            findings.append(finding(
                name, "s4_deprecated_candidate", "HIGH",
                f"Skill has eval_status=failing and no review in {days} days — candidate for deprecation",
                "Fix evals + update last_reviewed, or set status: deprecated",
            ))

        if status == "approved" and days is not None and days > 365:
            findings.append(finding(
                name, "s4_stale_approved", "WARNING",
                f"Skill approved but not reviewed in over a year ({days} days)",
                "Perform yearly review — verify skill is still relevant and functional",
            ))

    return findings


# ─────────────────────────────────────────────
# T1: Tool repo consistency
# ─────────────────────────────────────────────

def check_t1_tool_repo_consistency(
    fs_tools: list[dict],
    tool_registry: list[dict],
) -> list[dict]:
    findings = []
    reg_names = {t["tool_name"] for t in tool_registry}
    fs_dir_names = {t["dir_name"] for t in fs_tools}

    for rname in reg_names:
        if rname not in fs_dir_names:
            reg_entry = next((t for t in tool_registry if t["tool_name"] == rname), {})
            path = reg_entry.get("path", "?")
            findings.append(finding(
                rname, "t1_missing_in_fs", "HIGH",
                f"Tool '{rname}' is in tool-registry (path: {path}) "
                "but no TOOL.md found in filesystem",
                "Create the TOOL.md file or remove the registry entry",
                asset_type="tool",
            ))

    for fs in fs_tools:
        dname = fs["dir_name"]
        if dname not in reg_names:
            findings.append(finding(
                dname, "t1_missing_in_registry", "WARNING",
                f"Directory '{dname}' has a TOOL.md but is not in tool-registry.yaml",
                "Register this tool with status: draft, or remove the TOOL.md",
                asset_type="tool",
            ))

    # Name drift: TOOL.md tool_name vs. registry tool_name
    for fs in fs_tools:
        fm = try_read_frontmatter(fs["path"])
        if fm is None:
            continue
        reg_entry = next(
            (t for t in tool_registry if t["tool_name"] == fs["dir_name"]), None
        )
        if reg_entry is None:
            continue
        fm_name = fm.get("tool_name", "")
        if fm_name and fm_name != reg_entry["tool_name"]:
            findings.append(finding(
                reg_entry["tool_name"], "t1_metadata_drift", "WARNING",
                f"TOOL.md tool_name '{fm_name}' differs from registry tool_name '{reg_entry['tool_name']}'",
                "Align the tool_name field in TOOL.md with tool_name in tool-registry.yaml",
                asset_type="tool",
            ))

    return findings


# ─────────────────────────────────────────────
# T2: Tool metadata health
# ─────────────────────────────────────────────

def check_t2_tool_metadata_health(tool_registry: list[dict]) -> list[dict]:
    findings = []
    for tool in tool_registry:
        name = tool.get("tool_name", "<unknown>")

        for field in REQUIRED_TOOL_FIELDS:
            if not tool.get(field):
                findings.append(finding(
                    name, "t2_missing_fields", "HIGH",
                    f"Required tool registry field '{field}' is missing or empty",
                    f"Add '{field}' to the tool's registry entry",
                    asset_type="tool",
                ))

        # Naming: kebab-case verb-noun
        if name and not NAME_PATTERN.match(name):
            findings.append(finding(
                name, "t2_naming_violation", "WARNING",
                f"tool_name '{name}' violates naming convention (kebab-case verb-noun)",
                "Rename to match pattern: all-lowercase, hyphens, verb-noun format",
                asset_type="tool",
            ))

        # Category validity
        category = tool.get("category", "")
        if category and category not in VALID_TOOL_CATEGORIES:
            findings.append(finding(
                name, "t2_invalid_category", "WARNING",
                f"category '{category}' is not in valid set: {', '.join(sorted(VALID_TOOL_CATEGORIES))}",
                "Set category to one of the valid tool categories",
                asset_type="tool",
            ))

        # Risk level validity
        risk_level = str(tool.get("risk_level", "")).upper()
        if risk_level and risk_level not in VALID_RISK_LEVELS:
            findings.append(finding(
                name, "t2_invalid_risk", "HIGH",
                f"risk_level '{risk_level}' is not valid. Must be L0–L4.",
                "Set risk_level to L0, L1, L2, L3, or L4",
                asset_type="tool",
            ))

        # Risk + side_effects consistency
        side_effects = str(tool.get("side_effects", "")).lower()
        if risk_level in RISK_SIDE_EFFECTS_MATRIX:
            expected = RISK_SIDE_EFFECTS_MATRIX[risk_level]
            if side_effects and side_effects != expected:
                findings.append(finding(
                    name, "t2_risk_mismatch", "HIGH",
                    f"risk_level {risk_level} requires side_effects: '{expected}', "
                    f"but registry declares '{side_effects}'",
                    "Align risk_level and side_effects per the platform risk matrix",
                    asset_type="tool",
                ))

        # Status validity
        status = tool.get("status", "")
        if status and status not in VALID_STATUSES:
            findings.append(finding(
                name, "t2_invalid_status", "WARNING",
                f"status '{status}' is not a valid lifecycle state",
                f"Set status to one of: {', '.join(sorted(VALID_STATUSES))}",
                asset_type="tool",
            ))

    return findings


# ─────────────────────────────────────────────
# T3: Tool lifecycle
# ─────────────────────────────────────────────

def check_t3_tool_lifecycle(tool_registry: list[dict]) -> list[dict]:
    findings = []
    for tool in tool_registry:
        name = tool.get("tool_name", "<unknown>")
        status = tool.get("status", "")
        risk_level = str(tool.get("risk_level", "L0")).upper()
        last_reviewed = tool.get("last_reviewed", "")

        if status in ("retired",):
            continue

        days = _days_since(last_reviewed) if last_reviewed else None

        # General review cadence
        if days is not None and days > REVIEW_OVERDUE_DAYS:
            findings.append(finding(
                name, "t3_review_overdue", "WARNING",
                f"Tool not reviewed in {days} days (threshold: {REVIEW_OVERDUE_DAYS})",
                "Schedule a tool governance review and update last_reviewed",
                asset_type="tool",
            ))

        # L3/L4 tools require more frequent review (side effects / external actions)
        if risk_level in ("L3", "L4"):
            threshold = TOOL_L34_REVIEW_DAYS
            if days is not None and days > threshold:
                severity = "CRITICAL" if risk_level == "L4" else "HIGH"
                findings.append(finding(
                    name, "t3_high_risk_review_overdue", severity,
                    f"{risk_level} tool has not been reviewed in {days} days "
                    f"(threshold for {risk_level}: {threshold} days). "
                    f"Side effects: {tool.get('side_effects', '?')}",
                    f"Perform an immediate risk review for this {risk_level} tool",
                    asset_type="tool",
                ))

        # Stale approved tool
        if status == "approved" and days is not None and days > 365:
            findings.append(finding(
                name, "t3_stale_approved", "WARNING",
                f"Tool approved but not reviewed in over a year ({days} days)",
                "Perform yearly review — verify tool schema and implementation are still current",
                asset_type="tool",
            ))

    return findings


# ─────────────────────────────────────────────
# T4: Consumer integrity
# ─────────────────────────────────────────────

def check_t4_consumer_integrity(
    tool_registry: list[dict],
    skill_registry: list[dict],
) -> list[dict]:
    """
    Checks that tools' declared consumers (called_by_skills) are valid.
    Also flags tools with zero or single consumers.
    """
    findings = []
    skill_names = {s["skill_name"] for s in skill_registry}
    active_skills = {s["skill_name"] for s in skill_registry
                     if s.get("status") not in ("deprecated", "retired")}
    deprecated_skills = {s["skill_name"] for s in skill_registry
                         if s.get("status") == "deprecated"}

    for tool in tool_registry:
        name = tool.get("tool_name", "<unknown>")
        status = tool.get("status", "")

        if status in ("deprecated", "retired"):
            continue

        # Get called_by_skills (may be list or missing in registry-only data)
        called_by = tool.get("called_by_skills", [])
        if not isinstance(called_by, list):
            called_by = []
        called_by = [s for s in called_by if s and str(s).strip()]

        if len(called_by) == 0:
            findings.append(finding(
                name, "t4_no_consumers", "HIGH",
                "Tool has no declared consumers in called_by_skills. "
                "Tools with no consumers are dead weight — consider retiring or demoting to workflow_step.",
                "Add consuming skills to called_by_skills, or set status: deprecated",
                asset_type="tool",
            ))
        elif len(called_by) == 1:
            findings.append(finding(
                name, "t4_single_consumer", "WARNING",
                f"Tool has only 1 consumer: '{called_by[0]}'. "
                "Single-consumer tools may be premature abstractions — "
                "consider demoting to workflow_step inside that skill.",
                "Verify reuse plan or annotate TOOL.md with planned future consumers",
                asset_type="tool",
            ))

        # Validate each consumer reference
        for consumer in called_by:
            if consumer not in skill_names:
                findings.append(finding(
                    name, "t4_unknown_consumer", "HIGH",
                    f"called_by_skills references '{consumer}' which does not exist in skill-registry.yaml",
                    f"Remove '{consumer}' from called_by_skills or register the skill",
                    asset_type="tool",
                ))
            elif consumer in deprecated_skills:
                findings.append(finding(
                    name, "t4_deprecated_consumer", "WARNING",
                    f"called_by_skills references '{consumer}' which is deprecated. "
                    "The tool may have no active consumers.",
                    f"Update called_by_skills to remove '{consumer}' or add replacement skills",
                    asset_type="tool",
                ))

    return findings


# ─────────────────────────────────────────────
# X1: Skills referencing non-existent tools
# ─────────────────────────────────────────────

def check_x1_dead_tool_references(
    fs_skills: list[dict],
    tool_registry: list[dict],
    skill_registry: list[dict],
) -> list[dict]:
    """
    Scan all SKILL.md bodies for MCP tool calls (server:tool_name()).
    Flag calls to tools not present in tool-registry.yaml.
    """
    findings = []
    registered_tools = {t["tool_name"].replace("-", "_"): t for t in tool_registry}
    # Also index by original kebab-case name
    registered_tools_kebab = {t["tool_name"]: t for t in tool_registry}

    for fs in fs_skills:
        skill_name = fs["dir_name"]
        # Check if this is a meta_skill (exempt from tool compliance)
        fm = try_read_frontmatter(fs["path"])
        if fm and str(fm.get("meta_skill", "")).lower() == "true":
            continue

        body = read_skill_body(fs["path"])
        if not body:
            continue

        tool_calls = MCP_CALL_PATTERN.findall(body)
        for server, tool_fn in tool_calls:
            # tool_fn uses underscores in call syntax; tool_name in registry uses hyphens
            tool_name_kebab = tool_fn.replace("_", "-")
            tool_found = (
                tool_fn in registered_tools
                or tool_name_kebab in registered_tools_kebab
            )
            if not tool_found:
                findings.append(finding(
                    skill_name, "x1_dead_tool_reference", "HIGH",
                    f"Skill calls '{server}:{tool_fn}()' but tool '{tool_name_kebab}' "
                    "is not found in tool-registry.yaml",
                    f"Register tool '{tool_name_kebab}' in tool-registry.yaml or "
                    "remove the call from the skill",
                ))

    return findings


# ─────────────────────────────────────────────
# X2: Skills referencing deprecated/retired tools
# ─────────────────────────────────────────────

def check_x2_deprecated_tool_usage(
    fs_skills: list[dict],
    tool_registry: list[dict],
) -> list[dict]:
    """
    Flag skills that call tools with status deprecated or retired.
    """
    findings = []
    deprecated_tools = {
        t["tool_name"].replace("-", "_"): t
        for t in tool_registry
        if t.get("status") in ("deprecated", "retired")
    }
    deprecated_tools_kebab = {
        t["tool_name"]: t
        for t in tool_registry
        if t.get("status") in ("deprecated", "retired")
    }

    if not deprecated_tools:
        return findings

    for fs in fs_skills:
        skill_name = fs["dir_name"]
        fm = try_read_frontmatter(fs["path"])
        if fm and str(fm.get("meta_skill", "")).lower() == "true":
            continue

        body = read_skill_body(fs["path"])
        if not body:
            continue

        tool_calls = MCP_CALL_PATTERN.findall(body)
        for server, tool_fn in tool_calls:
            tool_name_kebab = tool_fn.replace("_", "-")
            matched_tool = (
                deprecated_tools.get(tool_fn)
                or deprecated_tools_kebab.get(tool_name_kebab)
            )
            if matched_tool:
                dep_status = matched_tool.get("status", "deprecated")
                findings.append(finding(
                    skill_name, "x2_deprecated_tool_usage", "HIGH",
                    f"Skill calls '{server}:{tool_fn}()' but tool '{tool_name_kebab}' "
                    f"has status: {dep_status}",
                    f"Update skill to use the replacement tool, or remove the call. "
                    "Check tool-registry.yaml for a replacement.",
                ))

    return findings


# ─────────────────────────────────────────────
# X3: Tools with orphaned or deprecated skill consumers
# ─────────────────────────────────────────────

def check_x3_orphaned_consumer_refs(
    tool_registry: list[dict],
    skill_registry: list[dict],
) -> list[dict]:
    """
    For each tool's called_by_skills, check that consuming skills:
    - Still exist in skill-registry.yaml
    - Have compatible risk level (skill risk >= tool risk)
    """
    findings = []
    skill_map = {s["skill_name"]: s for s in skill_registry}

    RISK_ORDER = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}

    for tool in tool_registry:
        name = tool.get("tool_name", "<unknown>")
        tool_risk = str(tool.get("risk_level", "L0")).upper()
        tool_risk_rank = RISK_ORDER.get(tool_risk, 0)

        called_by = tool.get("called_by_skills", [])
        if not isinstance(called_by, list):
            called_by = []

        for consumer_name in called_by:
            if not consumer_name or not str(consumer_name).strip():
                continue
            skill = skill_map.get(consumer_name)
            if skill is None:
                # Already flagged in T4 — skip duplicate
                continue

            # Risk inheritance: a skill calling an L4 tool should be L4 itself
            skill_risk = str(skill.get("risk_level", "L1")).upper()
            skill_risk_rank = RISK_ORDER.get(skill_risk, 1)

            if tool_risk_rank > skill_risk_rank:
                findings.append(finding(
                    name, "x3_risk_inheritance_gap", "HIGH",
                    f"Tool '{name}' is {tool_risk} but consuming skill '{consumer_name}' "
                    f"is only declared as {skill_risk}. "
                    "Skill risk_level must be >= the risk level of its highest-risk tool.",
                    f"Raise '{consumer_name}' risk_level to at least {tool_risk} in skill-registry.yaml",
                    asset_type="cross",
                ))

    return findings


# ─────────────────────────────────────────────
# Timestamp updater
# ─────────────────────────────────────────────

def update_registry_timestamp(registry_path: Path) -> None:
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

    counts = {"INFO": 0, "WARNING": 0, "HIGH": 0, "CRITICAL": 0}
    asset_counts: dict[str, int] = {"skill": 0, "tool": 0, "cross": 0}
    codes: dict[str, int] = {}

    for f in findings:
        sev = f.get("severity", "INFO")
        counts[sev] = counts.get(sev, 0) + 1
        atype = f.get("asset_type", "skill")
        asset_counts[atype] = asset_counts.get(atype, 0) + 1
        codes[f["code"]] = codes.get(f["code"], 0) + 1

    report = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_findings": len(findings),
            "by_severity": counts,
            "by_asset_type": asset_counts,
            "by_code": codes,
        },
        "findings": findings,
    }

    report_path = output_dir / f"governance_report_{today}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    queue_findings = [f for f in findings if f.get("severity") in ("HIGH", "CRITICAL")]
    queue = {
        "generated_at": datetime.now().isoformat(),
        "requires_human_action": len(queue_findings),
        "queue": queue_findings,
    }
    queue_path = output_dir / "manual_review_queue.json"
    with open(queue_path, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)

    print(f"Report written:  {report_path}")
    print(f"Review queue:    {queue_path}")
    print(
        f"Summary: {len(findings)} findings — "
        f"{counts['CRITICAL']} CRITICAL, {counts['HIGH']} HIGH, "
        f"{counts['WARNING']} WARNING, {counts['INFO']} INFO"
    )
    print(
        f"By asset type:   skill={asset_counts['skill']}, "
        f"tool={asset_counts['tool']}, cross-track={asset_counts['cross']}"
    )


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dual-Track Registry Governance Audit (Phase 5)"
    )
    parser.add_argument(
        "--registry", default="skill-registry.yaml",
        help="Path to skill-registry.yaml (default: skill-registry.yaml)",
    )
    parser.add_argument(
        "--tool-registry", default="tool-registry.yaml",
        dest="tool_registry",
        help="Path to tool-registry.yaml (default: tool-registry.yaml)",
    )
    parser.add_argument(
        "--skills-root", default=".",
        help="Root directory to scan for SKILL.md and TOOL.md files",
    )
    parser.add_argument(
        "--output", default="reports",
        help="Output directory for reports",
    )
    parser.add_argument(
        "--update-timestamp", action="store_true",
        help="Auto-update last_audited in skill-registry.yaml and tool-registry.yaml",
    )
    parser.add_argument(
        "--skills-only", action="store_true",
        help="Run only skill checks (S1–S4), skip tool and cross-track checks",
    )
    args = parser.parse_args()

    registry_path = Path(args.registry)
    tool_registry_path = Path(args.tool_registry)
    skills_root = Path(args.skills_root)
    output_dir = Path(args.output)

    if not registry_path.exists():
        print(f"ERROR: Skill registry not found: {registry_path}", file=sys.stderr)
        return 2

    skill_registry = load_skill_registry(registry_path)
    if not skill_registry:
        print("ERROR: Skill registry is empty or could not be loaded", file=sys.stderr)
        return 2

    fs_skills = discover_skill_files(skills_root)
    print(f"Skill registry:  {len(skill_registry)} entries | {len(fs_skills)} SKILL.md files found")

    # Load tool registry if available
    tool_registry: list[dict] = []
    fs_tools: list[dict] = []
    has_tool_registry = tool_registry_path.exists() and not args.skills_only
    if has_tool_registry:
        tool_registry = load_tool_registry(tool_registry_path)
        fs_tools = discover_tool_files(skills_root)
        print(f"Tool registry:   {len(tool_registry)} entries | {len(fs_tools)} TOOL.md files found")
    else:
        if not args.skills_only:
            print(f"NOTE: tool-registry.yaml not found at '{tool_registry_path}' — skipping tool checks")

    print("Running governance checks...")

    all_findings: list[dict] = []

    # Skill checks (always run)
    all_findings.extend(check_s1_repo_consistency(fs_skills, skill_registry))
    all_findings.extend(check_s2_metadata_health(skill_registry))
    all_findings.extend(check_s3_conflict_drift(skill_registry))
    all_findings.extend(check_s4_lifecycle(skill_registry))
    print(f"  S1-S4 (skill):  {len(all_findings)} findings so far")

    if has_tool_registry:
        tool_start = len(all_findings)
        all_findings.extend(check_t1_tool_repo_consistency(fs_tools, tool_registry))
        all_findings.extend(check_t2_tool_metadata_health(tool_registry))
        all_findings.extend(check_t3_tool_lifecycle(tool_registry))
        all_findings.extend(check_t4_consumer_integrity(tool_registry, skill_registry))
        print(f"  T1-T4 (tool):   {len(all_findings) - tool_start} findings")

        cross_start = len(all_findings)
        all_findings.extend(check_x1_dead_tool_references(fs_skills, tool_registry, skill_registry))
        all_findings.extend(check_x2_deprecated_tool_usage(fs_skills, tool_registry))
        all_findings.extend(check_x3_orphaned_consumer_refs(tool_registry, skill_registry))
        print(f"  X1-X3 (cross):  {len(all_findings) - cross_start} findings")

    write_reports(all_findings, output_dir)

    if args.update_timestamp:
        update_registry_timestamp(registry_path)
        print(f"Updated last_audited in {registry_path}")
        if has_tool_registry:
            update_registry_timestamp(tool_registry_path)
            print(f"Updated last_audited in {tool_registry_path}")

    has_critical = any(f.get("severity") in ("HIGH", "CRITICAL") for f in all_findings)
    return 1 if has_critical else 0


if __name__ == "__main__":
    sys.exit(main())
