#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_skill.py — EV Platform Skill Pre-Submission Validator

Usage:
    python skills/guiding-skill-authoring/scripts/validate_skill.py <path/to/SKILL.md>

Checks a SKILL.md against the 7-dimension quality rubric and platform-specific
constraints. Outputs a scored report with blocking issues and suggestions.

Meta-skills:
    Skills with `meta_skill: true` in frontmatter are guidance/tooling skills
    that produce documentation rather than operational outputs. They are exempt
    from Dimensions 2 (MCP tool calls in workflow) and 3 (tool compliance), and
    receive adjusted scoring for those dimensions.

Result codes (JSON --result field, unified vocabulary):
    PASS                — score >= 60, no blocking issues
    PASS_WITH_WARNINGS  — score >= 45 (minor fixes needed, can proceed with review)
    REQUIRES_REVIEW     — score 30-44 (substantial changes required before submission)
    REJECT              — score < 30 (rewrite required)

Exit codes:
    0 — PASS or PASS_WITH_WARNINGS
    1 — REQUIRES_REVIEW or REJECT
    2 — Parse error or missing file
"""

import sys
import re
import os
import json
from pathlib import Path

# ─────────────────────────────────────────────
# Platform constants
# ─────────────────────────────────────────────

REGISTERED_MCP_SERVERS = {
    "device-status-mcp": [
        "get_device_status", "get_fault_history", "get_realtime_metrics",
        "list_devices", "get_charge_session",
    ],
    "knowledge-base-mcp": ["search_knowledge_base"],
    "ticket-system-mcp": [
        "create_work_order", "update_work_order", "assign_technician",
        "list_available_technicians", "get_work_order", "list_work_orders",
    ],
    "notification-mcp": [
        "send_feishu_message", "send_sms", "send_in_app_notification",
    ],
    "verify-gate-mcp": ["request_approval"],
    # bpmn-tools: registered 2026-03-17 — see tool-registry.yaml + mcp-tool-catalog.md
    "bpmn-tools": [
        "parse_business_intent",
        "extract_process_entities",
        "detect_description_ambiguity",
        "match_bpmn_template",
        "decompose_process_steps",
        "resolve_step_dependencies",
        "identify_parallel_steps",
        "map_steps_to_bpmn_elements",
        "classify_bpmn_task_types",
        "assign_bpmn_participants",
        "assemble_bpmn_model",
        "serialize_bpmn_xml",
        "optimize_bpmn_layout",
        "validate_bpmn_structural",
        "evaluate_intent_coverage",
    ],
}

CONTROL_TOOLS = {
    "restarting", "stopping", "disabling", "unlocking",
    "restart_charger", "stop_charging", "disable_outlet",
    "unlock_connector", "set_power_limit",
}

VALID_RISK_LEVELS = {"L1", "L2", "L3", "L4"}

VALID_AGENTS = {
    "diagnosis-agent", "customer-agent", "ops-agent", "energy-agent",
    "bpmn-agent", "platform",
}

MARKDOWN_PATTERNS = [
    r"^\s*#+\s",         # headings
    r"\*\*[^*]+\*\*",   # bold
    r"\*[^*]+\*",        # italic
    r"^\s*[-*]\s",       # bullet list
    r"\[.+\]\(.+\)",     # links
    r"^\s*>",            # blockquote
    r"```",              # code block
    r"`[^`]+`",          # inline code
]

SKILL_CALLING_PATTERNS = [
    r"use\s+the\s+\S+-skill",
    r"call\s+the\s+\S+-skill",
    r"invoke\s+\S+-skill",
    r"trigger\s+\S+-skill",
    r"使用.*skill",
    r"调用.*skill",
]

REQUIRED_BODY_SECTIONS = [
    "# Purpose", "# Trigger", "# Workflow", "# Constraints",
]

NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]{1,62}[a-z0-9]$")


# ─────────────────────────────────────────────
# Parser
# ─────────────────────────────────────────────

def parse_skill_md(path: Path) -> dict:
    """Parse SKILL.md into frontmatter dict + body string."""
    content = path.read_text(encoding="utf-8")

    if not content.startswith("---"):
        raise ValueError("SKILL.md must start with --- (YAML frontmatter)")

    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Could not find closing --- for frontmatter")

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

    return {"frontmatter": frontmatter, "body": body, "raw": content}


# ─────────────────────────────────────────────
# Dimension checks
# ─────────────────────────────────────────────

def check_dim1_trigger(parsed: dict) -> tuple[int, list, list]:
    """Dimension 1: Trigger clarity (10 pts)"""
    issues, suggestions = [], []
    score = 0
    desc = parsed["frontmatter"].get("description", "")
    body = parsed["body"]

    # Third person check (no "I " or "you " at sentence start)
    if re.search(r"\b(I |I'm |I'll |you |your )", desc, re.IGNORECASE):
        issues.append("Description should be in third person (no 'I', 'you', 'your')")
    else:
        score += 2

    # Trigger clause — accept common equivalent phrasings
    TRIGGER_PHRASES = [
        "use when", "use this skill when", "use only when", "use after",
        "use for ", "triggers on", "trigger on", "triggered when",
        "activate when", "invoke when",
    ]
    if any(p in desc.lower() for p in TRIGGER_PHRASES):
        score += 3
    else:
        issues.append("Description missing a trigger clause ('Use when', 'Triggers on', etc.) — skill may never trigger")

    # Do NOT use when clause
    if "Do NOT use when" in desc or "Do not use when" in desc or "do not use when" in desc:
        score += 2
    else:
        suggestions.append("Add 'Do NOT use when' clause to prevent false triggers")

    # Trigger section in body
    if "# Trigger" in body:
        score += 2
    else:
        suggestions.append("Add a '# Trigger' section to the skill body for clarity")

    # Vagueness check
    vague_phrases = ["general", "various", "handles", "manages", "deals with", "helps with"]
    for phrase in vague_phrases:
        if phrase in desc.lower():
            suggestions.append(f"Description contains vague phrase '{phrase}' — be more specific")
            score = max(0, score - 1)

    return min(score, 10), issues, suggestions


def _is_meta_skill(parsed: dict) -> bool:
    """Return True if this skill declares itself as a meta-skill (guidance/tooling)."""
    raw_value = parsed["frontmatter"].get("meta_skill", "false")
    return str(raw_value).strip().lower() in ("true", "yes", "1")


def check_dim2_workflow(parsed: dict) -> tuple[int, list, list]:
    """Dimension 2: Workflow executability (10 pts)

    Meta-skills are exempt from the MCP tool-call requirement since their
    'workflow' produces documentation, not operational side-effects.
    They are still checked for structural completeness (phases/steps exist,
    error paths addressed, no vague language).
    """
    issues, suggestions = [], []
    score = 0
    body = parsed["body"]
    is_meta = _is_meta_skill(parsed)

    if "# Workflow" not in body:
        issues.append("No '# Workflow' section found — workflow is required")
        return 0, issues, suggestions

    # Extract workflow section
    workflow_match = re.search(r"# Workflow(.*?)(?=\n#|\Z)", body, re.DOTALL)
    workflow = workflow_match.group(1) if workflow_match else ""

    if is_meta:
        # Meta-skill: check structural completeness instead of MCP tool calls.
        # Search the full body (not just the extracted workflow slice) because
        # the workflow regex (?=\n#|\\Z) stops at the first ## subheading,
        # which would truncate multi-phase structures.
        phase_count = len(re.findall(r"## Phase\s+\d+|## Step\s+\d+|\[ \]\s+Step\s+\d+", body))
        numbered_steps = len(re.findall(r"^\s*\d+\.", body, re.MULTILINE))
        total_steps = phase_count + numbered_steps

        if total_steps >= 3:
            score += 7
        elif total_steps >= 1:
            score += 4
            suggestions.append("Meta-skill workflow has few defined phases/steps — aim for 3 or more")
        else:
            score += 2
            suggestions.append("Meta-skill workflow lacks structured phases — add numbered phases or steps")

        # Check for error / edge-case handling
        if re.search(r"(split|not suitable|escalate|flag|cannot|edge case|exception)", workflow, re.IGNORECASE):
            score += 3
        else:
            suggestions.append("Add guidance for edge cases (e.g., workflow too complex to be a single skill)")

        suggestions.append(
            "[Meta-skill] Dimensions 2 & 3 use adjusted scoring — "
            "MCP tool-call requirements do not apply to guidance skills"
        )
        return min(score, 10), issues, suggestions

    # Standard skill: require MCP tool calls
    step_count = len(re.findall(r"\[\s*\]\s*Step\s*\d+", workflow))
    if step_count == 0:
        issues.append("Workflow has no '[ ] Step N:' items — steps are required")
    elif step_count >= 2:
        score += 3
    else:
        score += 1
        suggestions.append("Workflow has only 1 step — most skills need at least 3")

    tool_calls = re.findall(r"`[\w-]+:[\w_]+\(", workflow)
    if len(tool_calls) == 0:
        issues.append("No MCP tool calls found in workflow — every step must name a tool")
    elif len(tool_calls) >= 2:
        score += 4
    else:
        score += 2
        suggestions.append("Only 1 tool call found — ensure all steps reference specific tools")

    if re.search(r"(error|fail|not found|exception|if .* → |else)", workflow, re.IGNORECASE):
        score += 3
    else:
        suggestions.append("Define at least one error/failure path in the workflow")

    ambiguous = ["process the data", "handle appropriately", "look up", "check the data"]
    for phrase in ambiguous:
        if phrase.lower() in workflow.lower():
            suggestions.append(f"Ambiguous step language: '{phrase}' — name the specific tool instead")
            score = max(0, score - 1)

    return min(score, 10), issues, suggestions


def check_dim3_tool_compliance(parsed: dict) -> tuple[int, list, list]:
    """Dimension 3: MCP tool compliance (10 pts)

    Meta-skills are exempt from MCP registration checks. A full score of 10
    is awarded automatically, with a note logged as a suggestion.
    """
    issues, suggestions = [], []
    body = parsed["body"]

    if _is_meta_skill(parsed):
        suggestions.append(
            "[Meta-skill] Dim 3 exempt — no MCP tools expected in a guidance skill. "
            "Verify manually that no tool names are invented in generated skill drafts."
        )
        return 10, issues, suggestions

    score = 10

    # Extract all tool calls in format server:tool_name
    tool_refs = re.findall(r"`([\w-]+):([\w_]+)\(", body)

    if not tool_refs:
        suggestions.append("No tool calls found — if workflow uses tools, verify format is server:tool_name()")
        return 6, issues, suggestions

    unregistered = []
    for server, tool in tool_refs:
        if server not in REGISTERED_MCP_SERVERS:
            unregistered.append(f"{server}:{tool}")
        elif tool not in REGISTERED_MCP_SERVERS[server]:
            unregistered.append(f"{server}:{tool} (server registered but tool unknown)")

    if unregistered:
        for u in unregistered:
            issues.append(f"Unregistered tool: {u} — check references/mcp-tool-catalog.md")
        score -= min(len(unregistered) * 3, 8)

    # Check: L4 skills must have Verify Gate
    risk_indicators = any(ctrl in body.lower() for ctrl in CONTROL_TOOLS)
    has_verify_gate = "verify-gate-mcp:request_approval" in body

    if risk_indicators and not has_verify_gate:
        issues.append(
            "Skill appears to perform device control operations but has no "
            "verify-gate-mcp:request_approval step — required for L4 operations"
        )
        score -= 4

    return max(score, 0), issues, suggestions


def check_dim4_io_contract(parsed: dict) -> tuple[int, list, list]:
    """Dimension 4: Input/Output contract (10 pts)"""
    issues, suggestions = [], []
    score = 0
    body = parsed["body"]
    raw = parsed["raw"]

    # Check Constraints section exists (often defines output fields)
    if "# Constraints" in body:
        score += 3
    else:
        suggestions.append("Add '# Constraints' section — use it to define required output fields")

    # Check for parameter references
    if re.search(r"(device_id|station_id|order_id|user_id|query|date_from|date_to)", body):
        score += 3
    else:
        suggestions.append("Explicitly name input parameters in the workflow steps")

    # Check for output definition
    if re.search(r"(output|returns?|response|result|produces?)", body, re.IGNORECASE):
        score += 2
    else:
        suggestions.append("Define the output format — what does this skill return or produce?")

    # TTS compliance check — only applies if 'voice' is listed in frontmatter surfaces.
    # Searching the body for keywords like 'voice' or 'TTS' would produce false
    # positives for guidance/meta-skills that merely document TTS rules.
    surfaces_raw = parsed["frontmatter"].get("surfaces", "")
    is_voice = "voice" in surfaces_raw.lower()

    if is_voice:
        # Check for markdown inside designated voice-output example blocks.
        # Look for content between "Voice output example" markers or similar.
        voice_example_match = re.search(
            r"(?:voice output|TTS output|语音输出)[^\n]*\n(.*?)(?=\n#|\Z)",
            body, re.DOTALL | re.IGNORECASE
        )
        check_target = voice_example_match.group(1) if voice_example_match else ""

        for pattern in MARKDOWN_PATTERNS:
            matches = re.findall(pattern, check_target, re.MULTILINE)
            if matches:
                issues.append(
                    f"Voice output example contains markdown: "
                    f"'{matches[0][:50]}' — TTS cannot render markdown"
                )
                score -= 2
                break
        score += 2
    else:
        score += 2
        if not _is_meta_skill(parsed):
            suggestions.append(
                "If this skill produces voice output, add 'voice' to surfaces "
                "and verify no markdown appears in user-facing text"
            )

    return min(max(score, 0), 10), issues, suggestions


def check_dim5_constraints(parsed: dict) -> tuple[int, list, list]:
    """Dimension 5: Constraints & safety boundaries (10 pts)"""
    issues, suggestions = [], []
    score = 0
    body = parsed["body"]

    if "# Constraints" not in body:
        issues.append("No '# Constraints' section — all skills must define explicit constraints")
        return 0, issues, suggestions

    constraints_match = re.search(r"# Constraints(.*?)(?=\n#|\Z)", body, re.DOTALL)
    constraints = constraints_match.group(1) if constraints_match else ""

    # Check for explicit DO NOTs
    if re.search(r"NEVER|never|Do not|do not|must not|MUST NOT", constraints):
        score += 4
    else:
        suggestions.append("Add explicit NEVER/Do not constraints to the Constraints section")

    # Check for scope statement
    if re.search(r"(READ-ONLY|read-only|write|control|L[1-4]|scope|limited to)", constraints, re.IGNORECASE):
        score += 3
    else:
        suggestions.append("Declare the scope in Constraints (e.g., 'This skill is READ-ONLY')")

    # Check for output field requirements
    if re.search(r"(output must|required.*field|must include|following fields)", constraints, re.IGNORECASE):
        score += 3
    else:
        suggestions.append("List required output fields in the Constraints section")

    return min(score, 10), issues, suggestions


def check_dim6_single_responsibility(parsed: dict) -> tuple[int, list, list]:
    """Dimension 6: Single responsibility (10 pts)"""
    issues, suggestions = [], []
    score = 10
    desc = parsed["frontmatter"].get("description", "")
    body = parsed["body"]

    # Detect conjunction overload in description
    conjunctions = ["and also", "as well as", "additionally", "furthermore", "moreover"]
    for conj in conjunctions:
        if conj in desc.lower():
            issues.append(
                f"Description uses '{conj}' — this suggests multiple responsibilities. "
                "Consider splitting into two skills."
            )
            score -= 3

    # Detect skill-calling patterns (trying to orchestrate)
    for pattern in SKILL_CALLING_PATTERNS:
        if re.search(pattern, body, re.IGNORECASE):
            issues.append(
                "Skill appears to call or reference another skill — "
                "skills must be leaf nodes. Move orchestration to the Agent/Workflow layer."
            )
            score -= 5
            break

    # Check for mixed output types (report + notification + control = too broad).
    # Meta-skills are exempt: they document all output types by design and are
    # not themselves producing those outputs.
    if not _is_meta_skill(parsed):
        output_types = 0
        if re.search(r"generat|report|document|file", body, re.IGNORECASE):
            output_types += 1
        if re.search(r"notif|alert|send.*message|push", body, re.IGNORECASE):
            output_types += 1
        if re.search(r"restart|stop|control|disable|modify.*device", body, re.IGNORECASE):
            output_types += 1
        if re.search(r"create.*order|work.*order|dispatch", body, re.IGNORECASE):
            output_types += 1

        if output_types >= 3:
            suggestions.append(
                f"Skill touches {output_types} different output types "
                "(report / notification / control / work order) — consider splitting"
            )
            score -= 3

    return max(score, 0), issues, suggestions


def check_dim7_testability(parsed: dict) -> tuple[int, list, list]:
    """Dimension 7: Testability (10 pts)"""
    issues, suggestions = [], []
    score = 0
    body = parsed["body"]
    skill_dir = Path(parsed.get("_path", ".")).parent

    # Check for examples in body or references/
    if re.search(r"(example|input.*output|sample|e\.g\.|示例)", body, re.IGNORECASE):
        score += 3
    else:
        suggestions.append("Add at least one input/output example to the skill body or references/examples.md")

    # Check for error/edge case example
    if re.search(r"(error.*example|edge case|不存在|找不到|超时|timeout|not found)", body, re.IGNORECASE):
        score += 2
    else:
        suggestions.append("Add an error or edge case example (what happens when device not found, etc.)")

    # Check for evals directory
    evals_path = skill_dir / "evals" / "evals.json"
    if evals_path.exists():
        score += 3
        # Try to count eval cases
        try:
            import json
            with open(evals_path, encoding="utf-8") as f:
                evals = json.load(f)
            eval_count = len(evals.get("evals", []))
            if eval_count >= 2:
                score += 2
            else:
                suggestions.append(f"evals.json has only {eval_count} test case(s) — aim for at least 3")
        except Exception:
            suggestions.append("evals/evals.json exists but could not be parsed as JSON")
    else:
        suggestions.append("Create evals/evals.json with at least 2-3 test prompts for automated testing")

    # Check for references/ examples file
    refs_dir = skill_dir / "references"
    if refs_dir.exists():
        example_files = list(refs_dir.glob("*example*")) + list(refs_dir.glob("*sample*"))
        if example_files:
            score = min(score + 1, 10)

    return min(score, 10), issues, suggestions


def check_name(parsed: dict) -> tuple[list, list]:
    """Additional name validation (not a separate dimension, blocks submission)."""
    issues, suggestions = [], []
    name = parsed["frontmatter"].get("name", "")

    if not name:
        issues.append("BLOCKING: 'name' field is missing from frontmatter")
        return issues, suggestions

    if not NAME_PATTERN.match(name):
        issues.append(
            f"BLOCKING: name '{name}' is invalid. "
            "Use lowercase letters, digits, and hyphens only. "
            "Must start with a letter and be 3-64 characters. "
            "Pattern: verb-ing-object[-qualifier]"
        )

    if "_" in name:
        issues.append(f"BLOCKING: name contains underscore — use hyphens instead: '{name.replace('_', '-')}'")

    if any(c.isupper() for c in name):
        issues.append(f"BLOCKING: name contains uppercase letters — use all lowercase: '{name.lower()}'")

    reserved = ["anthropic", "claude", "skill", "agent", "mcp"]
    for r in reserved:
        if name == r or name.startswith(r + "-") or name.endswith("-" + r):
            issues.append(f"BLOCKING: name '{name}' uses reserved word '{r}'")

    return issues, suggestions


# ─────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────

def validate(skill_path: str, output_json: bool = False) -> int:
    path = Path(skill_path)
    if not path.exists():
        print(f"ERROR: File not found: {skill_path}")
        return 2

    try:
        parsed = parse_skill_md(path)
        parsed["_path"] = str(path)
    except ValueError as e:
        print(f"ERROR: Could not parse SKILL.md: {e}")
        return 2

    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  EV Platform Skill Validator")
    print(f"  Skill: {parsed['frontmatter'].get('name', '<unnamed>')}")
    print(f"  File:  {path}")
    print(f"{sep}\n")

    # Run all dimensions
    dimensions = [
        ("1. Trigger Clarity",        check_dim1_trigger),
        ("2. Workflow Executability",  check_dim2_workflow),
        ("3. MCP Tool Compliance",     check_dim3_tool_compliance),
        ("4. Input/Output Contract",   check_dim4_io_contract),
        ("5. Constraints & Safety",    check_dim5_constraints),
        ("6. Single Responsibility",   check_dim6_single_responsibility),
        ("7. Testability",             check_dim7_testability),
    ]

    total = 0
    all_issues = []
    all_suggestions = []

    print(f"{'Dimension':<35} {'Score':>7}   Issues")
    print(f"{'-' * 35} {'-' * 7}   {'-' * 20}")

    for label, check_fn in dimensions:
        score, issues, suggestions = check_fn(parsed)
        total += score
        flag = "[!]" if issues else ("[?]" if suggestions else "[OK]")
        print(f"{label:<35} {score:>4}/10   {flag} {issues[0][:55] if issues else ''}")
        all_issues.extend([(label, i) for i in issues])
        all_suggestions.extend([(label, s) for s in suggestions])

    # Name validation (blocking, not scored)
    name_issues, _ = check_name(parsed)
    all_issues.extend([("Name format", i) for i in name_issues])

    # Rating
    print(f"\n{'-' * 60}")
    print(f"  Total: {total}/70", end="  ")
    if total >= 60:
        rating = "[PASS] PASS"
    elif total >= 45:
        rating = "[WARN] PASS_WITH_WARNINGS (minor fixes needed)"
    elif total >= 30:
        rating = "[FAIL] REQUIRES_REVIEW (substantial revision required)"
    else:
        rating = "[FAIL] REJECT (rewrite required)"
    print(f"  {rating}")
    print(f"{'-' * 60}\n")

    # Blocking issues
    blocking = [i for _, i in all_issues if "BLOCKING" in i or i in [
        x for _, x in all_issues
    ]]
    if all_issues:
        print("BLOCKING ISSUES (must fix before submission):")
        for dim, issue in all_issues:
            print(f"  [{dim}] {issue}")
        print()

    if all_suggestions:
        print("SUGGESTIONS (non-blocking):")
        for dim, suggestion in all_suggestions:
            print(f"  [{dim}] {suggestion}")
        print()

    # JSON output branch — emit structured result and return early
    if output_json:
        missing = [s for s in REQUIRED_BODY_SECTIONS if s not in parsed["body"]]
        blocking = [i for _, i in all_issues]
        blocking += [f"Missing required section: {s}" for s in missing]
        # Unified result vocabulary: PASS / PASS_WITH_WARNINGS / REQUIRES_REVIEW / REJECT
        if total >= 60 and not blocking:
            result_code = "PASS"
        elif total >= 45:
            # Near-passing: may proceed with review but has warnings or minor fixes
            result_code = "PASS_WITH_WARNINGS"
        elif total >= 30:
            # Substantial changes required before submission
            result_code = "REQUIRES_REVIEW"
        else:
            # Score too low — rewrite required
            result_code = "REJECT"
        _warn_kw = ("missing", "no evals", "add ", "define ", "create ", "required", "must")
        warnings = [s for _, s in all_suggestions if any(w in s.lower() for w in _warn_kw)]
        suggestions = [s for _, s in all_suggestions if not any(w in s.lower() for w in _warn_kw)]
        print(json.dumps({
            "skill_name": parsed["frontmatter"].get("name", "<unnamed>"),
            "score": total,
            "max_score": 70,
            "result": result_code,
            "blocking_issues": blocking,
            "warnings": warnings,
            "suggestions": suggestions,
        }, indent=2, ensure_ascii=False))
        return 0 if result_code in ("PASS", "PASS_WITH_WARNINGS") else 1

    # Check required sections
    missing_sections = [s for s in REQUIRED_BODY_SECTIONS if s not in parsed["body"]]
    if missing_sections:
        print("MISSING REQUIRED SECTIONS:")
        for s in missing_sections:
            print(f"  {s}")
        print()

    if total >= 60 and not all_issues:
        print("[OK] PASS — Ready for engineering review. Don't forget to add the registry stanza.\n")
    elif total >= 45:
        print("[!]  PASS_WITH_WARNINGS — Fix blocking issues above, then submit for review.\n")
    elif total >= 30:
        print("[!!] REQUIRES_REVIEW — Substantial revision needed. See references/validation-rubric.md.\n")
    else:
        print("[!!] REJECT — Rewrite required. Score too low to proceed.\n")

    return 0 if total >= 45 else 1


if __name__ == "__main__":
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    if len(positional) != 1:
        print(f"Usage: python {sys.argv[0]} <path/to/SKILL.md> [--json]")
        sys.exit(2)
    sys.exit(validate(positional[0], output_json="--json" in flags))
