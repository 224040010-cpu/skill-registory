# EV Charger Knowledge - Lookup Tables

This file contains structured data that agents can parse directly.

## Error Code Lookup Table

```json
{
  "0x3001": {
    "name": "SLAC Communication Timeout",
    "description": "PLC handshake failed within timeout period",
    "severity": "medium",
    "trigger": "No SLAC response from vehicle",
    "solution": "Check cable, PLC module, vehicle compatibility",
    "vehicle_specific": {
      "BMW": "Update firmware to 2.1+",
      "Tesla": "Normal at low temp, retry after warmup",
      "VW": "Check vehicle firmware >= 2.1"
    },
    "related_codes": ["0x3002", "0x4001"]
  },
  "0x3002": {
    "name": "CP State Error",
    "description": "Control pilot signal abnormal",
    "severity": "medium",
    "trigger": "CP voltage not in expected range",
    "solution": "Check connector, CP circuit",
    "related_codes": ["0x3001", "0x3003"]
  },
  "0x3003": {
    "name": "Contactor Failure",
    "description": "Contactor stuck or not responding",
    "severity": "high",
    "trigger": "Contactor feedback mismatch",
    "solution": "Check contactor coil and drive circuit"
  },
  "0x4001": {
    "name": "BMS Communication Timeout",
    "description": "No response from vehicle BMS",
    "severity": "medium",
    "trigger": "CAN bus communication timeout",
    "solution": "Usually vehicle-side issue, try different vehicle"
  },
  "0x4002": {
    "name": "Voltage Mismatch",
    "description": "Battery voltage out of expected range",
    "severity": "medium",
    "trigger": "SOC/voltage calculation mismatch",
    "solution": "Check battery SOC and charger config"
  },
  "0x5001": {
    "name": "Emergency Stop Activated",
    "description": "E-stop button pressed",
    "severity": "high",
    "trigger": "Safety circuit open",
    "solution": "Release E-stop button, check safety circuit"
  },
  "0x5002": {
    "name": "Ground Fault Detected",
    "description": "RCD tripped",
    "severity": "high",
    "trigger": "Leakage current exceeded threshold",
    "solution": "Check wiring, RCD, and grounding"
  },
  "305F": {
    "name": "Power Module Version Mismatch",
    "description": "Module firmware version incompatible",
    "severity": "medium",
    "trigger": "Version check failed at startup",
    "solution": "Upgrade power module firmware"
  },
  "604B": {
    "name": "Meter Communication Error",
    "description": "RS485 communication with meter failed",
    "severity": "low",
    "trigger": "No response from energy meter",
    "solution": "Check RS485 wiring, meter address config"
  },
  "708": {
    "name": "RPC Service Offline",
    "description": "DLL service crashed",
    "severity": "medium",
    "trigger": "Service watchdog timeout",
    "solution": "Restart charger, check for software updates"
  },
  "720": {
    "name": "RPC Communication Failed",
    "description": "Internal communication error",
    "severity": "medium",
    "trigger": "DLL communication timeout",
    "solution": "Restart service, check system logs"
  }
}
```

## Vehicle Compatibility Table

```json
{
  "BMW_iX": {
    "brand": "BMW",
    "compatible_chargers": {
      "DH480": {"success_rate": 89.5, "region": "EU"},
      "DH240": {"success_rate": 91.2, "region": "EU"},
      "DS480": {"success_rate": 88.7, "region": "EU"}
    },
    "known_issues": [
      {"issue": "SLAC timeout", "frequency": "high", "solution": "Firmware 2.1+"}
    ],
    "notes": "PLC timing sensitivity, needs recent firmware"
  },
  "BMW_i4": {
    "brand": "BMW",
    "compatible_chargers": {
      "DH480": {"success_rate": 88.0},
      "DH240": {"success_rate": 90.0}
    },
    "known_issues": [
      {"issue": "SLAC timeout", "frequency": "high", "solution": "Firmware 2.1+"}
    ],
    "notes": "Similar to iX, shares platform"
  },
  "Tesla_Model_3": {
    "brand": "Tesla",
    "compatible_chargers": {
      "DH480": {"success_rate": 94.2},
      "DH240": {"success_rate": 95.0},
      "DS480": {"success_rate": 93.5}
    },
    "known_issues": [
      {"issue": "SLAC timing at low temp", "frequency": "medium", "condition": "<0°C"}
    ],
    "mac_prefix": "4C:FC:AA",
    "notes": "Generally stable, some cold weather issues"
  },
  "Tesla_Model_Y": {
    "brand": "Tesla",
    "compatible_chargers": {
      "DH480": {"success_rate": 94.0},
      "DH240": {"success_rate": 95.0}
    },
    "known_issues": [
      {"issue": "SLAC timing at low temp", "frequency": "medium"}
    ],
    "mac_prefix": "4C:FC:AA",
    "notes": "Same as Model 3"
  },
  "VW_ID4": {
    "brand": "Volkswagen",
    "compatible_chargers": {
      "DH480": {"success_rate": 92.0},
      "DH240": {"success_rate": 93.0},
      "DS480": {"success_rate": 91.0}
    },
    "known_issues": [
      {"issue": "Firmware compatibility", "frequency": "medium", "requirement": "Vehicle FW >= 2.1"}
    ],
    "notes": "Check vehicle firmware version"
  },
  "Hyundai_Ioniq5": {
    "brand": "Hyundai",
    "compatible_chargers": {
      "DH480": {"success_rate": 93.0},
      "DH240": {"success_rate": 94.0}
    },
    "known_issues": [
      {"issue": "Cable connection sensitivity", "frequency": "low"}
    ],
    "notes": "Ensure good cable connection"
  },
  "Porsche_Taycan": {
    "brand": "Porsche",
    "compatible_chargers": {
      "DH480": {"success_rate": 96.0},
      "DS480": {"success_rate": 95.0}
    },
    "known_issues": [],
    "notes": "High power draw, verify charger capacity"
  }
}
```

