---
name: failure-analytics
description: Analyze failure patterns, regional trends, and improvement opportunities for EV chargers. Use this skill when users want failure statistics, trend analysis, regional breakdown, product reliability data, or quality improvement insights. Triggers on "failure analysis", "故障统计", "trend report", "regional issues", "reliability data", "质量分析", or "improvement opportunities".
bundle_scope: ops-agent
risk_level: L2
---

# Skill: Failure Pattern Analytics

## Purpose
Analyze historical failure data to identify trends, regional patterns, product issues, and improvement opportunities.

## Data Sources
- Documented JIRA cases with root causes (see `rag/sources/` for current counts)
- Case records from Excel tracking
- RAG chunks for pattern matching

## Analysis Categories

### 1. Failure Type Distribution

Typical distribution from historical data (actual counts vary — query the RAG for live numbers):

```python
FAILURE_CATEGORIES = [
    "display",          # ~20% — screen, LED, touch
    "communication",    # ~16% — 4G, OCPP, network
    "charging_failure", # ~14% — won't start/stop
    "power_electrical", # ~12% — voltage, contactor, module
    "software_firmware",# ~11% — OTA, config, DLL
    "connector_cable",  # ~9%  — gun, cable, PP/CP
    "environmental",    # ~7%  — water, dust, heat
    "installation",     # ~7%  — wiring, config errors
    "other",            # ~4%
]
```

### 2. Regional Analysis

**Top Regions by Case Count:**
| Region | Cases | Top Issues |
|--------|-------|------------|
| Europe | 156 | 4G connectivity, voltage compatibility |
| USA | 124 | Network config, CCS compatibility |
| APAC | 89 | Environmental (humidity), power quality |
| Middle East | 45 | Overtemperature, dust ingress |

**Region-Specific Patterns:**
- **Europe:** OCPP 2.0.1 issues, CE compliance, voltage variations
- **USA:** Different network configs, UL compliance, extreme weather
- **APAC:** High humidity corrosion, power grid instability
- **Middle East:** High temperature derating, sand/dust protection

### 3. Product Model Analysis

```python
def analyze_by_product(cases):
    """Group failures by product model."""
    # Model prefixes:
    # DE: DC Fast Charger
    # DL: DC Large Power
    # AE: AC Elite
    # AC: AC Standard
    
    PRODUCT_ISSUES = {
        "DE0120": {"total": 45, "top_issue": "Display", "mtbf_months": 18},
        "DE0240": {"total": 38, "top_issue": "Power module", "mtbf_months": 15},
        "DL0240": {"total": 32, "top_issue": "Communication", "mtbf_months": 20},
        "AE0022": {"total": 28, "top_issue": "RCD tripping", "mtbf_months": 24},
    }
```

### 4. Time-Based Trends

**Monthly Failure Trends:**
- Track new case creation over time
- Identify spikes after firmware releases
- Correlate with seasonal factors

**Age-Related Failures:**
```
0-6 months:  Installation/configuration issues (DOA, setup errors)
6-12 months: Early component failures (infant mortality)
12-24 months: Software/firmware bugs discovered in field
24+ months:  Wear-out failures (contactors, fans, connectors)
```

### 5. Root Cause Categories

**Software vs Hardware vs Installation:**
```python
ROOT_CAUSE_BREAKDOWN = {
    "software": {
        "percentage": "35%",
        "subcategories": ["Firmware bug", "Configuration error", "OCPP issue"]
    },
    "hardware": {
        "percentage": "40%",
        "subcategories": ["Component failure", "Design issue", "Quality issue"]
    },
    "installation": {
        "percentage": "15%",
        "subcategories": ["Wiring error", "Loose connection", "Wrong config"]
    },
    "environmental": {
        "percentage": "10%",
        "subcategories": ["Water ingress", "Overtemperature", "Power quality"]
    }
}
```

## Analytics Queries

### Get Failure Statistics
```python
def get_failure_stats():
    """Return overall failure statistics — query RAG for live numbers."""
    # Example shape; actual values come from the knowledge base
    return {
        "total_cases": "<query rag/production>",
        "resolved": "...",
        "pending": "...",
        "avg_resolution_days": "...",
        "top_3_issues": ["Display", "Communication", "Charging failure"]
    }
```

### Regional Breakdown
```python
def get_regional_stats(region):
    """Get failure stats for specific region."""
    # Returns cases, top issues, trends for region
```

### Product Reliability
```python
def get_product_reliability(model_prefix):
    """Get reliability metrics for product model."""
    # Returns MTBF, failure rate, top issues
```

## Improvement Recommendations

Based on analysis:

1. **High-Priority Fixes:**
   - Display reliability improvement (122 cases)
   - 4G module reliability (28 cases)
   - Contactor lifetime extension (34 cases)

2. **Process Improvements:**
   - Installation checklist enforcement
   - Torque verification for all connections
   - Network configuration validation

3. **Design Improvements:**
   - Better sealing for environmental protection
   - Improved thermal management
   - More robust connector design

## Tool Usage

```bash
cd /path/to/jira-knowledge
python3 tools/failure_analytics.py

# Generate regional report
python3 tools/failure_analytics.py --region Europe

# Product analysis
python3 tools/failure_analytics.py --product DE0120
```
