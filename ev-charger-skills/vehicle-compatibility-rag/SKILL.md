---
name: vehicle-compatibility-rag
description: Vehicle-specific queries ONLY - compatibility checks, MAC identification, brand-specific known issues. Use ONLY when vehicle/car/brand is the focus. Triggers on "BMW", "Tesla", "VW", "vehicle compatible", "车型兼容", "MAC address", "identify vehicle", "which cars", or vehicle brand names.
bundle_scope: customer-agent
risk_level: L1
---

# Skill: Vehicle Compatibility RAG

**Vehicle-specific queries only** - compatibility, MAC ID, brand issues.

## When to Use THIS Skill

| Question Type | Use |
|--------------|-----|
| "Is BMW compatible with DH480?" | **THIS SKILL** |
| "What vehicles have SLAC issues?" | **THIS SKILL** |
| "Identify vehicle from MAC 4C:FC:AA" | **THIS SKILL** |
| "What does error 0x3001 mean?" | `ev-charger-knowledge` |
| "Walk me through troubleshooting" | `ev-charger-troubleshoot` |

**Key**: This skill answers "WHICH VEHICLE" and "DOES THIS VEHICLE..."

## Data Sources

Location: `rag/production/indexes/` (built by `scripts/build_knowledge_graph.py`)

| Index File | Content |
|------------|---------|
| `compatibility_matrix.json` | Vehicle × Charger compatibility rules |
| `mac_index.json` | MAC prefix → Vehicle ID lookup |
| `entity_graph.json` | Vehicle brand profiles and relationships |
| `issue_solution_index.json` | Issue → Solution mappings |

## Query Patterns

### Pattern 1: Compatibility Check

```
User: "Is the BMW iX compatible with DH480?"

Response:
✅ BMW iX is compatible with DH480.
- Success rate: 89.5% (EU region)
- Known issues: SLAC timeout at high frequency
- Recommendation: Ensure charger firmware >=2.1.0
```

### Pattern 2: Vehicle-Specific Troubleshooting

```
User: "Error 0x3001 on BMW iX, what should I check?"

Response:
🔧 BMW iX + Error 0x3001 (SLAC Timeout)

**Vehicle-Specific Diagnosis:**
- Cause: PLC timing sensitivity in BMW iX
- Solution: Update charger firmware to version 2.1+

**General SLAC Troubleshooting:**
1. Check cable connection quality
2. Verify vehicle charging port cleanliness
3. Try different charging cable
```

### Pattern 3: MAC Address Vehicle Identification

```
User: "Log shows MAC 4C:FC:AA:12:34:56, what vehicle is this?"

Response:
🚗 Vehicle Identified: Tesla
- MAC Prefix: 4C:FC:AA
- Confidence: High
- Known Tesla issues: SLAC timing sensitivity at low temperatures
```

### Pattern 4: Brand Summary

```
User: "What BMW models work with our chargers?"

Response:
🚗 BMW Compatibility Summary

**Supported Models:** iX, i4, i7, iX1, iX3
**Compatible Chargers:** DH480, DH240, DS480, DS1440
**Common Issues:**
- SLAC timeout (high frequency on iX, i4)
- PLC timing sensitivity

**Recommendations:**
- Use firmware 2.1+ for best BMW compatibility
```

## Skill Handoffs

After identifying vehicle context, hand off to specialized skills:

| Vehicle Query Result | Hand Off To |
|---------------------|-------------|
| Vehicle has known issue X | `ev-charger-troubleshoot` |
| Need to search cases for this vehicle | `case-search` (with filter) |
| Log analysis with vehicle context | `log-analyzer` |
| Hardware issue specific to vehicle | `hardware-diagnostics` |

**This skill provides vehicle context, other skills provide solutions.**

## Reporting

When done with a vehicle compatibility query, report:
- Query type (compatibility / diagnosis / identification)
- Match source (rule / relationship / semantic)
- Confidence level
- Vehicle-specific recommendations
- Cross-referenced data sources used

## Reference Files

| File | Contents |
|------|----------|
| `reference.md` | Data loading, indexing, query functions, file locations |
