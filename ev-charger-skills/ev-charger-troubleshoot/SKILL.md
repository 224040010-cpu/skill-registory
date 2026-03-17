---
name: ev-charger-troubleshoot
description: Interactive step-by-step troubleshooting for EV charger issues. Use this skill when users need guided diagnosis with decision trees. Triggers on "step-by-step", "guide me through", "troubleshoot", "故障排除", "diagnose", "what should I check", or when user needs systematic diagnosis (not just quick lookup).
---

# Skill: EV Charger Troubleshooting

## Purpose
Provide **step-by-step interactive diagnosis** using decision trees from 51+ real JIRA cases.

## When to Use THIS Skill vs Others

| Scenario | Use |
|----------|-----|
| "What does error 0x3001 mean?" | `ev-charger-knowledge` (quick lookup) |
| "Walk me through diagnosing SLAC timeout" | **THIS SKILL** |
| "Is BMW compatible?" | `vehicle-compatibility-rag` |
| "Step-by-step for black screen issue" | **THIS SKILL** |

**This skill is for GUIDED TROUBLESHOOTING** - systematic decision trees, not quick answers.

## Decision Tree Entry Points

### Main Symptom Categories
1. **Charging fails to start** → Check QR/RFID/Remote start
2. **Charging stops unexpectedly** → Check error codes, voltage, BMS
3. **Screen/display issues** → Check power, cables, touch controller
4. **Communication errors** → Check OCPP, 4G, network
5. **OTA/Upgrade issues** → Check network, firmware version
6. **Power/electrical issues** → Check supply, contactors, meters

## Error Code Reference

> **For quick error code lookup, use `ev-charger-knowledge` skill first.**
> This skill provides **troubleshooting steps** after you know the error.

**Look up error code:**
```bash
python3 tools/troubleshoot.py --lookup <error_code>
```

## Diagnosis Workflows

### Charging Fails to Start
```
1. Check if error code displayed → Look up error code
2. QR/APP scan issue:
   - Check OCPP 2.0.1 authorization_status (VRC-3529)
   - Verify network connectivity
   - Check backend configuration
3. RFID card issue:
   - Verify card registered in system
   - Check card reader hardware
4. Gun 2 issue when Gun 1 idle:
   - Known issue VRC-666 (V0.99.03 fix)
   - Check SLAC timeout in logs
```

### Communication Errors
```
1. OCPP offline:
   - Check 4G signal strength (>-85dBm)
   - Verify SIM card active
   - Check backend URL configuration
2. BMS communication timeout:
   - Usually vehicle-side issue
   - Try different vehicle
   - Check CAN bus connections
3. Meter communication:
   - Check RS485 wiring
   - Verify meter address settings
```

### Display Issues
```
1. Black screen (黑屏):
   - Check 12V/24V auxiliary power
   - Check display cable connections
   - Check APK crash logs
2. Touch not responding (触屏失效):
   - Clean screen surface
   - Check touch controller connection
   - May need panel replacement
3. Abnormal display:
   - Check for water ingress
   - Review software logs
```

## Tool Usage

Run the interactive troubleshooter:
```bash
cd /path/to/jira-knowledge
python3 tools/troubleshoot.py
```

Look up specific error code:
```bash
python3 tools/troubleshoot.py --lookup 0x3001
```

## Related Cases

| Case ID | Issue | Root Cause | Fix |
|---------|-------|------------|-----|
| VRC-666 | Gun 2 can't charge | SLAC timeout in old architecture | V0.99.03 |
| VRC-3529 | QR scan fails | OCPP 2.0.1 auth logic error | Backend fix |
| VRC-3879 | Voltage mismatch | Parameter misconfiguration | Config update |
| VRC-3989 | 4G dropout | SIM card/antenna issue | Hardware check |

## Vehicle-Specific Diagnosis

**NEW:** For vehicle-specific issues, use the `vehicle-compatibility-rag` skill to:
- Check if the issue is vehicle-specific (e.g., BMW SLAC timing)
- Get vehicle-specific solutions for common errors
- Identify the vehicle from MAC address in logs

### Vehicle-Aware Troubleshooting Flow
```
1. Identify vehicle (from report or MAC in logs)
2. Check vehicle-specific known issues
3. Apply standard troubleshooting with vehicle context
4. Prioritize vehicle-specific solutions
```

### Common Vehicle-Specific Issues
| Vehicle Brand | Common Issue | Solution |
|---------------|--------------|----------|
| BMW (iX, i4) | SLAC timeout | Firmware 2.1+ |
| VW (ID.4, ID.5) | PLC timing | Check vehicle firmware |
| Tesla | Low temp SLAC | Normal, retry after warmup |
| Hyundai | Cable connection | Check connector fit |

## Skill Handoffs

| After Diagnosis Shows... | Hand Off To |
|--------------------------|-------------|
| Vehicle-specific issue | `vehicle-compatibility-rag` |
| Hardware failure suspected | `hardware-diagnostics` |
| Need to analyze log file | `log-analyzer` |
| Need similar past cases | `case-search` |
| Error code meaning unclear | `ev-charger-knowledge` |

## Output Format

When guiding troubleshooting:
1. **Identify symptom category** from decision tree entry points
2. **Ask diagnostic questions** to narrow down
3. **Walk through decision tree** step by step
4. **If vehicle-specific**: Hand off to `vehicle-compatibility-rag`
5. **If hardware issue**: Hand off to `hardware-diagnostics`
6. **Recommend action** with confidence level

**Key principle**: This skill GUIDES, it doesn't just answer. Use numbered steps and checkboxes.
