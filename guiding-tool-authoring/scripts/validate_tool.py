#!/usr/bin/env python3
"""
validate_tool.py — Platform Tool Spec Validator
================================================
Validates a TOOL.md file against the platform's 5-dimension rubric.

Usage:
    python guiding-tool-authoring/scripts/validate_tool.py <path/to/TOOL.md>
    python guiding-tool-authoring/scripts/validate_tool.py <path/to/TOOL.md> --json

Scoring:
    5 dimensions × 10 points = 50 total
    ≥ 45  PASS       — approved as-is
    40-44 CONDITIONAL — required changes before merge
    < 40  FAIL       — major revision needed
"""

import sys
import re
import json
import argparse
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

VALID_CATEGORIES = {
    "parsing", "transformation", "validation",
    "execution", "retrieval", "computation",
}

VALID_RISK_LEVELS = {"L0", "L1", "L2", "L3", "L4"}

VALID_SIDE_EFFECTS = {"none", "read", "write", "external"}

VALID_IMPL_TYPES = {"mcp", "http", "internal"}

VALID_STATUSES = {"draft", "submitted", "approved", "deprecated", "retired"}

# Risk level ↔ side_effects consistency matrix
RISK_SIDE_EFFECTS_RULES = {
    "L0": {"none"},
    "L1": {"read"},
    "L2": {"read"},         # L2 may have LLM calls — side_effects still 'read'
    "L3": {"write"},
    "L4": {"write", "external"},
}

# Reverse: if side_effects is X, minimum risk level
MIN_RISK_FOR_SIDE_EFFECTS = {
    "none":     "L0",
    "read":     "L1",
    "write":    "L3",
    "external": "L4",
}

VAGUE_VERBS = {
    "handles", "processes", "deals with", "manages", "performs",
    "does", "works with", "takes care of",
}

NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]{1,46}[a-z0-9]$")
UPPER_SNAKE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]+$")

REQUIRED_TOP_KEYS = [
    "tool_name", "display_name", "description", "category",
    "risk", "ownership", "input_schema", "output_schema", "errors", "usage",
    "implementation",
]

REQUIRED_RISK_KEYS = ["level", "side_effects", "idempotent"]
REQUIRED_OWNERSHIP_KEYS = ["team", "service"]
REQUIRED_IMPL_KEYS = ["type", "endpoint"]
REQUIRED_USAGE_KEYS = ["when_to_use", "when_not_to_use"]


# ─────────────────────────────────────────────
# Parser
# ─────────────────────────────────────────────

def load_tool_md(path: Path) -> dict:
    """Load and parse a TOOL.md file (pure YAML or YAML with leading comment lines)."""
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raw = path.read_text(encoding="utf-8", errors="replace")

    # Strip leading comment lines before YAML
    lines = raw.splitlines()
    yaml_lines = [l for l in lines if not l.startswith("#") or ":" in l]
    content = "\n".join(yaml_lines)

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ValueError(f"YAML parse error: {e}")

    if not isinstance(data, dict):
        raise ValueError("TOOL.md must be a YAML mapping at the top level")

    return data


# ─────────────────────────────────────────────
# Dimension 1: Naming & Description (10 pts)
# ─────────────────────────────────────────────