## Symptom → Diagnosis Table

```json
{
  "charging_stops_unexpectedly": {
    "possible_causes": [
      {"cause": "BMS communication timeout", "likelihood": "high", "error_code": "0x4001"},
      {"cause": "Contactor fault", "likelihood": "medium", "error_code": "0x3003"},
      {"cause": "Ground fault", "likelihood": "medium", "error_code": "0x5002"},
      {"cause": "Temperature limit", "likelihood": "low"}
    ],
    "diagnostic_steps": [
      "Check for error codes on display",
      "Review logs for BMS messages",
      "Check contactor click sound",
      "Measure temperature"
    ]
  },
  "charging_stops_at_80_percent": {
    "possible_causes": [
      {"cause": "Vehicle SOC limit setting", "likelihood": "high"},
      {"cause": "BMS SOC limit", "likelihood": "medium"},
      {"cause": "Voltage mismatch at high SOC", "likelihood": "medium", "error_code": "0x4002"}
    ],
    "diagnostic_steps": [
      "Check vehicle charge limit setting",
      "Review BMS logs around stop time",
      "Try different vehicle"
    ],
    "similar_cases": ["VRC-3879", "VRC-4102"]
  },
  "black_screen": {
    "possible_causes": [
      {"cause": "Display cable disconnected", "likelihood": "high"},
      {"cause": "12V/24V power supply issue", "likelihood": "high"},
      {"cause": "Display panel failure", "likelihood": "medium"},
      {"cause": "APK crash", "likelihood": "medium"}
    ],
    "diagnostic_steps": [
      "Check if status LED is on",
      "Listen for fans/relays",
      "Check display cable connection",
      "Measure auxiliary power voltage",
      "Try hard reboot (hold 30s)"
    ]
  },
  "touch_not_responding": {
    "possible_causes": [
      {"cause": "Touch controller fault", "likelihood": "medium"},
      {"cause": "Screen surface contamination", "likelihood": "medium"},
      {"cause": "Touch panel failure", "likelihood": "low"}
    ],
    "diagnostic_steps": [
      "Clean screen surface",
      "Check touch controller connection",
      "Reboot system"
    ]
  },
  "network_offline": {
    "possible_causes": [
      {"cause": "4G signal weak", "likelihood": "high"},
      {"cause": "SIM card issue", "likelihood": "medium"},
      {"cause": "Backend unreachable", "likelihood": "medium"},
      {"cause": "Antenna problem", "likelihood": "low"}
    ],
    "diagnostic_steps": [
      "Check signal strength (> -85dBm)",
      "Verify SIM card active",
      "Check backend URL configuration",
      "Inspect antenna connection"
    ]
  }
}
```

## Product Specifications Table

```json
{
  "DH480": {
    "type": "DC Fast Charger",
    "power": "480kW",
    "protocol": ["CCS1", "CCS2"],
    "guns": 2,
    "installation_guide": "feishu:wiki:I7UHwr6hIiOMf0kf6tbcap2sn1f",
    "maintenance_guide": "feishu:wiki:Ccl7wk2vwiwb07kjgLvcNygQn4b",
    "spare_parts_guide": "feishu:wiki:TKyYw0BBWiHRUBk5polcpFZ7nwh"
  },
  "DH240": {
    "type": "DC Fast Charger",
    "power": "240kW",
    "protocol": ["CCS1", "CCS2"],
    "guns": 2,
    "acceptance_guide": "feishu:wiki:PM1AwZftIiBjHok6pKzcw1RRnob",
    "maintenance_guide": "feishu:wiki:Dzqlwf3qviW2kokzLlicBm6cnmc"
  },
  "DS480": {
    "type": "DC Split Charger",
    "power": "480kW",
    "protocol": ["CCS1", "CCS2"],
    "configuration": "Split system",
    "installation_guide": "feishu:wiki:JAQNwGnRwi4ygVkf57ecE4oPnvf"
  },
  "AC_Ultra": {
    "type": "AC Charger",
    "power": "22kW",
    "protocol": ["Type2"],
    "installation_guide": "feishu:wiki:NYrpwGGiHiXeFRkhE4ycbOvEnJ8",
    "maintenance_guide": "feishu:wiki:LXjYwg3H4iFdtckTnAvcnrPnnae"
  }
}
```

## Usage Example

```python
# Agent can parse this file directly
import json
import re

def load_lookup_tables(skill_file_path):
    """Load lookup tables from the skill file."""
    with open(skill_file_path, 'r') as f:
        content = f.read()
    
    tables = {}
    
    # Extract JSON blocks
    json_blocks = re.findall(r'```json\n(.*?)\n```', content, re.DOTALL)
    
    table_names = ['error_codes', 'vehicles', 'symptoms', 'products']
    for i, block in enumerate(json_blocks):
        if i < len(table_names):
            tables[table_names[i]] = json.loads(block)
    
    return tables

# Usage
tables = load_lookup_tables('~/.cursor/skills/ev-charger-knowledge/LOOKUP_TABLES.md')
error = tables['error_codes'].get('0x3001')
print(error['solution'])
```
