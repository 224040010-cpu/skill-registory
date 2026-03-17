---
name: ev-charger-knowledge
description: Quick reference for EV charger error codes, product specs, and basic troubleshooting. Use as the FIRST skill for quick lookups. Triggers on "error code", "故障码", "what does code mean", "product model", "charger specs", or quick reference questions. For step-by-step troubleshooting use ev-charger-troubleshoot. For vehicle-specific issues use vehicle-compatibility-rag.
bundle_scope: diagnosis-agent
risk_level: L1
---

# Skill: EV Charger Knowledge Base

## Purpose

**Quick reference skill** for instant lookups:
- Error code meanings and basic solutions
- Product model specifications
- Common symptom explanations

## When to Use THIS Skill vs Others

| Use Case | Skill to Use |
|----------|--------------|
| "What does error 0x3001 mean?" | **THIS SKILL** |
| "What products do we have?" | **THIS SKILL** |
| "Quick answer about error code" | **THIS SKILL** |
| "Step-by-step troubleshooting for charging failure" | `ev-charger-troubleshoot` |
| "Is BMW compatible with DH480?" | `vehicle-compatibility-rag` |
| "Find similar past cases" | `case-search` |
| "Analyze this log file" | `log-analyzer` |
| "Full case pre-processing" | `agent-workflow` |

**Rule of thumb**: Use this skill for **quick lookups**. Use specialized skills for **deep analysis**.

## Quick Reference Data

### Common Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| 0x3001 | SLAC Communication Timeout | Check cable, PLC module, vehicle compatibility |
| 0x3002 | CP State Error | Check control pilot circuit, connector |
| 0x3003 | Contactor Failure | Check contactor coil and drive circuit |
| 0x4001 | BMS Communication Timeout | Usually vehicle-side issue, try different vehicle |
| 0x4002 | Voltage Mismatch | Check battery SOC and charger config |
| 0x5001 | Emergency Stop Activated | Release E-stop button |
| 0x5002 | Ground Fault Detected | Check RCD and wiring |
| 305F | Power Module Version Mismatch | Upgrade firmware |
| 604B | Meter Communication Error | Check RS485 wiring |
| 708 | RPC Service Offline | DLL crash, restart service |
| 720 | RPC Communication Failed | DLL crash, check connectivity |

### Vehicle Compatibility (Quick Reference)

> **For detailed vehicle compatibility, use `vehicle-compatibility-rag` skill**

| Vehicle Brand | Compatible | Quick Note |
|---------------|------------|------------|
| Tesla | ✅ | SLAC timing at low temp |
| BMW | ✅ | FW 2.1+ recommended |
| VW | ✅ | Generally stable |
| Hyundai | ✅ | Check cable fit |
| Audi | ✅ | Stable |
| Mercedes | ✅ | Stable |
| Porsche | ✅ | High power draw |

**For MAC identification or detailed compatibility queries** → Use `vehicle-compatibility-rag`

### Product Models

| Model | Type | Power | Protocol |
|-------|------|-------|----------|
| DH480 | DC Fast | 480kW | CCS1/CCS2 |
| DH240 | DC Fast | 240kW | CCS1/CCS2 |
| DH600 | DC Fast | 600kW | CCS1/CCS2 |
| DS480 | DC Split | 480kW | CCS1/CCS2 |
| DS1440 | DC Split | 1440kW | CCS1/CCS2 |
| AC Ultra | AC | 22kW | Type 2 |
| AC Pro | AC | 7-22kW | Type 1/2 |

## Query Patterns

### Pattern 1: Error Code Lookup

When user asks about an error code:

```
User: "What does error 0x3001 mean?"

Response structure:
1. Error name and description
2. Trigger condition
3. Severity level
4. Step-by-step solution
5. Related errors to check
```

**Example Response:**
```
**Error 0x3001 - SLAC Communication Timeout**

**Description:** PLC handshake failed within timeout period (typically 30s).

**Severity:** Medium

**Trigger:** No SLAC response from vehicle within timeout.

**Diagnosis Steps:**
1. Check cable connection - ensure fully seated
2. Inspect connector pins for damage/debris
3. Try a different vehicle (isolates charger vs vehicle)
4. Check PLC module LED status
5. Review logs for SLAC timing details

**Vehicle-Specific Notes:**
- BMW: Known PLC timing sensitivity → update to FW 2.1+
- Tesla: May occur at low temperatures → normal, retry after warmup
- VW: Check vehicle firmware version

**Related Codes:** 0x3002 (CP State), 0x4001 (BMS Timeout)
```