def check_dim1_naming(data: dict) -> tuple[int, list]:
    score = 0
    issues = []

    name = data.get("tool_name", "")
    display = data.get("display_name", "")
    desc = str(data.get("description", "")).strip()

    # Tool name format
    if not name:
        issues.append("tool_name is missing")
    elif not NAME_PATTERN.match(name):
        issues.append(f"tool_name '{name}' must be kebab-case, 3-48 chars, letters/numbers/hyphens only")
    elif name in ("tool", "helper", "util", "handler", "processor", "resolver"):
        issues.append(f"tool_name '{name}' is too generic — add a domain-specific qualifier")
    else:
        score += 3

    # Display name
    if not display:
        issues.append("display_name is missing")
    else:
        score += 1

    # Description quality
    if not desc:
        issues.append("description is missing")
    elif len(desc) > 160:
        issues.append(f"description is {len(desc)} chars — should be ≤ 120 chars")
        score += 1
    else:
        score += 2
        # Check for vague verbs
        desc_lower = desc.lower()
        found_vague = [v for v in VAGUE_VERBS if v in desc_lower]
        if found_vague:
            issues.append(f"description contains vague verb(s): {found_vague} — be more specific")
            score -= 1
        # Check verb-noun pattern roughly
        if not any(desc_lower.startswith(v) for v in (
            "parses", "converts", "validates", "extracts", "serializes", "computes",
            "maps", "classifies", "identifies", "resolves", "assembles", "evaluates",
            "retrieves", "queries", "matches", "detects", "assigns", "builds",
            "generates", "transforms", "checks", "analyzes",
        )):
            issues.append("description should start with an action verb (parses, converts, validates, etc.)")

    # Verb-noun name pattern check
    verb_prefixes = (
        "parse-", "convert-", "validate-", "extract-", "serialize-", "compute-",
        "map-", "classify-", "identify-", "resolve-", "assemble-", "evaluate-",
        "retrieve-", "query-", "match-", "detect-", "assign-", "build-",
        "generate-", "transform-", "check-", "analyze-", "calculate-",
    )
    if name and not any(name.startswith(p) for p in verb_prefixes):
        issues.append(f"tool_name should follow verb-noun pattern: e.g. 'parse-intent', got '{name}'")
        score = max(0, score - 1)
    else:
        score += 2

    score = max(0, min(10, score))
    return score, issues


# ─────────────────────────────────────────────
# Dimension 2: Schema Integrity (10 pts)
# ─────────────────────────────────────────────

def check_dim2_schema(data: dict) -> tuple[int, list]:
    score = 0
    issues = []

    def check_schema_block(schema: dict, label: str) -> tuple[int, list]:
        s, i = 0, []
        if not isinstance(schema, dict):
            i.append(f"{label}: schema must be a YAML mapping")
            return 0, i
        if schema.get("type") != "object":
            i.append(f"{label}: top-level type must be 'object'")
        else:
            s += 1
        props = schema.get("properties")
        if not props or not isinstance(props, dict):
            i.append(f"{label}: 'properties' is missing or empty — every field must be declared")
        else:
            s += 1
            for field, spec in props.items():
                if not isinstance(spec, dict):
                    i.append(f"{label}.properties.{field}: field spec must be a mapping")
                    continue
                if "type" not in spec:
                    i.append(f"{label}.properties.{field}: missing 'type'")
                else:
                    s += 0  # counted later
                if "description" not in spec:
                    i.append(f"{label}.properties.{field}: missing 'description'")
            # Score based on completeness
            typed = sum(1 for f, sp in props.items()
                       if isinstance(sp, dict) and "type" in sp and "description" in sp)
            total = len(props)
            if total > 0:
                ratio = typed / total
                s += int(ratio * 2)   # 0-2 points for completeness
        return s, i

    in_schema = data.get("input_schema", {})
    out_schema = data.get("output_schema", {})

    in_score, in_issues = check_schema_block(in_schema, "input_schema")
    out_score, out_issues = check_schema_block(out_schema, "output_schema")

    issues.extend(in_issues)
    issues.extend(out_issues)
    score = in_score + out_score

    # Input required list
    if isinstance(in_schema, dict):
        required = in_schema.get("required")
        if required is None:
            issues.append("input_schema: 'required' list is missing (use [] if all optional)")
        else:
            score += 1

    # Output stability (at least 2 output fields)
    if isinstance(out_schema, dict):
        out_props = out_schema.get("properties", {})
        if len(out_props) < 1:
            issues.append("output_schema: must declare at least 1 output field")
        else:
            score += 1

    # No 'type: any'
    raw_str = str(data.get("input_schema", "")) + str(data.get("output_schema", ""))
    if "type: any" in raw_str or "'any'" in raw_str:
        issues.append("Schema uses 'type: any' — specify a concrete type instead")
        score = max(0, score - 2)

    score = max(0, min(10, score))
    return score, issues


# ─────────────────────────────────────────────
# Dimension 3: Risk & Safety (10 pts)
# ─────────────────────────────────────────────

