---
name: case-search
description: Search historical EV charger cases by keywords, error codes, symptoms, or product models. Use when users want to find similar past issues, look up error codes, or search by symptoms. Triggers on "find similar case", "查找案例", "search cases", "历史问题", "similar issue", or case search requests.
bundle_scope: diagnosis-agent
risk_level: L1
---

# Skill: Case Search

## Purpose

Search 12,575+ RAG chunks and 897+ case records to find:
- Similar historical issues
- Error code meanings
- Solutions that worked before
- Product-specific problems

## When to Use

| Task | Skill |
|------|-------|
| "Find similar cases to this issue" | **THIS SKILL** |
| "Search resolved SLAC timeout cases" | **THIS SKILL** |
| "What cases exist for DE0120?" | **THIS SKILL** |

## Do NOT Use When

| Task | Use Instead |
|------|-------------|
| "Analyze this log file" | `log-analyzer` |
| "Step-by-step troubleshooting" | `ev-charger-troubleshoot` |
| "Quick error code meaning" | `ev-charger-knowledge` |
| "Vehicle compatibility check" | `vehicle-compatibility-rag` |

## Search Types

### 1. Keyword Search
```bash
python3 tools/case_search.py "充电失败"
python3 tools/case_search.py "SLAC timeout"
```

### 2. Error Code Search
```bash
python3 tools/case_search.py "code:0x3001"
python3 tools/case_search.py "code:405"
```

### 3. Symptom-Based Search
```bash
python3 tools/case_search.py "charging stops at 80%"
```

### 4. Product-Specific Search
```bash
python3 tools/case_search.py "DE0120 display issue"
```

### 5. Vehicle-Filtered Search
```bash
python3 tools/case_search.py "SLAC timeout" --vehicle-brand "BMW"
```

## Common Search Patterns

| Search Query | Finds |
|--------------|-------|
| "display" OR "黑屏" | Display/screen issues |
| "OCPP" OR "通信" | Communication problems |
| "contactor" OR "接触器" | Contactor failures |
| "temperature" OR "过温" | Thermal issues |
| "RCD" OR "漏电" | Ground fault issues |

## Output Format

```
================================================================================
CASE SEARCH RESULTS
================================================================================
Query: "SLAC timeout"
Found: 8 relevant cases

#1 VRC-666 (Score: 0.89)
    Title: Gun 2 cannot charge when Gun 1 idle
    Root Cause: SLAC通信超时
    Solution: Upgrade to V0.99.03
    Status: Resolved

#2 EVSHWT-1257 (Score: 0.72)
    Title: BMS通信异常故障
    Solution: 检查CAN线路连接
================================================================================
```

## Integration

Integrates with:
- **Log Analyzer**: Find similar cases for detected issues
- **Vehicle Compatibility RAG**: Filter by vehicle brand
- **Failure Analytics**: Aggregate for trend analysis

## Related Skills

| After Search Shows... | Hand Off To |
|----------------------|-------------|
| Vehicle-specific pattern | `vehicle-compatibility-rag` |
| Need deeper log analysis | `log-analyzer` |
| Step-by-step diagnosis needed | `ev-charger-troubleshoot` |
| Trend analysis needed | `failure-analytics` |

## Reference

For search algorithm, filters, and code examples, see `reference.md`.