### Pattern 2: Quick Symptom Reference

When user describes a symptom, provide quick answer then direct to specialized skills:

**Common Symptoms Quick Reference:**

| Symptom | Quick Answer | For Deep Dive |
|---------|--------------|---------------|
| Charging stops at 80% | Usually vehicle BMS limit | `ev-charger-troubleshoot` |
| Black screen | Check 12V supply, display cable | `hardware-diagnostics` |
| SLAC timeout | Check PLC module, cable | `vehicle-compatibility-rag` for vehicle-specific |
| OCPP offline | Check 4G signal, SIM, network | `ev-charger-troubleshoot` |
| Touch not working | Clean screen, check controller | `hardware-diagnostics` |

**For step-by-step diagnosis** → Use `ev-charger-troubleshoot`

### Pattern 3: Log Quick Reference

When user mentions logs:

> **For full log analysis, use `log-analyzer` skill**

Quick patterns to look for:
- `SLAC.*timeout` → PLC/cable issue
- `OCPP.*disconnect` → Network issue  
- `contactor.*fault` → Hardware issue
- `BMS.*timeout` → Usually vehicle-side

### Pattern 4: Case Quick Reference

When user wants similar cases:

> **For case search, use `case-search` skill**

Quick case patterns:

| Symptom | Known Cases |
|---------|-------------|
| Black screen | VRC-3989 |
| SLAC timeout | VRC-666 |
| 4G dropout | VRC-3989 |

## Data Sources

> For current chunk counts and build info, check `rag/production/build_summary.json`.

| Source | Type |
|--------|------|
| Error Codes | error_code |
| FAQ Entries | faq |
| FMEA Analysis | fmea |
| Documents | document |
| Field Experience | field_experience |
| Wiki Docs | wiki_doc |

## Knowledge Files Location

Full knowledge base:

```
~/.cursor/skills/ev-charger-knowledge/
├── chunks.jsonl          # 6,114 knowledge chunks (7MB)
├── SKILL.md              # This skill file
├── LOOKUP_TABLES.md      # Parseable JSON lookup tables
├── DATA_RELATIONSHIPS.md # Entity relationship maps
└── README.md             # Sharing instructions
```

## Skill Routing Guide

This skill is the **entry point** for EV charger questions. Route to specialized skills as needed:

```
User Question → ev-charger-knowledge (quick lookup)
                    │
                    ├─→ Need step-by-step? → ev-charger-troubleshoot
                    ├─→ Vehicle-specific? → vehicle-compatibility-rag  
                    ├─→ Search past cases? → case-search
                    ├─→ Analyze log file? → log-analyzer
                    ├─→ Hardware issue? → hardware-diagnostics
                    └─→ Full case processing? → agent-workflow
```

## Response Guidelines

1. **Start with the most likely answer** - Don't make user read paragraphs
2. **Include severity/urgency** - Help user prioritize
3. **Give actionable steps** - Not just descriptions
4. **Mention vehicle-specific notes** - If vehicle is known
5. **Reference similar cases** - Builds confidence
6. **Suggest next steps** - If initial fix doesn't work

## Example Conversations

### Example 1: Quick Error Lookup (THIS SKILL)
```
User: "Error 708 on charger"

Agent: **Error 708 - RPC Service Offline**
DLL service crashed. Quick fix: power cycle charger.
If persists, check for software updates.
```

### Example 2: Route to Specialized Skill
```
User: "BMW i4 getting SLAC timeout, need full diagnosis"

Agent: BMW has known SLAC issues. Let me use the vehicle-compatibility-rag 
skill for detailed BMW-specific diagnosis...
→ [Uses vehicle-compatibility-rag skill]
```

### Example 3: Quick Answer + Routing
```
User: "Screen is blank but charger seems powered"

Agent: **Quick answer:** Likely 12V supply or display cable issue.

**For step-by-step diagnosis**, I'll use the hardware-diagnostics skill...
→ [Uses hardware-diagnostics skill for detailed guidance]
```
