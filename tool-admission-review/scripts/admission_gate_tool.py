#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
admission_gate_tool.py — Tool Admission Gate (Phase 4T)

Evaluates whether a proposed tool should be admitted into the platform
tool registry. Performs five checks from the platform's perspective.

This gate answers: "Should this tool exist as a platform asset?"
(validate_tool.py already answered: "Is this tool spec well-formed?")

Usage:
    python admission_gate_tool.py <path/to/TOOL.md> [--registry tool-registry.yaml] [--json]

Output (JSON):
    {
        "tool_name": "parse-business-intent",
        "decision": "PASS | PASS_WITH_WARNINGS | REQUIRES_REVIEW | REJECT",
        "checks": {
            "check1_global_duplication": {...},
            "check2_service_assignment": {...},
            "check3_risk_consistency": {...},
            "check4_reuse_justifiability": {...},
            "check5_form_appropriateness": {...}
        },
        "reasons": ["..."],
        "recommended_actions": ["..."],
        "neighbor_tools": ["tool-a", "tool-b"]
    }

Exit codes:
    0 — PASS or PASS_WITH_WARNINGS
    1 — REQUIRES_REVIEW or REJECT
    2 — Parse/file error
"""

import sys
import io
import re
import json
import argparse
from pathlib import Path

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────
# Platform constants
# ─────────────────────────────────────────────

VALID_SERVICES = {
    "bpmn-tools",
    "diagnosis-tools",
    "customer-tools",
    "ops-tools",
    "energy-tools",
}

VALID_CATEGORIES = {
    "parsing", "transformation", "validation",
    "execution", "retrieval", "computation",
}

# Risk level → required side_effects value
RISK_SIDE_EFFECTS_MATRIX = {
    "L0": "none",
    "L1": "read",
    "L2": "read",
    "L3": "write",
    "L4": "external",
}

# Verbs / phrases that suggest orchestration (tool should be a skill or workflow_step)
ORCHESTRATION_INDICATORS = [
    "orchestrat", "coordinat", "manag", "sequenc", "pipeline",
    "first.*then.*finally", "step 1", "step 2", "multi-step",
    "workflow", "call.*tool", "invoke.*skill",
]

# Name suffixes that indicate a non-atomic role
NON_ATOMIC_SUFFIXES = [
    "manager", "handler", "coordinator", "orchestrator",
    "controller", "processor", "dispatcher", "supervisor",
]

# Similarity thresholds
NAME_EDIT_DISTANCE_REJECT = 2      # identical or near-identical name → REJECT
NAME_EDIT_DISTANCE_WARN = 4        # close name → WARNING
DESC_JACCARD_REVIEW = 0.65         # high description overlap → REQUIRES_REVIEW
SCHEMA_OVERLAP_REVIEW = 0.70       # high schema overlap → REQUIRES_REVIEW


# ─────────────────────────────────────────────
# TOOL.md parser
# ─────────────────────────────────────────────

def parse_tool_md(path: Path) -> dict | None:
    """
    Parse TOOL.md into structured data.
    TOOL.md is pure YAML (no '---' fences required, but tolerated).
    Returns None on parse failure.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None

    # Strip optional YAML fences
    if content.startswith("---"):
        parts = content.split("---", 2)
        yaml_body = parts[1] if len(parts) >= 2 else content
    else:
        yaml_body = content

    try:
        import yaml
        data = yaml.safe_load(yaml_body)
        if not isinstance(data, dict):
            return None
        return data
    except Exception:
        return _parse_tool_md_fallback(yaml_body)


def _parse_tool_md_fallback(yaml_body: str) -> dict | None:
    """Minimal key:value YAML parser (no PyYAML dependency)."""
    result: dict = {}
    current_key = None
    current_list: list | None = None
    indent_stack: list[tuple[int, str]] = []

    for line in yaml_body.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        if stripped.startswith("- ") and current_key:
            val = stripped[2:].strip().strip('"').strip("'")
            if isinstance(result.get(current_key), list):
                result[current_key].append(val)
            continue

        if ":" in stripped and not stripped.startswith("-"):
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val:
                result[key] = val
            else:
                result[key] = []
            current_key = key

    return result if result else None


