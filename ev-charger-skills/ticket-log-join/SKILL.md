---
name: ticket-log-join
description: Join ticket data with device logs and classify issues. Use this skill when users mention linking tickets to logs, log classification, module/severity mapping, generating RAG-ready ticket+log summaries, correlating device events across time windows, or matching logs by serial number aliases. Trigger even for "find related logs", "device history", or "fault timeline" requests.
bundle_scope: diagnosis-agent
risk_level: L2
---

# Purpose

Link tickets to device logs, classify log content, and emit RAG-ready summaries for troubleshooting.

# Trigger

**Use when:**
- User wants to "link tickets to logs" or "join ticket and log data"
- User asks for "log classification" or "module/severity mapping"
- User needs "RAG-ready ticket+log summaries"
- User mentions "correlate device events", "time window matching"
- User says "find related logs", "device history", "fault timeline"
- User wants to match logs by "serial number aliases"

**Do NOT use when:**
- User only wants to parse logs (use `diagnostic-log-parser`)
- User only wants to analyze logs for faults (use `log-analyzer`)
- User wants to export knowledge packages (use `knowledge-package-exporter`)
- User is searching existing RAG data (use retrieval tools)

# Inputs

- Ticket records/details (JSON/JSONL)
- Log index or log files with module/severity info
- Optional runbook or fault dictionary
- Optional SN alias mapping (for devices with multiple identifiers)

# Workflow

## Step 1: Match Tickets to Logs

Match via SN/device ID using these strategies:

### Direct SN Match
```python
ticket_sn = ticket.get('sn')
matching_logs = [log for log in logs if log.get('sn') == ticket_sn]
```

### SN Alias Handling
Devices may have multiple identifiers (SN, IMEI, MAC, internal ID):
```python
alias_map = {
    "SN123": ["IMEI456", "MAC:AA:BB:CC"],
    "SN789": ["internal_id_xyz"]
}

def resolve_device_ids(ticket_sn, alias_map):
    aliases = alias_map.get(ticket_sn, [])
    return [ticket_sn] + aliases
```

### Time-Window Matching
For logs without explicit ticket IDs:
```python
def find_logs_in_window(ticket_time, logs, window_hours=24):
    window_start = ticket_time - timedelta(hours=window_hours)
    window_end = ticket_time + timedelta(hours=window_hours)
    return [log for log in logs 
            if window_start <= log['timestamp'] <= window_end]
```

Windows:
- **Narrow (±2h)**: Real-time fault correlation
- **Standard (±24h)**: Typical troubleshooting
- **Wide (±7d)**: Intermittent issues or delayed reports

## Step 2: Summarize Logs per Ticket

- Top modules affected
- Severity distribution
- Key error codes
- Time range covered

## Step 3: Attach Classifications

Add log classifications to ticket metadata.

## Step 4: Emit RAG Chunks

Output rules:
- `source_type: ticket` for ticket chunks
- `source_type: log_summary` for aggregated log chunks
- Include `tags` for module, severity, product, region
- Preserve provenance: ticket ID, log file names
- Add `device_ids` array when multiple devices are involved
- Add `time_window` metadata showing the correlation window used

# Multi-Device Scenarios

When a ticket involves multiple devices (e.g., charger + vehicle):
1. Extract ALL device identifiers from the ticket
2. Join logs from each device separately
3. Merge into a unified timeline
4. Tag each log excerpt with its source device

# Reporting

When done, report:
- Ticket count
- Tickets with logs (and match method: exact SN / alias / time-window)
- Total log files joined
- Top modules/severity distribution
- Multi-device ticket count
- Unmatched tickets (with reason)
