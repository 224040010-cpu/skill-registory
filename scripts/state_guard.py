#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
state_guard.py — Registry State Machine Enforcement

Reads skill-registry.yaml and tool-registry.yaml and enforces the lifecycle
state machine.  Flags any violation that could allow an unreviewed or retired
asset to be consumed by the runtime.

Lifecycle (both skill and tool registries):
    draft → submitted → approved | restricted | needs_revision
    needs_revision → submitted
    approved ↔ restricted
    approved | restricted → deprecated → retired

Rules enforced:
    S-STATE-1  Unknown / invalid status value
    S-STATE-2  L4 skill without security_review: approved
    S-STATE-3  Active skill depends on a draft/submitted/needs_revision skill
    S-STATE-4  Active skill depends on a deprecated/retired skill
    S-STATE-5  Declared dependency not found in registry
    T-STATE-1  Unknown / invalid status value (tool)
    T-STATE-2  Approved tool listing a retired consumer skill
    T-STATE-3  Approved tool listing an unknown consumer skill
    T-STATE-4  Deprecated/retired tool still consumed by active skills

Exit codes:
    0 — PASS   (no violations)
    1 — FAIL   (CRITICAL or HIGH violations found)
    3 — WARN   (only WARNING-level findings)
    2 — Parse error / missing registry
