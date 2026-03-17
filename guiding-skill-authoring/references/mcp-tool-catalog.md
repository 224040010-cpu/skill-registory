# MCP Tool Catalog — Registered Tools

> Maintained by: Platform Engineering
> Last updated: 2026-03
> To request a new tool, file a ticket with the platform team.

Only tools listed here may be referenced in skill `Workflow` sections.
Use the fully-qualified format: `mcp-server-name:tool_name(params)`

---

## device-status-mcp

Read-only device telemetry and status queries. No side effects.

| Tool | Description | Key parameters | Returns |
|------|-------------|----------------|---------|
| `get_device_status` | Current operational state of one station | `device_id: str` | `{status, mode, temperature, firmware_version, last_heartbeat, error_code}` |
| `get_fault_history` | Fault/alarm log for a device over a time window | `device_id: str, days: int` | `[{timestamp, fault_code, severity, resolved}]` |
| `get_realtime_metrics` | Live telemetry readings | `device_id: str` | `{power_kw, voltage_v, current_a, temperature_c, energy_kwh_session}` |
| `list_devices` | List stations matching filter criteria | `area_code?: str, status?: str, model?: str` | `[{device_id, name, location, status}]` |
| `get_charge_session` | Details of a specific or active charging session | `device_id: str, session_id?: str` | `{session_id, start_time, energy_kwh, user_id, status}` |

**Risk level contribution:** L1 (all tools are read-only)

---

## knowledge-base-mcp

Semantic search over the platform knowledge base (fault cases, SOPs, FAQs,
protocol specs). Read-only. All results must cite `source` in skill output.

| Tool | Description | Key parameters | Returns |
|------|-------------|----------------|---------|
| `search_knowledge_base` | Vector search over a knowledge collection | `query: str, collection: str, top_k: int` | `[{content, source, score, metadata}]` |

**Available collections:**

| Collection | Contains |
|------------|----------|
| `fault_cases` | Historical fault diagnoses and root cause analyses |
| `maintenance_sop` | Step-by-step maintenance and repair procedures |
| `fault_codes` | Fault code definitions, severity, typical causes |
| `protocols` | OCPP 1.6/2.0.1, Modbus, CAN, ISO 15118 documentation |
| `faqs` | Customer-facing FAQ content |
| `product_specs` | Device specifications and normal operating ranges |

**Risk level contribution:** L1–L2 (analysis results only)

---

## ticket-system-mcp

Work order creation, assignment, and status management. Write operations.

| Tool | Description | Key parameters | Returns |
|------|-------------|----------------|---------|
| `create_work_order` | Create a new maintenance work order | `station_id: str, issue_type: str, description: str, priority: str` | `{order_id, created_at, status}` |
| `update_work_order` | Update status or add notes to an existing order | `order_id: str, status?: str, notes?: str` | `{success: bool}` |
| `assign_technician` | Assign a technician to a work order | `order_id: str, technician_id: str` | `{success: bool, eta_minutes: int}` |
| `list_available_technicians` | List technicians available in an area | `area_code: str, skill_tags?: [str]` | `[{technician_id, name, distance_km, skill_tags}]` |
| `get_work_order` | Retrieve work order details | `order_id: str` | `{order_id, status, assignee, created_at, description, sla_deadline}` |
| `list_work_orders` | List work orders matching filters | `station_id?: str, status?: str, date_from?: str` | `[{order_id, station_id, status, priority, created_at}]` |

**Risk level contribution:** L3 (creates and modifies records)

---

## notification-mcp

Push notifications to operators, technicians, and customers.

| Tool | Description | Key parameters | Returns |
|------|-------------|----------------|---------|
| `send_feishu_message` | Send message to a Feishu user or group | `target: str, message: str, urgency?: str` | `{sent: bool, timestamp}` |
| `send_sms` | Send SMS to a phone number | `phone: str, message: str` | `{sent: bool, message_id}` |
| `send_in_app_notification` | Push notification to mobile app | `user_id: str, title: str, body: str, action?: str` | `{delivered: bool}` |

**Risk level contribution:** L3 (external communication, non-reversible)

---

## verify-gate-mcp

**Required for all L4 (device control) operations.** Must be called before
any tool that modifies device state.

| Tool | Description | Key parameters | Returns |
|------|-------------|----------------|---------|
| `request_approval` | Submit a control operation for Verify Gate validation | `operation: str, device_id: str, params: dict, requester_id: str` | `{approved: bool, reason?: str, approval_token: str}` |

The `approval_token` returned on approval must be passed to the subsequent
control tool call to prove the operation was gate-checked.

**Risk level contribution:** Required for L4 (does not change level itself)

---

## Prohibited / Not-Yet-Registered

Do not use these in skill workflows. Flag them as ⚠️ Tool needed if required.

| Category | Status |
|----------|--------|
| Direct database queries (SQL, DynamoDB direct) | Prohibited — use registered query tools |
| Payment processing / billing mutations | Not registered — route through billing service |
| Firmware push / OTA trigger | Under review — not yet available |
| User account creation / modification | Not in scope for agent skills |
| Any `platform-admin-*` tools | Internal only, not accessible to skills |

---

## Adding a New Tool

If your skill needs a capability that is not listed above:

1. Do NOT invent a tool name in the skill draft
2. Mark the step: `⚠️ Tool needed: [describe exactly what the tool should do]`
3. Include the tool request in your PR description
4. Platform engineering will evaluate registration timeline

Skills referencing unregistered tools will be blocked at security review.
