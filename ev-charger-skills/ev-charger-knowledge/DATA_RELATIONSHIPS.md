# EV Charger Knowledge - Relationship Data

## Entity Relationships

### 1. Error Code Relationships

```yaml
Error_0x3001:
  name: "SLAC Communication Timeout"
  severity: medium
  relationships:
    - type: triggered_by
      targets: [PLC_failure, cable_issue, vehicle_incompatibility]
    - type: more_frequent_in
      targets: [BMW_iX, BMW_i4, cold_weather]
    - type: resolved_by
      targets: [firmware_update, cable_check, vehicle_change]
    - type: related_to
      targets: [Error_0x3002, Error_0x4001]

Error_0x3002:
  name: "CP State Error"
  severity: medium
  relationships:
    - type: triggered_by
      targets: [connector_damage, CP_circuit_fault]
    - type: resolved_by
      targets: [connector_inspection, CP_repair]

Error_0x4001:
  name: "BMS Communication Timeout"
  severity: medium
  relationships:
    - type: triggered_by
      targets: [vehicle_BMS_issue, CAN_bus_fault]
    - type: resolved_by
      targets: [try_different_vehicle, check_CAN_wiring]
    - type: usually_caused_by
      targets: [vehicle_side_issue]

Error_0x5001:
  name: "Emergency Stop Activated"
  severity: high
  relationships:
    - type: triggered_by
      targets: [E_stop_button_pressed]
    - type: resolved_by
      targets: [release_E_stop, check_safety_circuit]
```

### 2. Vehicle-Charger Relationships

```yaml
BMW_iX:
  type: vehicle
  brand: BMW
  relationships:
    - type: compatible_with
      target: DH480
      properties:
        success_rate: 89.5
        region: EU
        confidence: high
    - type: compatible_with
      target: DH240
      properties:
        success_rate: 91.2
        region: EU
    - type: has_known_issue
      target: SLAC_timeout
      properties:
        frequency: high
        cause: PLC_timing_sensitivity
    - type: identified_by
      target: MAC_prefix_XX
      properties:
        confidence: medium

BMW_i4:
  type: vehicle
  brand: BMW
  relationships:
    - type: compatible_with
      target: DH480
      properties:
        success_rate: 88
    - type: has_known_issue
      target: SLAC_timeout
      properties:
        frequency: high
    - type: shares_platform_with
      target: BMW_iX

Tesla_Model_3:
  type: vehicle
  brand: Tesla
  relationships:
    - type: compatible_with
      target: DH480
      properties:
        success_rate: 94
    - type: has_known_issue
      target: SLAC_low_temp
      properties:
        frequency: medium
        condition: temperature_below_0C
    - type: identified_by
      target: MAC_4C:FC:AA
      properties:
        confidence: high

VW_ID4:
  type: vehicle
  brand: Volkswagen
  relationships:
    - type: compatible_with
      target: DH480
      properties:
        success_rate: 92
    - type: has_known_issue
      target: firmware_compatibility
      properties:
        frequency: medium
    - type: requires
      target: vehicle_firmware_2.1

Hyundai_Ioniq5:
  type: vehicle
  brand: Hyundai
  relationships:
    - type: compatible_with
      target: DH480
      properties:
        success_rate: 93
    - type: has_known_issue
      target: cable_connection_sensitivity
      properties:
        frequency: low
```

### 3. Issue-Solution Relationships

```yaml
SLAC_timeout:
  type: issue
  relationships:
    - type: affects_vehicles
      targets: [BMW_iX, BMW_i4, BMW_i7]
    - type: has_error_code
      target: "0x3001"
    - type: resolved_by
      target: firmware_update_2.1
      properties:
        effectiveness: high
        for_vehicles: [BMW]
    - type: resolved_by
      target: cable_check
      properties:
        effectiveness: medium
        for_all: true

display_black_screen:
  type: issue
  relationships:
    - type: caused_by
      targets: [12V_power_loss, display_cable_disconnect, APK_crash]
    - type: resolved_by
      targets: [power_check, cable_reseat, hard_reboot]
    - type: similar_to
      targets: [display_garbled, touch_not_working]

charging_stops_80_percent:
  type: issue
  relationships:
    - type: caused_by
      targets: [BMS_SOC_limit, BMS_timeout, temperature_limit]
    - type: resolved_by_checking
      targets: [vehicle_charge_limit_setting, BMS_logs, temperature]
    - type: referenced_in
      targets: [VRC-3879, VRC-4102]
```

