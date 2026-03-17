---
name: installation-checklist
description: Installation and commissioning checklist for EV chargers based on 41+ installation-related cases. Use this skill when users are installing new chargers, commissioning equipment, or troubleshooting installation issues. Triggers on "installation checklist", "安装检查", "commissioning", "调试", "site setup", "new charger install", or installation-related questions.
---

# Skill: Installation & Commissioning Checklist

## Purpose
Provide comprehensive installation checklists based on 41+ real installation failure cases to prevent common issues.

## Installation Phases

### Phase 1: Pre-Installation Verification

| Check Item | Details | Common Issue |
|------------|---------|--------------|
| Verify electrical supply | 400V 3-phase, capacity, fuse rating | Undersized supply → nuisance tripping |
| Check network availability | 4G signal >-85dBm or Ethernet | 28 cases of 4G issues |
| Confirm charger model | Connector type, power rating match | Wrong connector for vehicles |
| Review wiring diagrams | Latest revision, site changes | Wiring errors from old drawings |
| Verify components | Check packing list, shipping damage | Missing/damaged parts delay |

### Phase 2: Mechanical Installation

| Check Item | Details | Common Issue |
|------------|---------|--------------|
| Foundation/mounting | Level, anchors, drainage | Water pooling → corrosion (18 cases) |
| Cable entry sealing | Correct glands, IP rating | Water ingress → failures |
| Ventilation clearance | Per installation manual | Overheating from restricted airflow |
| Cable reach | Consider vehicle positions | Cable too short for some vehicles |

### Phase 3: Electrical Installation

| Check Item | Details | Common Issue |
|------------|---------|--------------|
| Cable sizes | AWG/mm² per design | Undersized → heating (18 burned cases) |
| Connection torque | Use torque wrench | **#1 cause of burned terminals** |
| Earth/ground | Resistance <1Ω, bonding | RCD tripping (18 cases) |
| Phase sequence | L1-L2-L3 correct | Motor direction issues |
| Insulation test | 1000V megger, >1MΩ | Latent insulation damage |
| RCD test | Function test | Safety critical |

### Phase 4: Network Configuration

| Check Item | Details | Common Issue |
|------------|---------|--------------|
| 4G signal strength | >-85dBm (use signal meter) | Poor signal → dropouts |
| SIM card activation | Verify data plan active | Inactive SIM |
| OCPP URL configuration | Correct backend URL | Wrong URL → no connection |
| TLS certificates | Valid, not expired | Certificate errors |
| Firewall/ports | OCPP ports open | Blocked traffic |

### Phase 5: Commissioning Tests

| Test | Procedure | Pass Criteria |
|------|-----------|---------------|
| Power-on | Apply power, check displays | All indicators normal |
| Network connection | Verify OCPP heartbeat | Connected to backend |
| Charging test | Full charge cycle | Completes without error |
| Emergency stop | Activate E-stop | Immediately stops, resets OK |
| RCD test | Press test button | Trips and resets correctly |

## Critical Checks (Top 10)

Based on failure analysis, these are the most critical:

```python
CRITICAL_CHECKS = [
    {
        "rank": 1,
        "item": "All electrical connections torqued to spec",
        "reason": "45% of burned components from loose connections",
        "tool": "Torque wrench"
    },
    {
        "rank": 2,
        "item": "Cable sizes match design exactly",
        "reason": "25% of fires from undersized cables",
        "tool": "Cable gauge"
    },
    {
        "rank": 3,
        "item": "Earth resistance <1Ω",
        "reason": "18 RCD tripping cases",
        "tool": "Earth tester"
    },
    {
        "rank": 4,
        "item": "4G signal strength verified",
        "reason": "28 connectivity failure cases",
        "tool": "Signal meter"
    },
    {
        "rank": 5,
        "item": "Water ingress protection verified",
        "reason": "18 corrosion cases",
        "tool": "Visual inspection"
    },
    {
        "rank": 6,
        "item": "OCPP configuration correct",
        "reason": "Multiple backend connection failures",
        "tool": "Backend verification"
    },
    {
        "rank": 7,
        "item": "Ventilation clearance adequate",
        "reason": "Overtemperature failures",
        "tool": "Tape measure"
    },
    {
        "rank": 8,
        "item": "Emergency stop function tested",
        "reason": "Safety critical",
        "tool": "Functional test"
    },
    {
        "rank": 9,
        "item": "Full charge cycle completed",
        "reason": "Validates entire system",
        "tool": "Test vehicle"
    },
    {
        "rank": 10,
        "item": "Documentation completed",
        "reason": "Required for warranty and support",
        "tool": "Checklist form"
    }
]
```

## Common Installation Mistakes

### Electrical
- **Loose connections** - Not using torque wrench
- **Wrong cable sizes** - Using available instead of specified
- **Phase errors** - L1/L2/L3 swapped
- **Missing earth** - Not bonded properly

### Network
- **Wrong OCPP URL** - Typos or wrong environment
- **SIM not activated** - Carrier activation required
- **Antenna placement** - Inside metal enclosure
- **Wrong APN settings** - Carrier-specific

### Mechanical
- **Poor sealing** - Cable glands not tightened
- **No drainage** - Water pools at base
- **Restricted airflow** - Items blocking vents

## Tool Usage

```bash
cd /path/to/jira-knowledge

# Generate checklist
python3 tools/installation_checklist.py

# Phase-specific checklist
python3 tools/installation_checklist.py --phase electrical

# Export to PDF (if available)
python3 tools/installation_checklist.py --export pdf
```

## Sign-Off Template

```
INSTALLATION SIGN-OFF

Site: _______________________
Charger SN: _________________
Date: ______________________
Installer: __________________

□ Pre-installation checks complete
□ Mechanical installation verified
□ Electrical installation verified
□ Network configuration complete
□ Commissioning tests passed
□ Documentation complete

Installer Signature: _________________
Customer Signature: _________________
```
