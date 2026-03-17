---
name: log-analyzer
description: Analyze logs to diagnose issues - detect faults, match known issues, recommend solutions. Use when user has a log file and wants to know "what's wrong". Triggers on "analyze log", "日志分析", "what's wrong in this log", "find errors", "diagnose from log". NOT for ETL/parsing - use diagnostic-log-parser for that.
---

# Skill: EV Charger Log Analyzer

## Purpose

**Diagnostic skill** - Analyze logs to find faults and recommend solutions.

## When to Use

| Task | Skill |
|------|-------|
| "What's wrong in this log?" | **THIS SKILL** |
| "Diagnose the charger from logs" | **THIS SKILL** |
| "Find matching JIRA issues" | **THIS SKILL** |

## Do NOT Use When

| Task | Use Instead |
|------|-------------|
| "Parse logs into JSONL" | `diagnostic-log-parser` |
| "Extract faults for RAG" | `diagnostic-log-parser` |
| "Quick error code lookup" | `ev-charger-knowledge` |
| "Step-by-step troubleshooting" | `ev-charger-troubleshoot` |

## Capabilities

- **11 signal detection rules** - See `reference.md` for patterns
- **51+ known JIRA issue patterns** - Auto-match against database
- **12,575 RAG chunks** - Similarity matching
- **Vehicle auto-detection** - From MAC address in logs

## Workflow

```
1. Parse log file
2. Apply signal detection rules (HIGH/MEDIUM/LOW severity)
3. Match against known JIRA issues
4. Find similar historical cases
5. Auto-detect vehicle from MAC (if present)
6. Generate recommendations
```

## Signal Categories

| Category | Severity | Examples |
|----------|----------|----------|
| communication | HIGH | OCPP disconnect, BMS timeout |
| handshake | HIGH | SLAC timeout, CP state error |
| electrical | HIGH | Contactor fault, voltage error |
| thermal | MEDIUM | Over-temperature warning |
| safety | HIGH | Emergency stop, ground fault |
| software | MEDIUM | Firmware error, OTA fail |

For full detection rules, see `reference.md`.

## Output Format

```
================================================================================
EV CHARGER LOG ANALYZER
================================================================================
## SIGNAL RULES TRIGGERED

### [HIGH] SLAC Communication Timeout
    Category: handshake
    Line 1523: "SLAC negotiation timeout"
    Action: Check PLC module and vehicle compatibility

## MATCHED KNOWN JIRA ISSUES

### VRC-666 - Gun 2 cannot charge when Gun 1 idle
    Confidence: 72%
    Solution: Upgrade firmware to V0.99.03

## VEHICLE DETECTED (if MAC found)
Brand: BMW
Known Issues: SLAC timeout (high frequency)

## RECOMMENDATIONS
1. Primary suspect: VRC-666
   Action: Upgrade firmware
```

## Vehicle-Aware Analysis

When MAC address found in log:
1. Auto-identify vehicle brand
2. Load vehicle-specific known issues
3. Prioritize vehicle-relevant patterns
4. Add vehicle context to recommendations

## Usage

```bash
python3 tools/log_analyzer.py path/to/charger_log.txt
python3 tools/log_analyzer.py path/to/log.txt output_report.txt
```

## Related Skills

| After Analysis Shows... | Hand Off To |
|------------------------|-------------|
| Vehicle-specific issue | `vehicle-compatibility-rag` |
| Hardware failure | `hardware-diagnostics` |
| Need similar cases | `case-search` |
| Error code unclear | `ev-charger-knowledge` |

## Best Practices

1. **Provide complete logs** - Partial logs may miss context
2. **Include timestamps** - Helps with timeline reconstruction
3. **Note firmware version** - Some issues are version-specific
4. **Include vehicle info if known** - Enables vehicle-specific diagnosis

## Reference

For detection rules, patterns, and code examples, see `reference.md`.
