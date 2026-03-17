#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
batch_admission.py — Run admission checks on all SKILL.md files in a bundle directory.

Usage:
    python scripts/batch_admission.py <bundle-dir> [<bundle-dir2> ...]
    python scripts/batch_admission.py ev-charger-skills business-to-bpmn
"""

import subprocess
import json
import sys
import os
import io
from pathlib import Path

# Force UTF-8 output on Windows terminals
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REGISTRY = "skill-registry.yaml"
ADMISSION_SCRIPT = "skill-admission-review/scripts/admission_gate.py"

DECISION_ORDER = ["PASS", "PASS_WITH_WARNINGS", "REQUIRES_REVIEW", "REJECT", "ERROR"]


def run_admission(skill_path: str) -> dict:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, ADMISSION_SCRIPT, skill_path, "--registry", REGISTRY],
        capture_output=True,
        env=env,
    )
    raw = result.stdout.decode("utf-8", errors="replace")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # admission_gate outputs only JSON; if parse fails, capture stderr too
        err = result.stderr.decode("utf-8", errors="replace").strip()
        return {
            "skill_name": skill_path,
            "decision": "ERROR",
            "reasons": [f"Parse error: {err or raw[:120]}"],
            "recommended_actions": [],
            "neighbor_skills": [],
        }


def check_bundle(bundle_dir: str) -> dict:
    root = Path(bundle_dir)
    skill_files = sorted(root.rglob("SKILL.md"))
    if not skill_files:
        print(f"  [WARN] No SKILL.md files found in '{bundle_dir}'")
        return {}

    counts = {d: 0 for d in DECISION_ORDER}
    blocking = []  # (name, decision, reasons)
    warnings = []  # (name, reasons)
    passes = []

    for p in skill_files:
        rel = p.as_posix()
        r = run_admission(rel)
        d = r.get("decision", "ERROR")
        name = r.get("skill_name", rel)
        counts[d if d in counts else "ERROR"] += 1

        if d in ("REJECT", "REQUIRES_REVIEW", "ERROR"):
            blocking.append((name, d, r.get("reasons", []), r.get("recommended_actions", [])))
        elif d == "PASS_WITH_WARNINGS":
            warnings.append((name, r.get("reasons", [])))
        else:
            passes.append(name)

    total = len(skill_files)
    print(f"\n{'=' * 66}")
    print(f"  Bundle: {bundle_dir}  ({total} skills)")
    print(f"{'=' * 66}")

    if passes:
        print(f"\n  [PASS] {len(passes)} skill(s) ready:")
        for n in passes:
            print(f"    [OK] {n}")

    if warnings:
        print(f"\n  [PASS_WITH_WARNINGS] {len(warnings)} skill(s) - fix before final merge:")
        for name, reasons in warnings:
            print(f"    [~]  {name}")
            for r in reasons[:3]:
                print(f"         * {r}")

    if blocking:
        print(f"\n  [BLOCKING] {len(blocking)} skill(s) - must fix before admission:")
        for name, dec, reasons, actions in blocking:
            print(f"    [X]  [{dec}] {name}")
            for r in reasons[:3]:
                print(f"         reason: {r}")
            for a in actions[:2]:
                print(f"         action: {a}")

    ready_pct = round((counts["PASS"] + counts["PASS_WITH_WARNINGS"]) / total * 100) if total else 0
    print(f"\n  Summary: PASS={counts['PASS']}  WARN={counts['PASS_WITH_WARNINGS']}  "
          f"REVIEW={counts['REQUIRES_REVIEW']}  REJECT={counts['REJECT']}  ERROR={counts['ERROR']}"
          f"  →  {ready_pct}% ready")

    return {
        "bundle": bundle_dir,
        "total": total,
        "counts": counts,
        "ready_pct": ready_pct,
        "blocking_skills": [b[0] for b in blocking],
    }


def main():
    bundles = sys.argv[1:] if len(sys.argv) > 1 else ["ev-charger-skills", "business-to-bpmn"]
    summaries = []
    for b in bundles:
        summaries.append(check_bundle(b))

    print(f"\n{'=' * 66}")
    print("  OVERALL SUMMARY")
    print(f"{'=' * 66}")
    for s in summaries:
        if not s:
            continue
        bar = "#" * (s["ready_pct"] // 5) + "." * (20 - s["ready_pct"] // 5)
        print(f"  {s['bundle']:<38} [{bar}] {s['ready_pct']:3}%")
    print()


if __name__ == "__main__":
    main()
