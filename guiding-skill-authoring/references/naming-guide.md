# Skill Naming Guide — EV Platform

---

## Naming Pattern

```
<verb-ing>-<object>[-<qualifier>]
```

- Lowercase letters, digits, hyphens only: `[a-z0-9-]`
- Maximum 64 characters
- No underscores, no camelCase, no Chinese characters

---

## Verb Taxonomy

Choose the verb that most precisely describes the primary action.
Do not use generic verbs like `handling`, `processing`, `managing` alone.

| Verb | Use for | Examples |
|------|---------|----------|
| `querying` | Read-only data retrieval with a specific answer | `querying-realtime-status`, `querying-charge-records` |
| `diagnosing` | Analysis that identifies a root cause or problem | `diagnosing-charger-faults`, `diagnosing-power-anomalies` |
| `generating` | Creating a document, report, or structured output | `generating-maintenance-reports`, `generating-inspection-report` |
| `analyzing` | Processing data to extract insights (no single answer) | `analyzing-charger-protocols`, `analyzing-energy-consumption` |
| `dispatching` | Routing or assigning tasks/resources | `dispatching-work-orders`, `dispatching-emergency-alerts` |
| `guiding` | Providing step-by-step instructions to a human | `guiding-onsite-maintenance`, `guiding-user-troubleshooting` |
| `evaluating` | Scoring or rating something against criteria | `evaluating-device-reliability`, `evaluating-technician-performance` |
| `planning` | Producing a forward-looking schedule or strategy | `planning-maintenance-schedules`, `planning-capacity-expansion` |
| `notifying` | Sending alerts or messages | `notifying-fault-alerts`, `notifying-sla-breach` |
| `scheduling` | Creating or managing timed tasks | `scheduling-preventive-maintenance`, `scheduling-firmware-update` |
| `validating` | Checking data or config against rules | `validating-ocpp-config`, `validating-installation-checklist` |
| `calculating` | Performing a computation and returning a numeric result | `calculating-energy-cost`, `calculating-mtbf-score` |
| `summarizing` | Condensing existing information into a shorter form | `summarizing-incident-history`, `summarizing-fleet-health` |
| `escalating` | Triggering a higher-priority response or handoff | `escalating-critical-faults`, `escalating-unresolved-tickets` |
| `restarting` | Device control: reboot operations (L4) | `restarting-charger-module` |
| `stopping` | Device control: halt operations (L4) | `stopping-active-session` |

---

## 25+ EV Domain Naming Examples

### Device & Fault Management

| Skill name | What it does |
|------------|-------------|
| `diagnosing-charger-faults` | Analyzes fault codes and telemetry to identify root cause |
| `diagnosing-power-anomalies` | Identifies abnormal power readings (over/under voltage, current) |
| `querying-realtime-status` | Returns current device state and live telemetry |
| `querying-fault-history` | Retrieves historical fault log for a device |
| `querying-charge-records` | Returns charging session records by device or user |
| `evaluating-device-reliability` | Scores device health and recommends repair vs replace |
| `summarizing-incident-history` | Condenses 30-day fault history into a readable summary |

### Maintenance & Work Orders

| Skill name | What it does |
|------------|-------------|
| `dispatching-work-orders` | Creates and assigns maintenance work orders to technicians |
| `guiding-onsite-maintenance` | Provides SOP-based step-by-step repair guidance |
| `planning-maintenance-schedules` | Generates preventive maintenance calendar from device data |
| `scheduling-preventive-maintenance` | Books a specific scheduled maintenance task |
| `validating-installation-checklist` | Checks new installation against commissioning requirements |
| `escalating-critical-faults` | Triggers emergency response for safety-critical fault codes |

### Reporting & Analytics

| Skill name | What it does |
|------------|-------------|
| `generating-maintenance-reports` | Creates structured O&M reports with KPI statistics |
| `generating-inspection-report` | Produces a field inspection report from checklist data |
| `analyzing-energy-consumption` | Analyzes usage patterns and identifies efficiency opportunities |
| `calculating-energy-cost` | Computes charging cost for a session or time period |
| `calculating-mtbf-score` | Derives mean time between failures from fault history |
| `summarizing-fleet-health` | Produces a fleet-level health dashboard summary |

### Knowledge & Protocol

| Skill name | What it does |
|------------|-------------|
| `analyzing-charger-protocols` | Interprets OCPP/Modbus/CAN protocol messages and configs |
| `validating-ocpp-config` | Checks OCPP configuration parameters against spec |
| `querying-sop-procedure` | Retrieves the relevant SOP document for a maintenance task |

### Notifications & Alerts

| Skill name | What it does |
|------------|-------------|
| `notifying-fault-alerts` | Pushes fault alert to operator via Feishu/SMS |
| `notifying-sla-breach` | Alerts when a work order is approaching SLA deadline |
| `dispatching-emergency-alerts` | Sends multi-channel emergency notification for critical events |

### Device Control (L4 — Verify Gate required)

| Skill name | What it does |
|------------|-------------|
| `restarting-charger-module` | Remotely restarts a charging station module |
| `stopping-active-session` | Force-stops a charging session (safety or billing dispute) |

---

## Description Formula Examples

**Formula:**
```
[Third-person description of capability and output].
Use when [trigger scenario with specific keywords].
Do NOT use when [exclusion with pointer to correct skill].
```

**Example 1 — Fault diagnosis:**
```
Diagnoses EV charger faults by retrieving device telemetry, analyzing alarm
codes, correlating historical patterns, and recommending repair actions.
Use when user reports an error code, charging failure, device offline, abnormal
session, or requests fault root-cause analysis.
Do NOT use when user only asks about charging protocols without an active fault
(use analyzing-charger-protocols), or wants to create a work order without
a diagnosis context (use dispatching-work-orders).
```

**Example 2 — Read-only query:**
```
Queries real-time operational status and telemetry for EV charging stations,
returning current state and key metric readings.
Use when user asks about device status, current readings, connectivity state,
fleet overview, or active session status.
Do NOT use when device has an active fault requiring diagnosis (use
diagnosing-charger-faults), or user asks about historical trends (use
generating-maintenance-reports).
```

**Example 3 — Work order dispatch:**
```
Creates maintenance work orders and assigns available technicians based on
proximity, skill qualification, and current load.
Use when a fault has been diagnosed and on-site repair is required, or user
explicitly requests creating a maintenance ticket.
Do NOT use when fault can be resolved remotely, or when querying existing
work order status (use querying-work-order-status).
```

---

## Common Naming Mistakes

| Mistake | Example | Fix |
|---------|---------|-----|
| Too generic | `managing-devices` | `diagnosing-charger-faults` |
| Noun-only | `fault-diagnosis` | `diagnosing-charger-faults` |
| camelCase | `faultDiagnosis` | `diagnosing-charger-faults` |
| Underscore | `fault_diagnosis` | `diagnosing-charger-faults` |
| Contains Chinese | `充电桩-故障诊断` | `diagnosing-charger-faults` |
| Too long (>64 chars) | `automatically-diagnosing-and-resolving-charger-hardware-faults` | `diagnosing-charger-faults` |
| Ownership marker | `ops-team-fault-checker` | `diagnosing-charger-faults` |
| Version in name | `diagnosing-faults-v2` | Use registry version field instead |
