# Vehicle Compatibility RAG - Reference

## Data Loading

```python
import json
from pathlib import Path

def load_vehicle_rag_data(base_path: str):
    """Load all vehicle RAG data files."""
    data = {
        'rules': [],
        'relationships': [],
        'mac_rules': []
    }
    
    base = Path(base_path)
    
    # Load rules
    rules_file = base / 'rag_data' / 'rules' / 'rules_vehicle_compatibility.jsonl'
    if rules_file.exists():
        with open(rules_file, 'r') as f:
            data['rules'] = [json.loads(line) for line in f if line.strip()]
    
    # Load relationships
    rel_file = base / 'rag_data' / 'vehicle_compatibility' / 'relationships_vehicle.jsonl'
    if rel_file.exists():
        with open(rel_file, 'r') as f:
            data['relationships'] = [json.loads(line) for line in f if line.strip()]
    
    # Load MAC rules
    mac_file = base / 'rag_data' / 'rules' / 'rules_mac_patterns.jsonl'
    if mac_file.exists():
        with open(mac_file, 'r') as f:
            data['mac_rules'] = [json.loads(line) for line in f if line.strip()]
    
    return data
```

## Building Index

```python
def build_vehicle_index(data: dict) -> dict:
    """Build lookup indices for fast retrieval."""
    index = {
        'by_vehicle': {},      # vehicle_name -> chunks
        'by_charger': {},      # charger_model -> chunks  
        'by_error': {},        # error_code -> chunks
        'by_mac_prefix': {},   # mac_prefix -> brand
        'by_brand': {}         # brand -> vehicle chunks
    }
    
    # Index rules
    for rule in data['rules']:
        conditions = rule.get('conditions', {})
        
        if conditions.get('vehicle'):
            v = conditions['vehicle'].lower()
            index['by_vehicle'].setdefault(v, []).append(rule)
        
        if conditions.get('charger'):
            c = conditions['charger'].upper()
            index['by_charger'].setdefault(c, []).append(rule)
        
        if rule.get('error_codes'):
            for code in rule['error_codes']:
                index['by_error'].setdefault(code, []).append(rule)
    
    # Index relationships
    for rel in data['relationships']:
        entity_type = rel.get('entity_type', '')
        
        if entity_type == 'vehicle':
            v = rel.get('entity', '').lower()
            index['by_vehicle'].setdefault(v, []).append(rel)
            
            brand = rel.get('tags', {}).get('vehicle_brand', '')
            if brand:
                index['by_brand'].setdefault(brand.lower(), []).append(rel)
    
    # Index MAC patterns
    for rule in data['mac_rules']:
        for pattern in rule.get('mac_patterns', []):
            prefix = pattern.get('prefix', '')
            if prefix:
                index['by_mac_prefix'][prefix] = pattern
    
    return index
```

## Query Functions

### Compatibility Query

```python
def query_compatibility(index: dict, vehicle: str, charger: str) -> dict:
    """Query vehicle-charger compatibility."""
    vehicle_lower = vehicle.lower()
    charger_upper = charger.upper()
    
    # Check direct vehicle match
    vehicle_chunks = index['by_vehicle'].get(vehicle_lower, [])
    
    for chunk in vehicle_chunks:
        if chunk.get('source_type') == 'rule' and chunk.get('rule_type') == 'compatibility':
            if chunk.get('conditions', {}).get('charger', '').upper() == charger_upper:
                return chunk.get('result', {})
    
    # Check relationships
    for chunk in vehicle_chunks:
        if chunk.get('source_type') == 'relationship':
            for rel in chunk.get('relationships', []):
                if rel.get('type') == 'compatible_with':
                    if rel.get('target', '').upper() == charger_upper:
                        return {
                            'compatible': True,
                            'success_rate': rel.get('properties', {}).get('success_rate'),
                            'source': 'relationship'
                        }
    
    return {'compatible': 'unknown'}
```

### MAC Address Query

```python
def query_mac(index: dict, mac_address: str) -> dict:
    """Query vehicle from MAC address."""
    mac_clean = mac_address.replace(':', '').replace('-', '').upper()
    prefix = mac_clean[:6]
    
    pattern = index['by_mac_prefix'].get(prefix)
    if pattern:
        return {
            'brand': pattern.get('brand'),
            'model': pattern.get('model'),
            'confidence': 'high'
        }
    
    return {'brand': None, 'confidence': 'low'}
```

## Data Source Files

```
feishu-mcp/
├── scripts/
│   ├── extract_vehicle_compatibility.py   # Extract from Excel
│   ├── build_vehicle_relationships.py     # Build relationships
│   └── generate_vehicle_rules.py          # Generate rules
├── download/chrome-scan/
│   └── rag_data/
│       ├── vehicle_compatibility/
│       │   └── relationships_vehicle.jsonl
│       └── rules/
│           ├── rules_vehicle_compatibility.jsonl
│           └── rules_mac_patterns.jsonl
└── VEHICLE_COMPATIBILITY_RAG_PLAN.md      # Full documentation
```

## Excel Source Data (车桩兼容专项一览与进展同步.xlsx)

| Sheet | Records |
|-------|---------|
| 车型清单（EU） | 515 EU vehicles tested |
| 车型清单（US） | 175 US vehicles |
| CARA（95.45%） | 161 market share data |
| 车辆MAC与特征值 | 323 MAC patterns |
| 单点问题分析与解决清单 | 31 issue→solution |
| 问题分析 | 15 root cause analyses |
