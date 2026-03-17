---
name: diagnosing-cellular-logs
description: |
  Analyze EV charger cellular_log_for_AI.log files and output diagnostic results with root cause and recommended actions. Use when user mentions "cellular log", "蜂窝日志", "4G/5G问题", "网络注册失败", "ACMP离线", "SIM卡问题", "拨号失败", "充电桩离线", or attaches a cellular log file.
bundle_scope: diagnosis-agent
risk_level: L2
---

# Purpose

Diagnose EV charger cellular network issues by analyzing `cellular_log_for_AI.log` against 10 main rules and 33 sub-rules.

# Trigger

**Use when:**
- User provides `cellular_log_for_AI.log` file
- Keywords: cellular, 蜂窝, 4G, 5G, 网络注册, ACMP离线, SIM卡, 拨号失败, 充电桩离线
- User asks to diagnose charger connectivity issues

**Do NOT use when:**
- Parsing logs into JSONL → use `diagnostic-log-parser`
- Finding similar historical cases → use `case-search`
- Interactive troubleshooting → use `ev-charger-troubleshoot`
- Vehicle compatibility issues → use `vehicle-compatibility-rag`

# Workflow

## Step 1: Run Diagnostic

```bash
# Run from your edge-agent project directory
cd <edge-agent-project>/
python3 scripts/cellular_analyzer.py <log_file> --json
```

## Step 2: Interpret Results

The analyzer outputs:
- Matched rule (1-10)
- Root cause description
- Recommended actions

## Step 3: For Rule 8 (Network Registration Failure)

Check specific error codes in the log:
- `emm_cause` - 4G/LTE rejection codes
- `esm_cause` - APN/PDN rejection codes  
- `5gmm_cause` - 5G rejection codes

See `references/rule8-subrules.md` for complete sub-rule mapping.

# Log Structure (9 Parts)

| # | File | Purpose |
|---|------|---------|
| 1 | module_name.log | 5G modem status |
| 2 | sim_status.log | SIM card detection |
| 3 | airplane_status.log | Data switch on/off |
| 4 | network_registration.log | Network registration |
| 5 | ps_status.log | PS domain attachment |
| 6 | quectel_cm.log | Data call status |
| 7 | ifconfig.log | IP allocation |
| 8 | public_network.log | Internet connectivity |
| 9 | acmp_status.log | **Final status** - ACMP reachability |

Each part has: `SOURCE_FILE:` → `[LOG_INFO]:` → `[CONCLUSION]:[PASS/FAIL]` → `END_OF_FILE:`

# Quick Rule Reference

| Rule | Condition | Issue |
|------|-----------|-------|
| 1 | acmp=PASS | Normal - no action |
| 2 | public=PASS, acmp=FAIL | Internet OK but ACMP unreachable |
| 3 | ip=PASS, public=FAIL | Has IP but no internet |
| 4 | ps=PASS, dial=FAIL | PS OK but dial failed |
| 5 | network=PASS, ps=FAIL | Registered but PS failed |
| 6 | module=PASS, airplane=FAIL | Data switch disabled |
| 7 | module=FAIL | 5G modem init failed |
| 8 | sim=PASS, network=FAIL | **Network registration failed (33 sub-rules)** |
| 9 | sim=FAIL | SIM card error |
| 10 | dial=PASS, ip=FAIL | Dial OK but no IP |

# Common Rule 8 Sub-Rules

| Code | Meaning | Action |
|------|---------|--------|
| emm=15 | Arrears (欠费) | Contact SIM provider |
| esm=27 | Wrong APN | Fix APN config |
| esm=29 | Auth failed | Fix APN credentials |
| CSQ=99 | No signal | Check antenna |
| CSQ<10 | Weak signal | Improve antenna |

# Project Location

```
<edge-agent-project>/
├── scripts/cellular_analyzer.py    # Analyzer script
├── config/cellular_diagnostic_rules.json  # Rule definitions
└── test_cases/                     # Test log files
```

# References

- Sub-rule details: `references/rule8-subrules.md`
- Full rules: `/Users/sharon/w/energy/edge-agent/config/cellular_diagnostic_rules.json`
