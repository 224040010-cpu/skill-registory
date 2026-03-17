#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
admission_gate.py — Skill Admission Gate (Phase 4)

Evaluates whether a proposed skill should be admitted into the platform registry.
Performs five checks from the platform's perspective (not the author's perspective).

Usage:
    python admission_gate.py <path/to/SKILL.md> [--registry skill-registry.yaml]

Output:
    JSON to stdout:
    {
        "skill_name": "diagnosing-charger-faults",
        "decision": "PASS | PASS_WITH_WARNINGS | REQUIRES_REVIEW | REJECT",
        "reasons": ["..."],
        "recommended_actions": ["..."],
        "neighbor_skills": ["skill-a", "skill-b"]
    }

Exit codes:
    0 — PASS or PASS_WITH_WARNINGS
    1 — REQUIRES_REVIEW or REJECT
    2 — Parse/file error
"""

import sys
import re
import json
from pathlib import Path

# ─────────────────────────────────────────────
# Platform constants
# ─────────────────────────────────────────────

VALID_BUNDLE_SCOPES = {
    "diagnosis-agent",
    "customer-agent",
    "ops-agent",
    "energy-agent",
    "bpmn-agent",
    "platform",
}

# Keywords that suggest an agent's domain — used for cross-boundary detection
AGENT_DOMAIN_KEYWORDS = {
    "diagnosis-agent": ["fault", "diagnos", "hardware", "log", "charger", "error", "repair"],
    "customer-agent": ["customer", "billing", "session", "account", "user", "vehicle", "compatibility"],
    "ops-agent": ["fleet", "capacity", "energy", "maintenance", "knowledge", "rag", "index", "embed"],
    "energy-agent": ["energy", "consumption", "optimization", "power", "grid", "load"],
    "bpmn-agent": ["bpmn", "process", "workflow", "diagram", "entity", "intent", "xml"],
}

# Verbs in description/name that imply write operations (L3+)
WRITE_VERBS = [
    "creat", "dispatch", "send", "update", "modify", "delete",
    "generat", "submit", "assign", "schedule", "publish",
]

# Verbs that imply device control (L4)
CONTROL_VERBS = [
    "restart", "reboot", "stop charging", "disable", "unlock", "power limit",
    "control device", "set power", "force stop",
]

SKILL_CALLING_PATTERNS = [
    r"use\s+the\s+\S+-skill",
    r"call\s+the\s+\S+-skill",
    r"invoke\s+\S+-skill",
    r"trigger\s+\S+-skill",
]

VAGUE_ROUTING_WORDS = [
    "manages", "handles", "general", "various", "deals with",
    "helps with", "provides", "supports",
]


# ─────────────────────────────────────────────
# Parser (mirrors validate_skill.py parser)
# ─────────────────────────────────────────────

def parse_skill_md(path: Path) -> dict | None:
    """Parse SKILL.md into frontmatter + body. Returns None if binary/unreadable."""
    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None

    if not content.startswith("---"):
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    frontmatter_raw = parts[1].strip()
    body = parts[2].strip()

    frontmatter = {}
    current_key = None
    current_value_lines = []

    for line in frontmatter_raw.splitlines():
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

    return {"frontmatter": frontmatter, "body": body}


def load_registry(registry_path: Path) -> list[dict]:
    """Load skills from skill-registry.yaml. Returns list of skill dicts."""
    try:
        import yaml
        with open(registry_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("skills", [])
    except ImportError:
        # Fallback: minimal YAML parser for simple key:value structures
        return _load_registry_fallback(registry_path)
    except (OSError, Exception):
        return []


def _load_registry_fallback(registry_path: Path) -> list[dict]:
    """Minimal fallback registry loader without PyYAML dependency."""
    skills = []
    try:
        content = registry_path.read_text(encoding="utf-8")
    except OSError:
        return []

    current_skill: dict | None = None
    indent_base = 0

    for line in content.splitlines():
        stripped = line.strip()

        # Start of a new skill entry
        if stripped == "- skill_name:" or stripped.startswith("- skill_name:"):
            if current_skill:
                skills.append(current_skill)
            val = stripped.split(":", 1)[1].strip() if ":" in stripped else ""
            current_skill = {"skill_name": val}
            continue

        if current_skill is None:
            continue

        # Parse simple key: value lines within a skill block
        if stripped and ":" in stripped and not stripped.startswith("-"):
            key, _, val = stripped.partition(":")
            val = val.strip().strip('"').strip("'")
            current_skill[key.strip()] = val

    if current_skill:
        skills.append(current_skill)

    return skills


# ─────────────────────────────────────────────
# Similarity helpers
# ─────────────────────────────────────────────

def _edit_distance(a: str, b: str) -> int:
    """Levenshtein edit distance between two strings."""
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (ca != cb)))
        prev = curr
    return prev[-1]


def _jaccard(text_a: str, text_b: str) -> float:
    """Word-level Jaccard similarity between two strings."""
    words_a = set(re.findall(r"\b\w{3,}\b", text_a.lower()))
    words_b = set(re.findall(r"\b\w{3,}\b", text_b.lower()))
    if not words_a and not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


# ─────────────────────────────────────────────
# Five admission checks
# ─────────────────────────────────────────────

def check1_global_conflict(
    candidate: dict,
    registry: list[dict],
) -> tuple[str, list[str], list[str], list[str]]:
    """
    Check 1: Global conflict check.
    Detects name collisions, description overlap, and trigger phrase collisions.
    Returns (level, reasons, actions, neighbors).
    level: PASS | WARNING | REQUIRES_REVIEW | REJECT
    """
    reasons, actions, neighbors = [], [], []
    level = "PASS"

    cname = candidate["frontmatter"].get("name", "")
    cdesc = candidate["frontmatter"].get("description", "")

    for skill in registry:
        rname = skill.get("skill_name", "")
        rdesc = skill.get("purpose", "") or ""

        # Exact name match (self-check excluded via different path in caller)
        if rname == cname:
            reasons.append(f"Exact name collision with existing skill: '{rname}'")
            actions.append("Rename the skill — this name is already taken in the registry")
            level = "REJECT"
            continue

        # Near-name match (edit distance ≤ 2)
        if _edit_distance(cname, rname) <= 2 and rname != cname:
            reasons.append(f"Near-duplicate name: '{cname}' vs '{rname}' (edit distance ≤ 2)")
            actions.append(f"Consider renaming to avoid confusion with '{rname}'")
            neighbors.append(rname)
            if level not in ("REJECT", "REQUIRES_REVIEW"):
                level = "WARNING"

        # Description/purpose similarity
        sim = _jaccard(cdesc, rdesc)
        if sim > 0.65:
            reasons.append(
                f"High description similarity with '{rname}' (Jaccard={sim:.2f}) — "
                "possible duplicate or overlap"
            )
            actions.append(
                f"Compare with '{rname}' — if largely the same, merge or clearly differentiate scope"
            )
            neighbors.append(rname)
            if level not in ("REJECT",):
                level = "REQUIRES_REVIEW"
        elif sim > 0.45:
            reasons.append(
                f"Moderate description overlap with '{rname}' (Jaccard={sim:.2f})"
            )
            neighbors.append(rname)
            if level == "PASS":
                level = "WARNING"

    return level, reasons, actions, list(set(neighbors))


def check2_agent_boundary(candidate: dict) -> tuple[str, list[str], list[str]]:
    """
    Check 2: Agent boundary check.
    Validates bundle_scope and detects cross-agent contamination.
    """
    reasons, actions = [], []
    level = "PASS"

    fm = candidate["frontmatter"]
    desc = fm.get("description", "").lower()
    body = candidate["body"].lower()
    full_text = desc + " " + body

    # bundle_scope validation
    scope = fm.get("bundle_scope", "")
    if not scope:
        reasons.append("Missing bundle_scope in frontmatter")
        actions.append(f"Add bundle_scope. Valid values: {', '.join(sorted(VALID_BUNDLE_SCOPES))}")
        return "REJECT", reasons, actions

    if scope not in VALID_BUNDLE_SCOPES:
        reasons.append(f"Unknown bundle_scope '{scope}' — not in approved agent list")
        actions.append(f"Set bundle_scope to one of: {', '.join(sorted(VALID_BUNDLE_SCOPES))}")
        return "REJECT", reasons, actions

    # Cross-agent contamination: count how many agent domains are touched
    touched_agents = []
    for agent, keywords in AGENT_DOMAIN_KEYWORDS.items():
        if agent == scope:
            continue
        keyword_hits = sum(1 for kw in keywords if kw in full_text)
        if keyword_hits >= 3:
            touched_agents.append(agent)

    if len(touched_agents) >= 2:
        reasons.append(
            f"Skill text contains vocabulary from {len(touched_agents)} other agent domains "
            f"({', '.join(touched_agents)}) — suggests mixed responsibilities"
        )
        actions.append("Consider splitting into separate skills per agent boundary")
        level = "REQUIRES_REVIEW"
    elif len(touched_agents) == 1:
        reasons.append(
            f"Skill text contains vocabulary from '{touched_agents[0]}' domain — "
            "verify this is intentional"
        )
        if level == "PASS":
            level = "WARNING"

    return level, reasons, actions


def check3_risk_level(candidate: dict) -> tuple[str, list[str], list[str]]:
    """
    Check 3: Risk level accuracy check.
    Infers actual risk from description and body, compares to declared level.
    """
    reasons, actions = [], []
    level = "PASS"

    fm = candidate["frontmatter"]
    declared = fm.get("risk_level", "L1").upper()
    desc = fm.get("description", "").lower()
    body = candidate["body"].lower()
    full_text = desc + " " + body

    # Detect device control signals (L4)
    control_signals = [v for v in CONTROL_VERBS if v in full_text]
    has_verify_gate = "verify-gate-mcp:request_approval" in candidate["body"]

    if control_signals:
        if declared not in ("L4",):
            reasons.append(
                f"Device control vocabulary detected ({', '.join(control_signals[:3])}) "
                f"but declared risk_level is {declared} — should be L4"
            )
            actions.append("Raise risk_level to L4 and add verify-gate-mcp:request_approval step")
            return "REJECT", reasons, actions
        if not has_verify_gate:
            reasons.append("L4 skill is missing verify-gate-mcp:request_approval step")
            actions.append("Add Verify Gate step before any device control operation")
            return "REJECT", reasons, actions

    # Detect write operation signals (L3)
    write_signals = [v for v in WRITE_VERBS if v in full_text]
    if write_signals and declared in ("L1", "L2"):
        reasons.append(
            f"Write-operation vocabulary detected ({', '.join(write_signals[:3])}) "
            f"but declared risk_level is {declared} — should be L3 or higher"
        )
        actions.append("Raise risk_level to L3 if this skill creates/modifies records")
        level = "REQUIRES_REVIEW"

    # L4 declared but no control vocabulary
    if declared == "L4" and not control_signals:
        reasons.append(
            "risk_level declared as L4 but no device control vocabulary found — "
            "may be over-classified"
        )
        actions.append("Review whether L3 is sufficient; L4 implies direct device operations")
        if level == "PASS":
            level = "WARNING"

    return level, reasons, actions


def check4_routing_governance(candidate: dict) -> tuple[str, list[str], list[str]]:
    """
    Check 4: Routing governance check.
    Ensures the description won't pollute the skill router or cause mis-triggers.
    """
    reasons, actions = [], []
    level = "PASS"

    desc = candidate["frontmatter"].get("description", "")

    # Description too short
    if len(desc.strip()) < 40:
        reasons.append(
            f"Description is very short ({len(desc.strip())} chars) — "
            "router needs at least ~40 characters for accurate routing"
        )
        actions.append("Expand description to include 'Use when' and 'Do NOT use when' clauses")
        level = "WARNING"

    # Missing Use when clause
    if "use when" not in desc.lower():
        reasons.append("Description missing 'Use when' clause — routing accuracy will be low")
        actions.append("Add 'Use when [specific trigger condition]' to the description")
        if level == "PASS":
            level = "WARNING"

    # Vague routing words
    vague_found = [w for w in VAGUE_ROUTING_WORDS if w in desc.lower()]
    if vague_found:
        reasons.append(
            f"Description contains routing-unfriendly vague terms: {', '.join(vague_found)}"
        )
        actions.append("Replace vague terms with specific trigger conditions")
        if level == "PASS":
            level = "WARNING"

    # Description looks like it covers everything (too broad)
    broad_signals = ["all", "any", "everything", "whenever", "always", "any request"]
    broad_found = [s for s in broad_signals if s in desc.lower()]
    if len(broad_found) >= 2:
        reasons.append(
            f"Description appears overly broad ({', '.join(broad_found)}) — "
            "may capture too many intents and create routing noise"
        )
        actions.append("Narrow the scope: add explicit exclusion clauses")
        if level not in ("REJECT", "REQUIRES_REVIEW"):
            level = "REQUIRES_REVIEW"

    return level, reasons, actions


def check5_form_factor(candidate: dict) -> tuple[str, list[str], list[str]]:
    """
    Check 5: Form factor check.
    Determines whether this is truly a Skill, or should be a Tool / sub-step / merged skill.
    """
    reasons, actions = [], []
    level = "PASS"

    body = candidate["body"]

    # Detect skill-calling (orchestration belongs at Agent layer, not Skill layer)
    for pattern in SKILL_CALLING_PATTERNS:
        if re.search(pattern, body, re.IGNORECASE):
            reasons.append(
                "Skill calls or references other skills — "
                "skills must be leaf nodes; orchestration belongs at the Agent/Workflow layer"
            )
            actions.append(
                "Remove inter-skill calls; if orchestration is needed, "
                "implement it in the Agent workflow, not in this skill"
            )
            return "REJECT", reasons, actions

    # Very few workflow steps with no error handling → may be a Tool, not a Skill
    step_count = len(re.findall(r"\[\s*\]\s*Step\s*\d+", body))
    has_error_path = bool(re.search(
        r"(error|fail|not found|exception|if .* → |else)", body, re.IGNORECASE
    ))
    if step_count <= 2 and not has_error_path:
        reasons.append(
            f"Skill has only {step_count} step(s) and no error handling — "
            "this may be more suitable as an MCP Tool rather than a Skill"
        )
        actions.append(
            "If this is a single atomic operation, consider registering it as an MCP Tool instead"
        )
        if level == "PASS":
            level = "WARNING"

    # Check for conjunction overload (multiple responsibilities)
    desc = candidate["frontmatter"].get("description", "")
    conjunctions = ["and also", "as well as", "additionally", "furthermore", "moreover"]
    conj_found = [c for c in conjunctions if c in desc.lower()]
    if conj_found:
        reasons.append(
            f"Description uses conjunction overload ({', '.join(conj_found)}) — "
            "indicates multiple responsibilities"
        )
        actions.append("Split into two focused skills, one responsibility each")
        if level not in ("REJECT",):
            level = "REQUIRES_REVIEW"

    return level, reasons, actions


# ─────────────────────────────────────────────
# Decision aggregation
# ─────────────────────────────────────────────

_LEVEL_RANK = {"PASS": 0, "WARNING": 1, "REQUIRES_REVIEW": 2, "REJECT": 3}


def _aggregate(*levels: str) -> str:
    """Return the highest-severity level from a list."""
    return max(levels, key=lambda l: _LEVEL_RANK.get(l, 0))


def _level_to_decision(level: str) -> str:
    if level == "PASS":
        return "PASS"
    if level == "WARNING":
        return "PASS_WITH_WARNINGS"
    if level == "REQUIRES_REVIEW":
        return "REQUIRES_REVIEW"
    return "REJECT"


# ─────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────

def run_admission(skill_path: str, registry_path: str = "skill-registry.yaml") -> int:
    path = Path(skill_path)
    if not path.exists():
        print(json.dumps({"error": f"File not found: {skill_path}"}))
        return 2

    parsed = parse_skill_md(path)
    if parsed is None:
        print(json.dumps({
            "error": (
                f"Could not parse {skill_path} as UTF-8 text. "
                "The file may be encrypted or binary."
            )
        }))
        return 2

    registry = load_registry(Path(registry_path))
    skill_name = parsed["frontmatter"].get("name", path.parent.name)

    # Remove self from registry comparison (re-admission scenario)
    registry_others = [s for s in registry if s.get("skill_name") != skill_name]

    # Run five checks
    lvl1, reasons1, actions1, neighbors = check1_global_conflict(parsed, registry_others)
    lvl2, reasons2, actions2 = check2_agent_boundary(parsed)
    lvl3, reasons3, actions3 = check3_risk_level(parsed)
    lvl4, reasons4, actions4 = check4_routing_governance(parsed)
    lvl5, reasons5, actions5 = check5_form_factor(parsed)

    overall_level = _aggregate(lvl1, lvl2, lvl3, lvl4, lvl5)
    decision = _level_to_decision(overall_level)

    all_reasons = reasons1 + reasons2 + reasons3 + reasons4 + reasons5
    all_actions = actions1 + actions2 + actions3 + actions4 + actions5

    result = {
        "skill_name": skill_name,
        "decision": decision,
        "reasons": all_reasons,
        "recommended_actions": all_actions,
        "neighbor_skills": neighbors,
        "check_details": {
            "global_conflict": lvl1,
            "agent_boundary": lvl2,
            "risk_level": lvl3,
            "routing_governance": lvl4,
            "form_factor": lvl5,
        },
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if decision in ("PASS", "PASS_WITH_WARNINGS") else 1


if __name__ == "__main__":
    registry_arg = "skill-registry.yaml"
    skip_next = False
    positional = []
    for i, a in enumerate(sys.argv[1:], 1):
        if skip_next:
            skip_next = False
            continue
        if a == "--registry":
            if i + 1 < len(sys.argv):
                registry_arg = sys.argv[i + 1]
                skip_next = True
        elif not a.startswith("--"):
            positional.append(a)

    if len(positional) != 1:
        print(f"Usage: python {sys.argv[0]} <path/to/SKILL.md> [--registry skill-registry.yaml]")
        sys.exit(2)
    sys.exit(run_admission(positional[0], registry_arg))
