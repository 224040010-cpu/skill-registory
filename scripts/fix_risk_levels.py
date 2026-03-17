#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_risk_levels.py — Patch specific skills' risk_level in both SKILL.md and registry.

Skills where L1 should be L2 (they produce output artifacts, not pure read-only):
- These are transformation/analysis skills that generate reports or structured data.
  The transition from L1→L2 is correct: L1 is pure read-only lookup; L2 is
  analysis/transformation that produces new data structures (even if not writing
  to external DBs, they still generate output).
"""

import re
import sys
import yaml
import io
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REGISTRY_PATH = Path("skill-registry.yaml")

# Skills to update: skill_name → new risk_level
RISK_UPGRADES = {
    # ev-charger-skills: analysis tools that generate reports
    "log-analyzer":    "L2",
    "skill-creator":   "L2",
    "ticket-log-join": "L2",
    # business-to-bpmn: transformation tools that produce new data structures
    "ambiguity-detector":       "L2",
    "bpmn-element-mapper":      "L2",
    "bpmn-participant-organizer": "L2",
    "bpmn-task-classifier":     "L2",
    "intent-coverage-evaluator": "L2",
}


def update_registry(upgrades: dict) -> None:
    """Patch risk_level in skill-registry.yaml for the given skills."""
    content = REGISTRY_PATH.read_text(encoding="utf-8")
    lines = content.splitlines()
    result = []
    current_skill = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- skill_name:"):
            current_skill = stripped.split(":", 1)[1].strip().strip('"').strip("'")
        if current_skill in upgrades and stripped.startswith("risk_level:"):
            old = stripped.split(":", 1)[1].strip()
            new = upgrades[current_skill]
            line = line.replace(f"risk_level: {old}", f"risk_level: {new}")
            print(f"  [registry] {current_skill}: {old} → {new}")
        result.append(line)

    REGISTRY_PATH.write_text("\n".join(result) + "\n", encoding="utf-8")


def update_skill_md(skill_name: str, new_level: str) -> None:
    """Find SKILL.md by skill name and patch its risk_level frontmatter field."""
    candidates = [p for p in Path(".").rglob("SKILL.md")
                  if p.parent.name == skill_name
                  and not any(x.startswith(".") for x in p.parts)]
    if not candidates:
        print(f"  [WARN] SKILL.md not found for '{skill_name}'")
        return

    path = candidates[0]
    content = path.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    if len(parts) < 3:
        print(f"  [WARN] No frontmatter in {path}")
        return

    fm = parts[1]
    if "risk_level:" not in fm:
        print(f"  [WARN] No risk_level in {path} frontmatter")
        return

    old_level = re.search(r"risk_level:\s*(\S+)", fm)
    old = old_level.group(1) if old_level else "?"
    new_fm = re.sub(r"(risk_level:\s*)\S+", rf"\g<1>{new_level}", fm)
    path.write_text(f"---{new_fm}---{parts[2]}", encoding="utf-8")
    print(f"  [SKILL.md] {path}: {old} → {new_level}")


def fix_business_to_bpmn_description() -> None:
    """Remove overly broad 'any' terms from business-to-bpmn description."""
    path = Path("business-to-bpmn/SKILL.md")
    if not path.exists():
        print("  [WARN] business-to-bpmn/SKILL.md not found")
        return

    content = path.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    if len(parts) < 3:
        return

    fm = parts[1]
    # Replace broad phrases in the description
    replacements = [
        ("any request", "requests that describe business scenarios"),
        ("including any", "including"),
    ]
    new_fm = fm
    for old_phrase, new_phrase in replacements:
        if old_phrase in new_fm:
            new_fm = new_fm.replace(old_phrase, new_phrase)
            print(f"  [business-to-bpmn] replaced '{old_phrase}' → '{new_phrase}'")

    if new_fm != fm:
        path.write_text(f"---{new_fm}---{parts[2]}", encoding="utf-8")
    else:
        print("  [business-to-bpmn] no 'any' phrases found — already clean")


def main():
    print("=== Updating risk levels ===\n")
    update_registry(RISK_UPGRADES)
    print()
    for skill_name, new_level in RISK_UPGRADES.items():
        update_skill_md(skill_name, new_level)

    print("\n=== Fixing business-to-bpmn description ===\n")
    fix_business_to_bpmn_description()
    print("\nDone. Re-run batch_admission.py to verify.")


if __name__ == "__main__":
    main()
