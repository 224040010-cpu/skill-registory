# Case Search - Reference

## Search Algorithm

```python
def search(query, max_results=10):
    """
    Multi-factor scoring:
    - Title match: 3x weight
    - Text match: 2x weight
    - Error code exact match: 5x weight
    - Symptom match: 2x weight
    - Product/model match: 2x weight
    """
    
    results = []
    for chunk in case_chunks:
        score = calculate_score(query, chunk)
        if score > threshold:
            results.append((chunk, score))
    
    return sorted(results, key=lambda x: x[1], reverse=True)[:max_results]
```

## Available Filters

```python
filters = {
    "product": "DE0120",      # Filter by product model
    "status": "resolved",      # resolved, open, all
    "region": "Europe",        # Filter by region
    "date_range": "2024",      # Filter by year
    "vehicle": "BMW iX",       # Filter by vehicle model
    "vehicle_brand": "Tesla",  # Filter by vehicle brand
}

# Example with filters
search("charging failure", filters={"product": "DE0120", "status": "resolved"})

# Vehicle-filtered search
search("SLAC timeout", filters={"vehicle_brand": "BMW"})
```

## Error Code Patterns

| Code Range | Category |
|------------|----------|
| 0x3XXX | Handshake/protocol errors |
| 0x4XXX | Vehicle communication |
| 0x5XXX | Safety/protection |
| 0x6XXX | Metering/power |

## Product Prefixes

| Prefix | Product Line |
|--------|--------------|
| DE | DC Fast Charger |
| DL | DC Large Power |
| AE | AC Elite |
| AC | AC Standard |

## Vehicle-Specific Search

```python
from vehicle_compat import get_vehicle_known_issues

vehicle_issues = get_vehicle_known_issues("BMW iX")
for issue in vehicle_issues:
    cases = search(issue, filters={"vehicle_brand": "BMW"})
    print(f"Cases for '{issue}': {len(cases)}")
```

## Command Line Usage

```bash
cd /path/to/jira-knowledge

# Basic search
python3 tools/case_search.py "your query"

# With filters (programmatic)
python3 -c "
from tools.case_search import CaseSearch
cs = CaseSearch()
results = cs.search('SLAC timeout', filters={'status': 'resolved'})
for r in results[:5]:
    print(r['title'], r['score'])
"

# Vehicle-specific search
python3 tools/case_search.py "charging failure" --vehicle "Tesla Model 3"
python3 tools/case_search.py "SLAC timeout" --vehicle-brand "BMW"
```

## Full Output Example

```
================================================================================
CASE SEARCH RESULTS
================================================================================
Query: "SLAC timeout"
Found: 8 relevant cases

--------------------------------------------------------------------------------
#1 VRC-666 (Score: 0.89)
--------------------------------------------------------------------------------
Title: Gun 2 cannot charge when Gun 1 idle
Symptoms: SLAC通信超时, 2号枪无法启动充电
Root Cause: 老版本架构问题
Solution: 架构调整
Fix Version: V0.99.03
Status: Resolved

--------------------------------------------------------------------------------
#2 EVSHWT-1257 (Score: 0.72)
--------------------------------------------------------------------------------
Title: BMS通信异常故障
Symptoms: BMS timeout, 充电中断
Root Cause: CAN总线通信问题
Solution: 检查CAN线路连接
Status: Resolved
================================================================================
```