def check_dim3_risk(data: dict) -> tuple[int, list]:
    score = 0
    issues = []

    risk = data.get("risk", {})
    if not isinstance(risk, dict):
        issues.append("risk block is missing or not a mapping")
        return 0, issues

    level = risk.get("level", "")
    side_fx = risk.get("side_effects", "")
    idempotent = risk.get("idempotent")
    requires_approval = risk.get("requires_approval", False)

    # Level valid
    if level not in VALID_RISK_LEVELS:
        issues.append(f"risk.level '{level}' is invalid — must be one of {sorted(VALID_RISK_LEVELS)}")
    else:
        score += 2

    # Side effects valid
    if side_fx not in VALID_SIDE_EFFECTS:
        issues.append(f"risk.side_effects '{side_fx}' is invalid — must be one of {sorted(VALID_SIDE_EFFECTS)}")
    else:
        score += 2

    # Consistency: risk level ↔ side_effects
    if level in VALID_RISK_LEVELS and side_fx in VALID_SIDE_EFFECTS:
        allowed = RISK_SIDE_EFFECTS_RULES.get(level, set())
        min_risk = MIN_RISK_FOR_SIDE_EFFECTS.get(side_fx, "L0")
        risk_order = ["L0", "L1", "L2", "L3", "L4"]

        if side_fx in ("write", "external") and risk_order.index(level) < risk_order.index("L3"):
            issues.append(
                f"Inconsistent risk: side_effects='{side_fx}' requires risk_level ≥ L3, got '{level}'"
            )
            score = max(0, score - 2)
        elif side_fx == "none" and level != "L0":
            issues.append(
                f"Inconsistent risk: side_effects='none' should have risk_level=L0, got '{level}'"
            )
        else:
            score += 2

    # Idempotent declared
    if idempotent is None:
        issues.append("risk.idempotent is missing — declare true or false")
    else:
        score += 1
        # Consistency: write + idempotent=true needs justification
        if side_fx in ("write", "external") and idempotent is True:
            issues.append(
                "risk.idempotent=true with write/external side_effects — "
                "add a note in implementation.notes explaining why this is safe"
            )

    # L3/L4 must have requires_approval
    if level in ("L3", "L4") and not requires_approval:
        issues.append(f"risk_level {level} tools MUST set requires_approval: true")
        score = max(0, score - 1)
    elif level in ("L3", "L4") and requires_approval:
        score += 1

    # L0 must have side_effects: none
    if level == "L0" and side_fx != "none":
        issues.append("L0 tools MUST have side_effects: none — they are pure computation")
        score = max(0, score - 1)

    score = max(0, min(10, score))
    return score, issues


# ─────────────────────────────────────────────
# Dimension 4: Error Contract (10 pts)
# ─────────────────────────────────────────────

def check_dim4_errors(data: dict) -> tuple[int, list]:
    score = 0
    issues = []

    errors = data.get("errors", [])
    if not isinstance(errors, list):
        issues.append("errors must be a list")
        return 0, issues

    if len(errors) == 0:
        issues.append("errors list is empty — define at least 2 error codes (input error + system error)")
        return 0, issues

    if len(errors) == 1:
        issues.append("Only 1 error defined — add at least a system-level error (e.g. EXECUTION_FAILED)")
        score += 2
    else:
        score += 4  # 2+ errors base score

    for i, err in enumerate(errors):
        if not isinstance(err, dict):
            issues.append(f"errors[{i}]: error entry must be a mapping")
            continue

        code = err.get("code", "")
        message = err.get("message", "")
        retryable = err.get("retryable")

        if not code:
            issues.append(f"errors[{i}]: 'code' is missing")
        elif not UPPER_SNAKE_PATTERN.match(code):
            issues.append(f"errors[{i}].code '{code}': must be UPPER_SNAKE_CASE (e.g. INVALID_INPUT)")
        else:
            score += 1

        if not message:
            issues.append(f"errors[{i}]: 'message' is missing")
        elif len(str(message)) < 10:
            issues.append(f"errors[{i}].message is too short — must be human-readable")
        else:
            score += 1

        if retryable is None:
            issues.append(f"errors[{i}]: 'retryable' is missing — declare true or false")
        else:
            score += 1

    # Check for generic catch-all error
    codes = [str(e.get("code", "")) for e in errors if isinstance(e, dict)]
    if "ERROR" in codes or "UNKNOWN" in codes:
        issues.append("Avoid generic error codes like ERROR or UNKNOWN — be specific about what went wrong")
        score = max(0, score - 1)

    # Bonus: has both input and system errors
    has_input_err = any(
        "INPUT" in str(e.get("code", "")) or "INVALID" in str(e.get("code", "")) or "MISSING" in str(e.get("code", ""))
        for e in errors if isinstance(e, dict)
    )
    has_system_err = any(
        "FAILED" in str(e.get("code", "")) or "TIMEOUT" in str(e.get("code", "")) or "UNAVAILABLE" in str(e.get("code", ""))
        for e in errors if isinstance(e, dict)
    )
    if has_input_err and has_system_err:
        score += 2
    elif not has_input_err:
        issues.append("Missing input validation error (e.g. INVALID_INPUT, MISSING_REQUIRED_FIELD)")
    elif not has_system_err:
        issues.append("Missing system-level error (e.g. EXECUTION_FAILED, SERVICE_UNAVAILABLE, TIMEOUT)")

    score = max(0, min(10, score))
    return score, issues


