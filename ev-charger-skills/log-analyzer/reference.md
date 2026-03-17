# Log Analyzer - Reference

## Signal Detection Rules

```python
SIGNAL_RULES = {
    "ocpp_disconnect": {
        "pattern": r"OCPP.*disconnect|connection.*lost|backend.*unreachable",
        "severity": "HIGH",
        "category": "communication",
        "action": "Check network connectivity and backend status"
    },
    "slac_timeout": {
        "pattern": r"SLAC.*timeout|PLC.*negotiation.*fail",
        "severity": "HIGH", 
        "category": "handshake",
        "action": "Check PLC module and vehicle compatibility"
    },
    "cp_state_error": {
        "pattern": r"CP.*state.*error|control.*pilot.*abnormal",
        "severity": "MEDIUM",
        "category": "handshake",
        "action": "Check CP circuit and vehicle connector"
    },
    "contactor_fault": {
        "pattern": r"contactor.*fault|contactor.*stuck|relay.*error",
        "severity": "HIGH",
        "category": "electrical",
        "action": "Check contactor coil and drive circuit"
    },
    "temperature_warning": {
        "pattern": r"over.*temp|temperature.*high|thermal.*warning",
        "severity": "MEDIUM",
        "category": "thermal",
        "action": "Check ventilation, fans, and ambient conditions"
    },
    "voltage_error": {
        "pattern": r"voltage.*error|over.*voltage|under.*voltage|mismatch",
        "severity": "HIGH",
        "category": "electrical",
        "action": "Check input supply and power module"
    },
    "bms_timeout": {
        "pattern": r"BMS.*timeout|vehicle.*communication.*fail",
        "severity": "MEDIUM",
        "category": "communication",
        "action": "Usually vehicle-side issue, try different vehicle"
    },
    "meter_error": {
        "pattern": r"meter.*error|energy.*measurement.*fail",
        "severity": "LOW",
        "category": "metering",
        "action": "Check RS485 wiring and meter configuration"
    },
    "emergency_stop": {
        "pattern": r"emergency.*stop|e-stop|急停",
        "severity": "HIGH",
        "category": "safety",
        "action": "Check E-stop button and safety circuit"
    },
    "firmware_error": {
        "pattern": r"firmware.*error|update.*fail|OTA.*fail",
        "severity": "MEDIUM",
        "category": "software",
        "action": "Check network, retry update, or manual recovery"
    },
    "authentication_fail": {
        "pattern": r"auth.*fail|认证.*失败|鉴权.*超时",
        "severity": "MEDIUM",
        "category": "ocpp",
        "action": "Check OCPP configuration and backend"
    }
}
```

## Known JIRA Issue Patterns

| Issue | Pattern | Confidence Threshold |
|-------|---------|---------------------|
| VRC-666 | SLAC timeout + Gun 2 | 60% |
| VRC-3529 | Auth timeout + OCPP 2.0.1 | 55% |
| VRC-3879 | Voltage mismatch | 50% |
| VRC-3989 | 4G disconnect pattern | 55% |

## MAC Address Extraction

```python
def extract_vehicle_from_log(log_content: str) -> dict:
    """Extract vehicle info from MAC address in log."""
    import re
    
    mac_pattern = r'(?:MAC|mac|Mac)[:\s=]*([0-9A-Fa-f:]{17}|[0-9A-Fa-f-]{17})'
    macs = re.findall(mac_pattern, log_content)
    
    if macs:
        from vehicle_compat import identify_vehicle_from_mac
        return identify_vehicle_from_mac(macs[0])
    
    return {'brand': None}
```

## Command Line Usage

```bash
cd /path/to/jira-knowledge

# Analyze a log file
python3 tools/log_analyzer.py path/to/charger_log.txt

# With output report
python3 tools/log_analyzer.py path/to/log.txt analysis_report.txt
```

## RAG Integration

```python
def find_similar_cases(log_content, top_k=5):
    """Find similar cases from RAG knowledge base."""
    # Extract key terms from log
    # Query against case_chunks.jsonl
    # Return ranked matches with scores
```
