---
name: agent-workflow
description: Orchestrate EV charger support case pre-processing using all diagnostic tools. Use this skill when processing a complete support case, preparing expert summaries, automating case triage, or running the full diagnostic pipeline. Triggers on "process case", "案例处理", "expert report", "case analysis", "support ticket analysis", "pre-process ticket", or when a complete case needs automated analysis.
---

# Skill: Agent-Expert Workflow

## Purpose
Orchestrate all diagnostic tools to pre-process support cases, reducing expert investigation time by **50-70 minutes per case**.

## Workflow Overview

```
Traditional: 60-90 min per case
With Agent:  15-20 min per case
Savings:     50-70 min per case
```

### Time Savings Breakdown
| Task | Traditional | With Agent | Savings |
|------|------------|------------|---------|
| Log Analysis | 30 min | 2 min | 28 min |
| Search History | 20 min | instant | 20 min |
| Error Code Lookup | 5 min | instant | 5 min |
| Categorization | 10 min | instant | 10 min |
| Find Diagnostic Guide | 15 min | instant | 15 min |

## How to Use

### Step 1: Gather Case Information
```python
# Collect from JIRA ticket or user report:
case_input = {
    "log_path": "/path/to/charger_log.txt",  # Optional
    "symptoms": ["黑屏", "充电失败"],           # From description
    "error_codes": ["0x3001"],                 # If reported
    "title": "【泰国】充电桩黑屏",              # Ticket title
    "region": "Thailand",                       # Extracted or specified
    "product": "DE0120"                         # Product model
}
```

### Step 2: Run Automated Analysis
```python
from agent_workflow import AgentWorkflow

agent = AgentWorkflow()
report = agent.process_case(**case_input)
```

### Step 3: Tool Pipeline

```
Log File ──────→ log_analyzer.py ──→ Pattern matches, JIRA matches
                      │
                      ▼
Symptoms ──────→ case_search.py ──→ Similar resolved cases
                      │
                      ▼
Error Codes ───→ troubleshoot.py ──→ Error meanings, actions
                      │
                      ▼
Category ──────→ hardware_diagnostics.py ──→ Diagnostic guide
                      │
                      ▼
                [PRE-ANALYSIS REPORT]
```

## Output Report Format

```
================================================================================
AGENT PRE-ANALYSIS REPORT
================================================================================
Case: 【泰国】DE0120充电桩黑屏无法启动
Generated: 2024-02-27 10:30:00
Analysis Time: 3.2 seconds

================================================================================
📊 CASE CLASSIFICATION
================================================================================
Primary Category: Display Issues (Confidence: 85%)
Sub-Category: Black screen / no power to display
Severity: HIGH - Customer cannot use charger

================================================================================
📋 LOG ANALYSIS RESULTS
================================================================================
Signals Detected:
  [HIGH] Power supply fault detected at line 1523
  [MEDIUM] Display controller not responding at line 2341

Matched JIRA Issues:
  1. VRC-4214 (78% match) - Display power supply failure
     Root Cause: 12V auxiliary supply fuse blown
     Solution: Replace F3 fuse, check for short circuit

================================================================================
🔍 SIMILAR HISTORICAL CASES
================================================================================
1. EVSHWT-1247 (Score: 0.82)
   "拔枪后充电桩黑屏"
   Resolution: Display cable reseated

2. VRC-5993 (Score: 0.71)
   "Display intermittent"
   Resolution: Replaced LVDS cable

================================================================================
🔧 RECOMMENDED DIAGNOSTIC STEPS
================================================================================
Based on "Display Issues" diagnostic tree:

1. Check 12V/24V auxiliary power supply
   □ Measure voltage at display connector
   □ Check F3 fuse (12V supply)
   
2. Check display cable connections
   □ Reseat LVDS cable at both ends
   □ Inspect for damage
   
3. If power OK but no display
   □ Check APK crash logs
   □ Try display reset via service menu

================================================================================
⚡ PRIORITY ACTIONS
================================================================================
1. [IMMEDIATE] Check 12V fuse - most likely cause (45% of cases)
2. [IF FUSE OK] Reseat display cables
3. [IF CABLES OK] Replace display panel

Parts Likely Needed: F3 Fuse (12V, 5A), possibly LVDS cable
Estimated MTTR: 1-2 hours

================================================================================
📎 ATTACHMENTS FOR EXPERT
================================================================================
- Log analysis details: [attached]
- Similar case summaries: [attached]
- Diagnostic flowchart: [attached]
================================================================================
```

## Integration Points

### Input Sources
- JIRA tickets (via API or manual)
- Log files (uploaded or from remote)
- User symptom descriptions
- Error codes from display or logs

### Output Destinations
- Expert review queue
- JIRA ticket comments
- Support dashboard
- Automated ticket routing

## Tool Dependencies

The workflow uses these tools in sequence:
1. `log_analyzer.py` - Pattern detection
2. `case_search.py` - Historical matching
3. `troubleshoot.py` - Error code lookup
4. `hardware_diagnostics.py` - Diagnostic guides
5. `failure_analytics.py` - Categorization

## Best Practices

1. **Always provide log file if available** - Enables pattern detection
2. **Include exact error codes** - Enables precise lookup
3. **Extract region from title** - Helps identify regional patterns
4. **Note product model** - Product-specific issues exist

## Command Line Usage

```bash
cd /path/to/jira-knowledge

# Full case analysis
python3 tools/agent_workflow.py \
  --log path/to/log.txt \
  --symptoms "黑屏" "充电失败" \
  --error-codes "0x3001" \
  --title "【泰国】充电桩故障"

# Quick symptom-only analysis
python3 tools/agent_workflow.py --symptoms "触屏失效"
```

## Metrics Tracking

Track workflow effectiveness:
- Cases processed per day
- Average analysis time
- Expert time saved
- Accuracy of primary suspect identification