# ─────────────────────────────────────────────
# Registry loader
# ─────────────────────────────────────────────

def load_tool_registry(registry_path: Path) -> list[dict]:
    """Load tools from tool-registry.yaml."""
    try:
        import yaml
        with open(registry_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("tools", [])
    except ImportError:
        return _load_registry_fallback(registry_path)
    except (OSError, Exception):
        return []


def _load_registry_fallback(registry_path: Path) -> list[dict]:
    tools = []
    try:
        content = registry_path.read_text(encoding="utf-8")
    except OSError:
        return []

    current_tool: dict | None = None
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("- tool_name:"):
            if current_tool:
                tools.append(current_tool)
            val = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            current_tool = {"tool_name": val}
            continue
        if current_tool and ":" in stripped and not stripped.startswith("-"):
            key, _, val = stripped.partition(":")
            current_tool[key.strip()] = val.strip().strip('"').strip("'")

    if current_tool:
        tools.append(current_tool)
    return tools


# ─────────────────────────────────────────────
# Similarity helpers
# ─────────────────────────────────────────────

def _edit_distance(a: str, b: str) -> int:
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
    words_a = set(re.findall(r"\b\w{3,}\b", text_a.lower()))
    words_b = set(re.findall(r"\b\w{3,}\b", text_b.lower()))
    if not words_a and not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def _schema_field_overlap(fields_a: list[str], fields_b: list[str]) -> float:
    """Jaccard similarity on field name sets."""
    if not fields_a and not fields_b:
        return 0.0
    set_a, set_b = set(fields_a), set(fields_b)
    return len(set_a & set_b) / len(set_a | set_b)


def _extract_input_fields(tool_data: dict) -> list[str]:
    schema = tool_data.get("input_schema", {})
    if isinstance(schema, dict):
        props = schema.get("properties", {})
        if isinstance(props, dict):
            return list(props.keys())
    return []


# ─────────────────────────────────────────────
# Check 1 — Global Duplication
# ─────────────────────────────────────────────

def check1_global_duplication(tool: dict, registry: list[dict]) -> dict:
    """
    Detect name or function duplication against the existing tool registry.
    - Exact name match or edit distance <= 2 → REJECT
    - Edit distance 3-4 → WARNING
    - Description Jaccard >= 0.65 → REQUIRES_REVIEW
    - Input schema field overlap >= 0.70 → REQUIRES_REVIEW
    """
    name = tool.get("tool_name", "")
    description = str(tool.get("description", ""))
    input_fields = _extract_input_fields(tool)

    result = {"status": "PASS", "findings": [], "neighbors": []}

    for existing in registry:
        ex_name = existing.get("tool_name", "")
        if ex_name == name:
            continue  # skip self if already registered

        # Name similarity
        dist = _edit_distance(name, ex_name)
        if dist <= NAME_EDIT_DISTANCE_REJECT:
            result["status"] = "REJECT"
            result["findings"].append(
                f"Name '{name}' is near-identical to existing tool '{ex_name}' "
                f"(edit distance {dist}). Use the existing tool or justify the difference."
            )
            result["neighbors"].append(ex_name)
            continue

        if dist <= NAME_EDIT_DISTANCE_WARN:
            if result["status"] == "PASS":
                result["status"] = "WARNING"
            result["findings"].append(
                f"Name '{name}' is similar to existing tool '{ex_name}' "
                f"(edit distance {dist}). Verify these are distinct capabilities."
            )
            result["neighbors"].append(ex_name)

        # Description similarity
        ex_desc = str(existing.get("description", existing.get("display_name", "")))
        desc_sim = _jaccard(description, ex_desc)
        if desc_sim >= DESC_JACCARD_REVIEW:
            if result["status"] not in ("REJECT",):
                result["status"] = "REQUIRES_REVIEW"
            result["findings"].append(
                f"Description overlap {desc_sim:.0%} with tool '{ex_name}'. "
                "These tools may be functionally equivalent — consider merging."
            )
            if ex_name not in result["neighbors"]:
                result["neighbors"].append(ex_name)

        # Schema overlap (requires TOOL.md data for existing tool — fallback to registry only)
        ex_fields = existing.get("_input_fields", [])
        if ex_fields and input_fields:
            overlap = _schema_field_overlap(input_fields, ex_fields)
            if overlap >= SCHEMA_OVERLAP_REVIEW:
                if result["status"] not in ("REJECT",):
                    result["status"] = "REQUIRES_REVIEW"
                result["findings"].append(
                    f"Input schema field overlap {overlap:.0%} with '{ex_name}'. "
                    "Confirm these tools process distinct inputs."
                )

    if not result["findings"]:
        result["findings"].append("No name or description conflicts found in registry.")

    return result


# ─────────────────────────────────────────────
# Check 2 — Service Assignment
# ─────────────────────────────────────────────

def check2_service_assignment(tool: dict, registry: list[dict]) -> dict:
    """
    Verify the tool's MCP service assignment is rational.
    - Service not in known platform services → WARNING (new service being created)
    - New service with only this tool → WARNING (single-tool service is fragile)
    - Similar tools exist in a different service → REQUIRES_REVIEW (possible wrong home)
    - Service field missing → REJECT
    """
    service = tool.get("service") or (
        tool.get("ownership", {}).get("service") if isinstance(tool.get("ownership"), dict) else None
    )
    name = tool.get("tool_name", "")
    description = str(tool.get("description", ""))

    result = {"status": "PASS", "findings": []}

    if not service:
        result["status"] = "REJECT"
        result["findings"].append(
            "Missing 'service' field. Every tool must declare which MCP server hosts it."
        )
        return result

    # Check against known services
    if service not in VALID_SERVICES:
        if result["status"] == "PASS":
            result["status"] = "WARNING"
        result["findings"].append(
            f"Service '{service}' is not in the registered platform services "
            f"({', '.join(sorted(VALID_SERVICES))}). "
            "If this is a new service, register it in mcp-tool-catalog.md first."
        )

    # Count existing tools in the same service
    same_service_tools = [t for t in registry if t.get("service") == service]
    if len(same_service_tools) == 0 and service not in VALID_SERVICES:
        if result["status"] == "PASS":
            result["status"] = "WARNING"
        result["findings"].append(
            f"This would be the first (and only) tool in service '{service}'. "
            "A single-tool service adds infrastructure overhead. "
            "Consider adding it to an existing service, or plan at least 3 tools for the new service."
        )

    # Check if similar tools exist in a different service
    for existing in registry:
        ex_service = existing.get("service", "")
        if ex_service == service:
            continue
        ex_desc = str(existing.get("description", existing.get("display_name", "")))
        if _jaccard(description, ex_desc) >= 0.55:
            if result["status"] not in ("REJECT",):
                result["status"] = "REQUIRES_REVIEW"
            result["findings"].append(
                f"Tool '{existing.get('tool_name')}' in service '{ex_service}' has a similar "
                f"description. Verify this tool belongs in '{service}' and not '{ex_service}'."
            )
            break

    if result["status"] == "PASS":
        result["findings"].append(
            f"Service assignment '{service}' is registered and consistent."
        )

    return result


# ─────────────────────────────────────────────
# Check 3 — Risk Consistency
# ─────────────────────────────────────────────

def check3_risk_consistency(tool: dict) -> dict:
    """
    Validate risk_level, side_effects, idempotent, and requires_approval
    are mutually consistent per the platform risk matrix.

    Matrix:
        L0 → side_effects: none,     idempotent: true  (must)
        L1 → side_effects: read,     idempotent: true  (expected)
        L2 → side_effects: read,     idempotent: may vary
        L3 → side_effects: write,    requires_approval: recommended
        L4 → side_effects: external, requires_approval: true (must)
    """
    risk = tool.get("risk", {})
    if not isinstance(risk, dict):
        return {
            "status": "REJECT",
            "findings": ["'risk' block is missing or not a mapping. Cannot evaluate risk consistency."],
        }

    level = str(risk.get("level", "")).upper()
    side_effects = str(risk.get("side_effects", "")).lower()
    idempotent = risk.get("idempotent")
    requires_approval = risk.get("requires_approval")

    result = {"status": "PASS", "findings": []}

    if level not in RISK_SIDE_EFFECTS_MATRIX:
        result["status"] = "REJECT"
        result["findings"].append(
            f"Unknown risk level '{level}'. Must be one of: {', '.join(RISK_SIDE_EFFECTS_MATRIX)}."
        )
        return result

    expected_effects = RISK_SIDE_EFFECTS_MATRIX[level]
    if side_effects != expected_effects:
        result["status"] = "REJECT"
        result["findings"].append(
            f"Risk level {level} requires side_effects: '{expected_effects}', "
            f"but got '{side_effects}'. Fix the risk block to match the platform matrix."
        )

    if level == "L0" and idempotent is not True:
        result["status"] = "REJECT"
        result["findings"].append(
            "L0 tools (pure computation) must declare idempotent: true."
        )

    if level == "L4" and requires_approval is not True:
        result["status"] = "REJECT"
        result["findings"].append(
            "L4 tools (external side effects) must declare requires_approval: true."
        )

    if level == "L3" and requires_approval is not True:
        if result["status"] == "PASS":
            result["status"] = "WARNING"
        result["findings"].append(
            "L3 tools (write operations) should declare requires_approval: true "
            "or explicitly justify why approval is not required."
        )

    if level in ("L3", "L4") and idempotent is None:
        if result["status"] == "PASS":
            result["status"] = "WARNING"
        result["findings"].append(
            f"{level} tools with side effects must declare 'idempotent' explicitly "
            "(safe retries vs. duplicate-action risk)."
        )

    if result["status"] == "PASS":
        result["findings"].append(
            f"Risk block is consistent: {level} / side_effects:{side_effects} / "
            f"idempotent:{idempotent} / requires_approval:{requires_approval}."
        )

    return result


# ─────────────────────────────────────────────
# Check 4 — Reuse Justifiability
# ─────────────────────────────────────────────

def check4_reuse_justifiability(tool: dict) -> dict:
    """
    A platform tool must be reusable. Verify it has declared consumers.

    - called_by_skills empty or missing → REJECT
      (a tool with no consumers is dead weight; may be a premature abstraction)
    - called_by_skills has exactly 1 entry → WARNING
      (single-consumer tool is at risk of being a workflow_step in disguise)
    - called_by_skills has >= 2 entries → PASS
    """
    usage = tool.get("usage", {})
    if isinstance(usage, dict):
        called_by = usage.get("called_by_skills", [])
    else:
        called_by = tool.get("called_by_skills", [])

    if not isinstance(called_by, list):
        called_by = []

    # Filter out empty strings
    called_by = [s for s in called_by if s and str(s).strip()]

    result = {"status": "PASS", "findings": [], "called_by_count": len(called_by)}

    if len(called_by) == 0:
        result["status"] = "REJECT"
        result["findings"].append(
            "No skills declared in 'called_by_skills'. "
            "Platform tools must have at least one confirmed skill consumer. "
            "If this tool has no consumers yet, it should not enter the registry — "
            "it may be a premature abstraction or should remain a workflow_step."
        )
    elif len(called_by) == 1:
        result["status"] = "WARNING"
        result["findings"].append(
            f"Only 1 skill uses this tool ('{called_by[0]}'). "
            "Single-consumer tools risk being workflow_steps in disguise. "
            "If reuse is expected to grow, annotate the TOOL.md with future consumers. "
            "Otherwise, consider implementing this capability as a workflow_step inside that skill."
        )
    else:
        result["findings"].append(
            f"Tool is used by {len(called_by)} skill(s): {', '.join(called_by)}. "
            "Reuse justification is satisfied."
        )

    return result


# ─────────────────────────────────────────────
# Check 5 — Form Appropriateness
# ─────────────────────────────────────────────

def check5_form_appropriateness(tool: dict) -> dict:
    """
    Detect if this capability should be a workflow_step or skill instead of a tool.

    Signals that it should NOT be a tool:
    - Name contains orchestration suffixes (manager, handler, coordinator, ...)
    - Description contains orchestration language (orchestrate, manage, pipeline, ...)
    - Description describes multiple sequential steps
    - Category is 'execution' combined with orchestration language
    - Description length > 250 chars (too complex for atomic)
    """
    name = str(tool.get("tool_name", "")).lower()
    description = str(tool.get("description", ""))
    category = str(tool.get("category", "")).lower()

    result = {"status": "PASS", "findings": []}

    # Name suffix check
    for suffix in NON_ATOMIC_SUFFIXES:
        if name.endswith(suffix) or f"-{suffix}-" in name:
            result["status"] = "REJECT"
            result["findings"].append(
                f"Tool name '{name}' ends with or contains '{suffix}', which indicates "
                "a coordinating/managing role. Tools must be atomic — rename to a "
                "verb-noun that describes a single transformation (e.g., 'parse-X', 'validate-X')."
            )
            break

    # Description orchestration language
    desc_lower = description.lower()
    triggered_patterns = []
    for pattern in ORCHESTRATION_INDICATORS:
        if re.search(pattern, desc_lower):
            triggered_patterns.append(pattern.replace(".*", "..."))

    if triggered_patterns:
        severity = "REJECT" if len(triggered_patterns) >= 2 else "REQUIRES_REVIEW"
        if result["status"] not in ("REJECT",):
            result["status"] = severity
        result["findings"].append(
            f"Description contains orchestration language: {triggered_patterns}. "
            "Tools must be atomic single-step operations. "
            "If this capability orchestrates other tools or describes a sequence, "
            "it should be a skill or workflow_step instead."
        )

    # Description length
    if len(description) > 250:
        if result["status"] == "PASS":
            result["status"] = "WARNING"
        result["findings"].append(
            f"Description is {len(description)} characters. "
            "Atomic tools typically have short, specific descriptions (< 150 chars). "
            "Long descriptions may indicate the tool is doing too much."
        )

    # Execution category + orchestration language
    if category == "execution" and triggered_patterns:
        if result["status"] not in ("REJECT",):
            result["status"] = "REQUIRES_REVIEW"
        result["findings"].append(
            "Category 'execution' combined with orchestration language suggests this "
            "tool may be a skill or workflow_step. Execution tools should be atomic "
            "side-effecting operations (e.g., 'send-notification', 'write-record'), "
            "not general purpose executors."
        )

    # Missing category
    if category not in VALID_CATEGORIES:
        if result["status"] == "PASS":
            result["status"] = "WARNING"
        result["findings"].append(
            f"Category '{category}' is not in the valid set: "
            f"{', '.join(sorted(VALID_CATEGORIES))}. "
            "An incorrect category may signal incorrect capability classification."
        )

    if result["status"] == "PASS":
        result["findings"].append(
            "Tool name, description, and category are consistent with atomic form."
        )

    return result


# ─────────────────────────────────────────────
# Decision aggregator
# ─────────────────────────────────────────────

DECISION_RANK = {
    "PASS": 0,
    "WARNING": 1,
    "REQUIRES_REVIEW": 2,
    "REJECT": 3,
}

DECISION_NAMES = {v: k for k, v in DECISION_RANK.items()}


def _check_status_to_decision(status: str) -> str:
    mapping = {
        "PASS": "PASS",
        "WARNING": "PASS_WITH_WARNINGS",
        "REQUIRES_REVIEW": "REQUIRES_REVIEW",
        "REJECT": "REJECT",
    }
    return mapping.get(status, "REQUIRES_REVIEW")


def aggregate_decision(check_results: dict) -> tuple[str, list[str], list[str]]:
    """
    Combine five check statuses into a single gate decision.
    Any REJECT → overall REJECT.
    Any REQUIRES_REVIEW (no REJECT) → overall REQUIRES_REVIEW.
    Any WARNING only → PASS_WITH_WARNINGS.
    """
    worst_rank = 0
    reasons: list[str] = []
    actions: list[str] = []

    for check_name, check_data in check_results.items():
        status = check_data.get("status", "PASS")
        rank = DECISION_RANK.get(status, 0)
        if rank > worst_rank:
            worst_rank = rank
        for finding in check_data.get("findings", []):
            reasons.append(f"[{check_name}] {finding}")

    decision = _check_status_to_decision(DECISION_NAMES.get(worst_rank, "PASS"))

    if decision == "REJECT":
        actions.append("Fix all REJECT findings before resubmitting to the registry.")
    if decision in ("REQUIRES_REVIEW", "PASS_WITH_WARNINGS"):
        actions.append("Address flagged items and resubmit, or add justification comments to TOOL.md.")
    if decision == "PASS":
        actions.append("Tool is ready to be registered with status: approved.")

    return decision, reasons, actions


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def run_gate(tool_md_path: Path, registry_path: Path) -> dict:
    tool = parse_tool_md(tool_md_path)
    if tool is None:
        return {
            "tool_name": str(tool_md_path),
            "decision": "REJECT",
            "checks": {},
            "reasons": ["Could not parse TOOL.md — check YAML syntax and encoding."],
            "recommended_actions": ["Fix TOOL.md syntax errors."],
            "neighbor_tools": [],
        }

    registry = load_tool_registry(registry_path)
    tool_name = tool.get("tool_name", str(tool_md_path.stem))

    checks = {
        "check1_global_duplication": check1_global_duplication(tool, registry),
        "check2_service_assignment":  check2_service_assignment(tool, registry),
        "check3_risk_consistency":    check3_risk_consistency(tool),
        "check4_reuse_justifiability": check4_reuse_justifiability(tool),
        "check5_form_appropriateness": check5_form_appropriateness(tool),
    }

    decision, reasons, actions = aggregate_decision(checks)

    neighbor_tools = list({
        n
        for c in checks.values()
        for n in c.get("neighbors", [])
    })

    return {
        "tool_name": tool_name,
        "decision": decision,
        "checks": checks,
        "reasons": reasons,
        "recommended_actions": actions,
        "neighbor_tools": neighbor_tools,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Tool Admission Gate (Phase 4T)")
    parser.add_argument("tool_md", help="Path to TOOL.md")
    parser.add_argument(
        "--registry",
        default="tool-registry.yaml",
        help="Path to tool-registry.yaml (default: tool-registry.yaml)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output JSON instead of human-readable text",
    )
    args = parser.parse_args()

    tool_md_path = Path(args.tool_md)
    registry_path = Path(args.registry)

    if not tool_md_path.exists():
        print(json.dumps({"error": f"File not found: {tool_md_path}"}))
        sys.exit(2)

    result = run_gate(tool_md_path, registry_path)

    if args.json_output:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        _print_human(result)

    exit_code = 0 if result["decision"] in ("PASS", "PASS_WITH_WARNINGS") else 1
    sys.exit(exit_code)


def _print_human(result: dict) -> None:
    decision = result["decision"]
    icons = {
        "PASS": "PASS",
        "PASS_WITH_WARNINGS": "WARN",
        "REQUIRES_REVIEW": "REVIEW",
        "REJECT": "REJECT",
    }
    icon = icons.get(decision, decision)
    print(f"\n[{icon}] {result['tool_name']} — {decision}")
    print("=" * 60)

    for check_name, check_data in result.get("checks", {}).items():
        status = check_data.get("status", "PASS")
        label = check_name.replace("check", "Check").replace("_", " ").title()
        print(f"\n  {label}  [{status}]")
        for finding in check_data.get("findings", []):
            print(f"    - {finding}")

    print("\nRecommended actions:")
    for action in result.get("recommended_actions", []):
        print(f"  -> {action}")

    if result.get("neighbor_tools"):
        print(f"\nNeighbor tools: {', '.join(result['neighbor_tools'])}")
    print()


if __name__ == "__main__":
    main()
