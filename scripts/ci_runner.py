#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ci_runner.py — CI Validation Runner

For every SKILL.md / TOOL.md in a given list, runs:
  1. Authoring Gate (validate_skill.py / validate_tool.py)
  2. Admission Gate (admission_gate.py / admission_gate_tool.py)

Aggregates results into reports/ci/ and prints a summary.
Used by GitHub Actions on every push / PR that touches skill or tool files.

Usage:
    # Validate a list of changed files (one path per line):
    python scripts/ci_runner.py --files /tmp/changed.txt

    # Validate ALL assets in the repository:
    python scripts/ci_runner.py --all

Options:
    --skill-registry  Path to skill-registry.yaml  (default: skill-registry.yaml)
    --tool-registry   Path to tool-registry.yaml   (default: tool-registry.yaml)
    --output          Directory for per-asset JSON reports (default: reports/ci)

Exit codes:
    0 — All assets PASS or PASS_WITH_WARNINGS
    1 — One or more assets REQUIRES_REVIEW or REJECT
    2 — No files found / parse error
"""

import sys
import json
import subprocess
import argparse
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
REPO_ROOT   = SCRIPTS_DIR.parent

# Paths to validators and admission gates (relative to repo root)
VALIDATE_SKILL   = REPO_ROOT / "guiding-skill-authoring"  / "scripts" / "validate_skill.py"
VALIDATE_TOOL    = REPO_ROOT / "guiding-tool-authoring"   / "scripts" / "validate_tool.py"
ADMISSION_SKILL  = REPO_ROOT / "skill-admission-review"   / "scripts" / "admission_gate.py"
ADMISSION_TOOL   = REPO_ROOT / "tool-admission-review"    / "scripts" / "admission_gate_tool.py"


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def run_script(script: Path, extra_args: list[str]) -> tuple[int, dict]:
    """Run a Python governance script with --json and return (exit_code, parsed_dict)."""
    cmd = [sys.executable, str(script)] + extra_args + ["--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    output = proc.stdout

    # Grab the last complete JSON object in stdout
    depth = 0
    end   = -1
    for i in range(len(output) - 1, -1, -1):
        ch = output[i]
        if ch == "}":
            if depth == 0:
                end = i
            depth += 1
        elif ch == "{":
            depth -= 1
            if depth == 0:
                start = i
                try:
                    return proc.returncode, json.loads(output[start: end + 1])
                except json.JSONDecodeError:
                    break

    return proc.returncode, {
        "error":  "Could not parse JSON output",
        "stderr": proc.stderr[-300:] if proc.stderr else "",
        "stdout": output[-300:],
    }


def overall_decision(validate_result: str, admission_decision: str) -> str:
    """Worst-case combination of the two gate results."""
    order = ["REJECT", "REQUIRES_REVIEW", "PASS_WITH_WARNINGS", "PASS"]
    v_idx = order.index(validate_result)  if validate_result  in order else 3
    a_idx = order.index(admission_decision) if admission_decision in order else 3
    return order[min(v_idx, a_idx)]


def write_report(out_dir: Path, asset_name: str, report: dict):
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"ci_{asset_name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────
# Per-asset checks
# ─────────────────────────────────────────────

def check_skill(skill_md: Path, skill_registry: Path, out_dir: Path) -> dict:
    _, val  = run_script(VALIDATE_SKILL,  [str(skill_md)])
    _, adm  = run_script(ADMISSION_SKILL, [str(skill_md), "--registry", str(skill_registry)])

    val_result = val.get("result",   "ERROR")
    adm_result = adm.get("decision", "ERROR")
    name       = val.get("skill_name") or adm.get("skill_name") or skill_md.parent.name

    report = {
        "asset_type": "skill",
        "asset_name": name,
        "file":       str(skill_md),
        "validate":   {
            "result":         val_result,
            "score":          val.get("score"),
            "max_score":      val.get("max_score"),
            "blocking_issues": val.get("blocking_issues", []),
        },
        "admission":  {
            "decision":            adm_result,
            "reasons":             adm.get("reasons", []),
            "recommended_actions": adm.get("recommended_actions", []),
        },
        "overall": overall_decision(val_result, adm_result),
    }
    write_report(out_dir, name, report)
    return report


def check_tool(tool_md: Path, tool_registry: Path, out_dir: Path) -> dict:
    _, val = run_script(VALIDATE_TOOL,   [str(tool_md)])
    _, adm = run_script(ADMISSION_TOOL,  [str(tool_md), "--registry", str(tool_registry)])

    val_result = val.get("result",   "ERROR")
    adm_result = adm.get("decision", "ERROR")
    name       = val.get("tool_name") or adm.get("tool_name") or tool_md.parent.name

    report = {
        "asset_type": "tool",
        "asset_name": name,
        "file":       str(tool_md),
        "validate":   {
            "result":          val_result,
            "score":           val.get("score"),
            "max_score":       val.get("max_score"),
            "blocking_issues": val.get("blocking_issues", []),
        },
        "admission":  {
            "decision":            adm_result,
            "reasons":             adm.get("reasons", []),
            "recommended_actions": adm.get("recommended_actions", []),
        },
        "overall": overall_decision(val_result, adm_result),
    }
    write_report(out_dir, name, report)
    return report


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="CI Validation Runner")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--files", help="File containing list of changed paths (one per line)")
    group.add_argument("--all",   action="store_true",
                       help="Validate ALL SKILL.md and TOOL.md in the repo")

    parser.add_argument("--skill-registry", default="skill-registry.yaml")
    parser.add_argument("--tool-registry",  default="tool-registry.yaml")
    parser.add_argument("--output",         default="reports/ci",
                        help="Directory for per-asset JSON reports")
    args = parser.parse_args()

    skill_registry = Path(args.skill_registry)
    tool_registry  = Path(args.tool_registry)
    out_dir        = Path(args.output)

    # ── Collect files ──────────────────────────────────────────────────────────
    if args.all:
        files = [
            p for p in REPO_ROOT.rglob("SKILL.md")
            if ".git" not in p.parts
        ] + [
            p for p in REPO_ROOT.rglob("TOOL.md")
            if ".git" not in p.parts
        ]
    else:
        files_path = Path(args.files)
        if not files_path.exists():
            print(f"ERROR: files list not found: {files_path}", file=sys.stderr)
            sys.exit(2)
        raw = files_path.read_text(encoding="utf-8").strip()
        if not raw:
            print("No changed SKILL.md / TOOL.md detected — skipping asset validation.")
            sys.exit(0)
        files = [REPO_ROOT / p.strip() for p in raw.splitlines() if p.strip()]

    files = [f for f in files if f.exists()]
    if not files:
        print("No files to check.")
        sys.exit(0)

    print(f"\nCI Governance Runner — {len(files)} file(s) to check\n")
    print(f"  {'Asset':<45} {'Validate':<22} {'Admission':<22} {'Overall'}")
    print(f"  {'-'*45} {'-'*22} {'-'*22} {'-'*15}")

    results = []
    for fpath in sorted(files):
        name = fpath.name
        if name == "SKILL.md":
            r = check_skill(fpath, skill_registry, out_dir)
        elif name == "TOOL.md":
            r = check_tool(fpath, tool_registry, out_dir)
        else:
            continue

        icon = {
            "PASS":              "[OK]  PASS",
            "PASS_WITH_WARNINGS":"[WN]  PASS_WITH_WARNINGS",
            "REQUIRES_REVIEW":   "[!!]  REQUIRES_REVIEW",
            "REJECT":            "[XX]  REJECT",
        }.get(r["overall"], "[ ] " + r["overall"])

        label = f"{r['asset_type']}:{r['asset_name']}"
        print(f"  {label:<45} "
              f"{r['validate']['result']:<22} "
              f"{r['admission']['decision']:<22} "
              f"{icon}")
        results.append(r)

    # ── Summary ────────────────────────────────────────────────────────────────
    passed  = [r for r in results if r["overall"] in ("PASS", "PASS_WITH_WARNINGS")]
    blocked = [r for r in results if r["overall"] in ("REQUIRES_REVIEW", "REJECT")]

    summary = {
        "total":   len(results),
        "passed":  len(passed),
        "blocked": len(blocked),
        "results": results,
    }

    summary_path = out_dir / "ci_summary.json"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    sep = "─" * 60
    print(f"\n  {sep}")
    print(f"  Total: {len(results)}   Passed: {len(passed)}   Blocked: {len(blocked)}")

    def _safe(text: str, limit: int = 90) -> str:
        """Truncate and replace unencodable chars for safe terminal output."""
        return text[:limit].encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
            sys.stdout.encoding or "utf-8", errors="replace")

    if blocked:
        print(f"\n  BLOCKED — the following assets must be fixed before merge:")
        for r in blocked:
            print(f"    [{r['overall']}] {r['asset_type']}:{r['asset_name']}")
            for issue in r["validate"].get("blocking_issues", [])[:3]:
                print(f"        - {_safe(str(issue))}")
        print()
        sys.exit(1)

    print(f"\n  All checks passed.\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