# ─────────────────────────────────────────────
# Dimension 5: Atomicity & Reusability (10 pts)
# ─────────────────────────────────────────────

def check_dim5_atomicity(data: dict) -> tuple[int, list]:
    score = 0
    issues = []

    category = data.get("category", "")
    usage = data.get("usage", {})
    impl = data.get("implementation", {})
    desc = str(data.get("description", "")).lower()
    name = data.get("tool_name", "")
    ownership = data.get("ownership", {})

    # Category valid
    if category not in VALID_CATEGORIES:
        issues.append(f"category '{category}' is invalid — must be one of {sorted(VALID_CATEGORIES)}")
    else:
        score += 2

    # Multi-step detection (heuristic)
    multi_step_signals = [
        "then", "after", "next", "finally", "step", "sequence",
        "first", "second", "third", "pipeline",
    ]
    desc_signals = [s for s in multi_step_signals if s in desc]
    if len(desc_signals) >= 2:
        issues.append(
            f"Description hints at multi-step behavior ({desc_signals}) — "
            "tools must be atomic. Consider splitting into multiple tools or making this a skill."
        )
        score = max(0, score - 1)

    # Orchestration anti-pattern in name
    orchestration_names = ["orchestrate", "pipeline", "workflow", "process-all", "run-all"]
    if any(n in name for n in orchestration_names):
        issues.append(f"tool_name '{name}' suggests orchestration — tools must be atomic")
        score = max(0, score - 2)

    # Implementation defined
    impl_type = impl.get("type", "") if isinstance(impl, dict) else ""
    impl_endpoint = impl.get("endpoint", "") if isinstance(impl, dict) else ""

    if impl_type not in VALID_IMPL_TYPES:
        issues.append(f"implementation.type '{impl_type}' invalid — must be: mcp | http | internal")
    else:
        score += 2

    if not impl_endpoint:
        issues.append("implementation.endpoint is missing — specify the MCP call or HTTP endpoint")
    else:
        score += 1

    # Ownership defined
    team = ownership.get("team", "") if isinstance(ownership, dict) else ""
    service = ownership.get("service", "") if isinstance(ownership, dict) else ""

    if not team:
        issues.append("ownership.team is missing")
    else:
        score += 1

    if not service:
        issues.append("ownership.service is missing — specify which MCP server owns this tool")
    else:
        score += 1

    # Usage guidance
    if isinstance(usage, dict):
        when_use = usage.get("when_to_use", [])
        when_not = usage.get("when_not_to_use", [])
        called_by = usage.get("called_by_skills", [])

        if not when_use or len(when_use) == 0:
            issues.append("usage.when_to_use is empty — provide at least 1 concrete scenario")
        else:
            score += 1

        if not when_not or len(when_not) == 0:
            issues.append("usage.when_not_to_use is empty — describe at least 1 anti-pattern")

        if called_by:
            score += 1
        else:
            issues.append(
                "usage.called_by_skills is empty — list at least one skill that calls this tool "
                "(or mark as 'pending' if the calling skill is under development)"
            )
    else:
        issues.append("usage block is missing")

    score = max(0, min(10, score))
    return score, issues


# ─────────────────────────────────────────────
# Main validation
# ─────────────────────────────────────────────

