---
name: hardware-diagnostics
description: Hardware diagnostics and field service guide for EV chargers. Use this skill when users need to diagnose hardware failures, replace components, or perform field repairs. Triggers on "hardware fault", "硬件故障", "replace component", "field service", "display repair", "contactor issue", "power supply problem", "burned terminal", or physical damage reports.
bundle_scope: diagnosis-agent
risk_level: L2
---

# Skill: Hardware Diagnostics & Field Service

## Purpose
Provide systematic hardware diagnosis procedures and repair recommendations for EV charger field service.

## Component Diagnostic Trees

### 1. Display/Screen Issues (122 cases)

**Symptoms:** 黑屏, 花屏, 屏幕不亮, 触屏失效, 显示异常, LED不亮

**Diagnosis Flow:**
```
Step 1: Check power supply to screen
  ├── FAIL: Check 12V/24V auxiliary power supply, fuse
  └── PASS: Continue

Step 2: Check screen cable connections
  ├── FAIL: Reseat or replace LVDS/display cable
  └── PASS: Continue

Step 3: Check for physical damage (cracks, water ingress)
  ├── FAIL: Replace display panel
  └── PASS: Continue

Step 4: Check touch controller (if touch fails)
  ├── FAIL: Replace touch panel or controller board
  └── PASS: Check APK/software logs for crashes
```

**Common Parts:** Display panel, LVDS cable, Touch controller, 12V power supply
**Typical MTTR:** 2 hours

### 2. Contactor Issues (34 cases)

**Symptoms:** 接触器拒动, 接触器粘连, 交流/直流接触器故障

**Diagnosis Flow:**
```
Step 1: Check contactor coil resistance (should be 50-200Ω)
  ├── FAIL: Replace contactor - coil damaged
  └── PASS: Continue

Step 2: Check drive circuit voltage when activated
  ├── FAIL: Check control board/relay driving the contactor
  └── PASS: Continue

Step 3: Check for mechanical binding or debris
  ├── FAIL: Clean or replace contactor
  └── PASS: Continue

Step 4: Check auxiliary contact feedback
  ├── FAIL: Aux contact worn - replace contactor
  └── PASS: Intermittent - monitor and replace preventively
```

**Common Parts:** AC/DC contactor, Control relay, Driver board
**Typical MTTR:** 1.5 hours

### 3. Power Supply Issues (28 cases)

**Symptoms:** 电源故障, 过温, 欠压, 过压, 模块故障

**Diagnosis Flow:**
```
Step 1: Check input voltage (should be 380-420V 3-phase)
  ├── LOW: Check upstream supply, fuses, connections
  ├── HIGH: Check utility supply, add protection
  └── NORMAL: Continue

Step 2: Check DC bus voltage
  ├── ABNORMAL: Power module issue
  └── NORMAL: Continue

Step 3: Check for overtemperature
  ├── YES: Check fans, filters, ventilation clearance
  └── NO: Continue

Step 4: Check power module status LEDs
  └── Interpret per manufacturer documentation
```

**Common Parts:** Power module, Cooling fan, DC bus capacitor, Fuse
**Typical MTTR:** 3 hours

### 4. Communication Board Issues (28 cases)

**Symptoms:** 4G离线, 网络不通, OCPP断连

**Diagnosis Flow:**
```
Step 1: Check 4G signal strength (should be >-85dBm)
  ├── WEAK: Relocate antenna, check cable
  └── OK: Continue

Step 2: Check SIM card status
  ├── INACTIVE: Contact carrier, replace SIM
  └── ACTIVE: Continue

Step 3: Check communication board LEDs
  ├── NO POWER: Check board power supply
  └── POWER OK: Continue

Step 4: Check antenna connections
  ├── LOOSE: Reconnect, ensure proper torque
  └── OK: May need board replacement
```

**Common Parts:** 4G module, Antenna, SIM card, Communication board
**Typical MTTR:** 1 hour

### 5. Charging Gun/Connector Issues (18 cases)

**Symptoms:** 插枪检测失败, 锁止故障, 温度异常

**Diagnosis Flow:**
```
Step 1: Check PP/CP signal (measure with multimeter)
  ├── ABNORMAL: Check connector pins, cable
  └── NORMAL: Continue

Step 2: Check gun lock mechanism
  ├── STUCK: Check motor, clean mechanism
  └── OK: Continue

Step 3: Check temperature sensor
  ├── OPEN/SHORT: Replace sensor or connector
  └── OK: Continue

Step 4: Visual inspection for damage
  └── Replace if physical damage found
```

**Common Parts:** Charging connector, Lock motor, Temperature sensor, Cable assembly
**Typical MTTR:** 1 hour

## Burned Component Analysis (18 cases)

**Root Causes:**
1. **Loose connections** (45%) - Insufficient torque on terminals
2. **Undersized cables** (25%) - Current capacity exceeded
3. **Poor quality components** (15%) - Counterfeit or substandard parts
4. **Environmental** (15%) - Corrosion, water ingress

**Prevention:**
- Use torque wrench for all connections
- Follow cable sizing specifications exactly
- Source components from approved suppliers
- Ensure proper sealing and ventilation

## Field Service Toolkit

Essential tools:
- Multimeter (True RMS)
- Insulation tester (1000V)
- Torque wrench set
- Thermal camera (optional but recommended)
- Laptop with diagnostic software
- Spare fuses, connectors, cables

## Tool Usage

```bash
cd /path/to/jira-knowledge
python3 tools/hardware_diagnostics.py
```