### 4. Component-Failure Relationships

```yaml
PLC_module:
  type: component
  relationships:
    - type: failure_causes
      targets: [SLAC_timeout, handshake_failure]
    - type: diagnosed_by
      targets: [LED_status_check, log_analysis]
    - type: replaced_following
      target: spare_part_guide_DH480

contactor:
  type: component
  relationships:
    - type: failure_causes
      targets: [Error_0x3003, charging_stops_unexpectedly]
    - type: diagnosed_by
      targets: [coil_resistance_check, drive_circuit_test]
    - type: FMEA_record
      target: FMEA_292

power_module:
  type: component
  relationships:
    - type: failure_causes
      targets: [Error_305F, power_output_low]
    - type: diagnosed_by
      targets: [version_check, voltage_measurement]
```

### 5. Document Relationships

```yaml
DH480_Installation_Guide:
  type: document
  relationships:
    - type: covers_product
      target: DH480
    - type: contains_procedures
      targets: [installation, commissioning, verification]
    - type: links_to
      targets: [DH480_Maintenance_Guide, DH480_Spare_Part_Guide]
    - type: source
      target: feishu_wiki

DH480_Maintenance_Guide:
  type: document
  relationships:
    - type: covers_product
      target: DH480
    - type: contains_procedures
      targets: [preventive_maintenance, inspection_schedule]
    - type: references
      targets: [error_code_list, alarm_code_list]
```

## Relationship Types Reference

| Type | Description | Example |
|------|-------------|---------|
| `compatible_with` | Vehicle works with charger | BMW_iX → DH480 |
| `has_known_issue` | Entity has documented issue | BMW_iX → SLAC_timeout |
| `resolved_by` | Issue fixed by action | SLAC_timeout → firmware_update |
| `triggered_by` | Error caused by condition | 0x3001 → PLC_failure |
| `identified_by` | Entity identified via method | Tesla → MAC_4C:FC:AA |
| `more_frequent_in` | Error more common with | 0x3001 → BMW_vehicles |
| `caused_by` | Issue has root cause | black_screen → 12V_loss |
| `related_to` | Entities are connected | 0x3001 → 0x3002 |
| `covers_product` | Document about product | Guide → DH480 |
| `contains_procedures` | Document has steps | Guide → installation |

## Query Examples Using Relationships

### Find solutions for error + vehicle combination

```
Query: Error 0x3001 on BMW iX

Traverse:
1. Error_0x3001 --[more_frequent_in]--> BMW_iX ✓ (confirms known issue)
2. Error_0x3001 --[resolved_by]--> firmware_update
3. BMW_iX --[has_known_issue]--> SLAC_timeout (same issue)
4. SLAC_timeout --[resolved_by]--> firmware_update_2.1

Result: Known issue, update firmware to 2.1+
```

### Find related issues from symptom

```
Query: Charging stops unexpectedly

Traverse:
1. Find issues matching symptom
2. charging_stops --[caused_by]--> [contactor_fault, BMS_timeout, ...]
3. For each cause, get resolution
4. contactor_fault --[resolved_by]--> contactor_check
5. BMS_timeout --[resolved_by]--> try_different_vehicle

Result: Multiple possible causes with resolutions
```

### Build diagnosis chain

```
Query: Black screen on DH480

Traverse:
1. display_black_screen --[caused_by]--> 12V_power_loss
2. 12V_power_loss --[diagnosed_by]--> voltage_measurement
3. display_black_screen --[caused_by]--> display_cable_disconnect
4. display_cable_disconnect --[diagnosed_by]--> visual_inspection
5. DH480 --[documented_in]--> DH480_Maintenance_Guide

Result: Ordered diagnosis steps with documentation reference
```