def validate(path: Path) -> dict:
    try:
        data = load_tool_md(path)
    except Exception as e:
        return {
            "tool_name": path.stem,
            "score": 0,
            "result": "ERROR",
            "error": str(e),
            "blocking_issues": [str(e)],
            "warnings": [],
        }

    tool_name = data.get("tool_name", path.parent.name)

    # Check required top-level keys
    missing = [k for k in REQUIRED_TOP_KEYS if k not in data]
    if missing:
        blocking = [f"Required field missing: {k}" for k in missing]
        return {
            "tool_name": tool_name,
            "score": 0,
            "result": "FAIL",
            "blocking_issues": blocking,
            "warnings": [],
        }

    d1_score, d1_issues = check_dim1_naming(data)
    d2_score, d2_issues = check_dim2_schema(data)
    d3_score, d3_issues = check_dim3_risk(data)
    d4_score, d4_issues = check_dim4_errors(data)
    d5_score, d5_issues = check_dim5_atomicity(data)

    total = d1_score + d2_score + d3_score + d4_score + d5_score

    if total >= 45:
        result = "PASS"
    elif total >= 40:
        result = "PASS_WITH_REQUIRED_FIXES"
    else:
        result = "FAIL"

    # Collect blocking vs. warning issues
    # Any dimension at 0 is blocking
    blocking = []
    warnings = []

    dim_results = [
        ("1. Naming & Description", d1_score, d1_issues),
        ("2. Schema Integrity",     d2_score, d2_issues),
        ("3. Risk & Safety",        d3_score, d3_issues),
        ("4. Error Contract",       d4_score, d4_issues),
        ("5. Atomicity & Reusability", d5_score, d5_issues),
    ]

    for label, sc, iss in dim_results:
        for issue in iss:
            if sc == 0:
                blocking.append(f"[{label}] {issue}")
            else:
                warnings.append(f"[{label}] {issue}")

    return {
        "tool_name": tool_name,
        "score": total,
        "result": result,
        "dimensions": {
            "naming_description": d1_score,
            "schema_integrity": d2_score,
            "risk_safety": d3_score,
            "error_contract": d4_score,
            "atomicity_reusability": d5_score,
        },
        "blocking_issues": blocking,
        "warnings": warnings,
    }


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Validate a TOOL.md spec file")
    parser.add_argument("path", help="Path to TOOL.md file")
    parser.add_argument("--json", action="store_true", help="Output JSON result")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    result = validate(path)

    if args.json:
        print()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result["result"] in ("PASS", "PASS_WITH_REQUIRED_FIXES") else 1)

    # Human-readable output
    score = result["score"]
    tool_name = result["tool_name"]

    print()
    print("=" * 60)
    print(f"  Platform Tool Validator")
    print(f"  Tool: {tool_name}")
    print(f"  File: {path}")
    print("=" * 60)
    print()

    if result.get("error"):
        print(f"  PARSE ERROR: {result['error']}")
        sys.exit(1)

    dims = result.get("dimensions", {})
    dim_labels = [
        ("1. Naming & Description",    "naming_description"),
        ("2. Schema Integrity",        "schema_integrity"),
        ("3. Risk & Safety",           "risk_safety"),
        ("4. Error Contract",          "error_contract"),
        ("5. Atomicity & Reusability", "atomicity_reusability"),
    ]

    print(f"  {'Dimension':<35} {'Score':>5}   Issues")
    print(f"  {'-'*35} {'-'*5}   {'-'*20}")
    for label, key in dim_labels:
        sc = dims.get(key, 0)
        tag = "[OK]" if sc >= 8 else ("[!]" if sc == 0 else "[?]")
        print(f"  {label:<35} {sc:>3}/10   {tag}")

    print()
    print("-" * 60)

    if score >= 45:
        status = "[PASS] APPROVED"
    elif score >= 40:
        status = "[WARN] CONDITIONAL (required changes before merge)"
    else:
        status = "[FAIL] MAJOR REVISION REQUIRED"

    print(f"  Total: {score}/50    {status}")
    print("-" * 60)

    if result["blocking_issues"]:
        print()
        print("BLOCKING ISSUES (must fix before registration):")
        for issue in result["blocking_issues"]:
            print(f"  {issue}")

    if result["warnings"]:
        print()
        print("SUGGESTIONS (non-blocking):")
        for w in result["warnings"]:
            print(f"  {w}")

    print()

    # Also print JSON
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()

    sys.exit(0 if result["result"] in ("PASS", "PASS_WITH_REQUIRED_FIXES") else 1)


if __name__ == "__main__":
    main()