"""

import sys
import json
import argparse
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required — run: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

# ─────────────────────────────────────────────
# State machine constants
# ─────────────────────────────────────────────

VALID_STATUSES = {
    "draft", "submitted", "needs_revision",
    "approved", "restricted",
    "deprecated", "retired",
}

VALID_TRANSITIONS: dict[str, set] = {
    "draft":          {"submitted"},
    "submitted":      {"approved", "restricted", "needs_revision"},
    "needs_revision": {"submitted"},
    "approved":       {"deprecated", "restricted"},
    "restricted":     {"approved", "deprecated"},
    "deprecated":     {"retired"},
    "retired":        set(),
}

ACTIVE_STATUSES   = {"approved", "restricted"}
INACTIVE_STATUSES = {"deprecated", "retired"}
PENDING_STATUSES  = {"draft", "submitted", "needs_revision"}


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def finding(severity: str, rule: str, asset_type: str, asset_name: str, message: str) -> dict:
    return {
        "severity":   severity,    # CRITICAL | HIGH | WARNING | INFO
        "rule":       rule,
        "asset_type": asset_type,
        "asset_name": asset_name,
        "message":    message,
    }


# ─────────────────────────────────────────────
# Skill state checks
# ─────────────────────────────────────────────

def check_skill_states(skills: list) -> list:
    findings = []
    skill_map = {s["skill_name"]: s for s in skills}

    for skill in skills:
        name   = skill.get("skill_name", "<unknown>")
        status = skill.get("status", "")
        risk   = skill.get("risk_level", "")
        sec    = skill.get("security_review", "not_required")
        deps   = skill.get("dependencies") or []

        # S-STATE-1: invalid status
        if status not in VALID_STATUSES:
            findings.append(finding(
                "CRITICAL", "S-STATE-1", "skill", name,
                f"Unknown status '{status}' — must be one of {sorted(VALID_STATUSES)}"
            ))
            continue

        # S-STATE-2: L4 without security approval
        if risk == "L4" and status in ACTIVE_STATUSES and sec != "approved":
            findings.append(finding(
                "HIGH", "S-STATE-2", "skill", name,
                f"L4 skill in active state but security_review='{sec}' (must be 'approved')"
            ))

        # Dependency checks only for active skills
        if status not in ACTIVE_STATUSES:
            continue

        for dep in deps:
            dep_rec = skill_map.get(dep)
            if dep_rec is None:
                # S-STATE-5: dependency not in registry
                findings.append(finding(
                    "HIGH", "S-STATE-5", "skill", name,
                    f"Declared dependency '{dep}' not found in skill-registry.yaml"
                ))
                continue

            dep_status = dep_rec.get("status", "")
            if dep_status in PENDING_STATUSES:
                # S-STATE-3: active skill depends on unreviewed skill
                findings.append(finding(
                    "CRITICAL", "S-STATE-3", "skill", name,
                    f"Active skill depends on '{dep}' which is in pending state '{dep_status}'"
                ))
            elif dep_status in INACTIVE_STATUSES:
                # S-STATE-4: active skill depends on deprecated/retired
                sev = "CRITICAL" if dep_status == "retired" else "HIGH"
                findings.append(finding(
                    sev, "S-STATE-4", "skill", name,
                    f"Active skill depends on '{dep}' which is '{dep_status}'"
                ))

    return findings


# ─────────────────────────────────────────────
# Tool state checks
# ─────────────────────────────────────────────

def check_tool_states(tools: list, skill_map: dict) -> list:
    findings = []

    for tool in tools:
        name      = tool.get("tool_name", "<unknown>")
        status    = tool.get("status", "")
        consumers = tool.get("called_by_skills") or []

        # T-STATE-1: invalid status
        if status not in VALID_STATUSES:
            findings.append(finding(
                "CRITICAL", "T-STATE-1", "tool", name,
                f"Unknown status '{status}' — must be one of {sorted(VALID_STATUSES)}"
            ))
            continue

        if status in ACTIVE_STATUSES:
            for consumer in consumers:
                if consumer in ("pending", "tbd", ""):
                    continue
                consumer_rec = skill_map.get(consumer)
                if consumer_rec is None:
                    # T-STATE-3: consumer not in registry
                    findings.append(finding(
                        "WARNING", "T-STATE-3", "tool", name,
                        f"Consumer skill '{consumer}' not found in skill-registry.yaml"
                        " — update called_by_skills or add the skill"
                    ))
                elif consumer_rec.get("status") == "retired":
                    # T-STATE-2: retired skill still listed as consumer
                    findings.append(finding(
                        "WARNING", "T-STATE-2", "tool", name,
                        f"Consumer skill '{consumer}' is 'retired' — remove from called_by_skills"
                    ))

        if status in INACTIVE_STATUSES:
            # T-STATE-4: inactive tool consumed by active skills
            active_consumers = [
                c for c in consumers
                if skill_map.get(c, {}).get("status", "") in ACTIVE_STATUSES
            ]
            if active_consumers:
                sev = "CRITICAL" if status == "retired" else "HIGH"
                findings.append(finding(
                    sev, "T-STATE-4", "tool", name,
                    f"{status.upper()} tool still listed as consumer by active skills:"
                    f" {active_consumers} — update tool registry or migrate skills"
                ))

    return findings


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Registry State Machine Guard")
    parser.add_argument("--skill-registry", default="skill-registry.yaml",
                        help="Path to skill-registry.yaml")
    parser.add_argument("--tool-registry",  default="tool-registry.yaml",
                        help="Path to tool-registry.yaml")
    parser.add_argument("--output", help="Write JSON report to this path (optional)")
    parser.add_argument("--json",   action="store_true",
                        help="Print JSON to stdout instead of human-readable text")
    args = parser.parse_args()

    skill_path = Path(args.skill_registry)
    tool_path  = Path(args.tool_registry)

    for p in (skill_path, tool_path):
        if not p.exists():
            print(f"ERROR: Registry not found: {p}", file=sys.stderr)
            sys.exit(2)

    skill_data = load_yaml(skill_path)
    tool_data  = load_yaml(tool_path)

    skills    = skill_data.get("skills", [])
    tools     = tool_data.get("tools", [])
    skill_map = {s["skill_name"]: s for s in skills}

    findings_list  = []
    findings_list += check_skill_states(skills)
    findings_list += check_tool_states(tools, skill_map)

    critical = [f for f in findings_list if f["severity"] == "CRITICAL"]
    high     = [f for f in findings_list if f["severity"] == "HIGH"]
    warnings = [f for f in findings_list if f["severity"] == "WARNING"]

    if critical or high:
        overall = "FAIL"
    elif warnings:
        overall = "WARN"
    else:
        overall = "PASS"

    report = {
        "result":  overall,
        "summary": {
            "total":           len(findings_list),
            "critical":        len(critical),
            "high":            len(high),
            "warnings":        len(warnings),
            "skills_checked":  len(skills),
            "tools_checked":   len(tools),
        },
        "findings": findings_list,
    }

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"[state_guard] Report written to {out}")

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        sep = "=" * 60
        print(f"\n{sep}")
        print(f"  State Guard — Registry Lifecycle Enforcement")
        print(f"  Skills: {len(skills)}   Tools: {len(tools)}")
        print(f"{sep}\n")

        if not findings_list:
            print("  [OK] No state machine violations found.\n")
        else:
            icons = {"CRITICAL": "[!!]", "HIGH": "[! ]", "WARNING": "[? ]", "INFO": "[  ]"}
            for f in findings_list:
                icon = icons.get(f["severity"], "[  ]")
                print(f"  {icon} [{f['rule']}] {f['asset_type']}:{f['asset_name']}")
                print(f"       {f['message']}")
                print()

        print(f"  Result: {overall}  "
              f"(CRITICAL={len(critical)}  HIGH={len(high)}  WARN={len(warnings)})\n")

    exit_code = 0 if overall == "PASS" else (3 if overall == "WARN" else 1)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
