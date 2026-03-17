# Diagnostic Log Parser - Reference

## Log Pattern Regexes

```python
LOG_PATTERNS = {
    'standard': r'^(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+\[?(?P<level>\w+)\]?\s+(?P<module>[\w\.]+)\s*[:\-]?\s*(?P<message>.+)$',
    'syslog': r'^(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(?P<host>\S+)\s+(?P<module>\S+?)(?:\[\d+\])?:\s+(?P<message>.+)$',
    'android': r'^(?P<timestamp>\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\s+(?P<pid>\d+)\s+(?P<tid>\d+)\s+(?P<level>[VDIWEF])\s+(?P<module>\S+)\s*:\s*(?P<message>.+)$',
    'json_line': r'^\{.*\}$',
    'cellular': r'^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[(?P<module>[^\]]+)\]\s+(?P<level>\w+):\s+(?P<message>.+)$',
}
```

## Error Indicators

```python
ERROR_INDICATORS = [
    r'error', r'fail(?:ed|ure)?', r'exception', r'crash',
    r'abort', r'timeout', r'refused', r'denied',
    r'invalid', r'corrupt', r'fault', r'alarm',
    r'警告', r'错误', r'失败',
]
```

## Level Normalization Map

```python
LEVEL_MAP = {
    'V': 'VERBOSE', 'D': 'DEBUG', 'I': 'INFO',
    'W': 'WARNING', 'WARN': 'WARNING',
    'E': 'ERROR', 'ERR': 'ERROR',
    'F': 'FATAL', 'C': 'CRITICAL', 'CRIT': 'CRITICAL'
}
```

## Severity Scores

```python
SEVERITY_MAP = {
    'VERBOSE': 1, 'DEBUG': 2, 'INFO': 3,
    'WARNING': 4, 'ERROR': 5, 'CRITICAL': 6, 'FATAL': 7,
}
```

## Module Categories

```python
MODULE_CATEGORIES = {
    'network': ['cellular', 'wifi', 'bluetooth', 'network', 'socket', 'http', 'tcp', 'udp'],
    'power': ['battery', 'power', 'charging', 'voltage', 'current'],
    'storage': ['disk', 'storage', 'flash', 'sdcard', 'filesystem', 'io'],
    'hardware': ['sensor', 'gps', 'camera', 'display', 'audio', 'motor'],
    'system': ['kernel', 'init', 'service', 'process', 'memory', 'cpu'],
    'application': ['app', 'activity', 'service', 'broadcast'],
}
```

## Timestamp Formats

```python
TIMESTAMP_FORMATS = [
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%d %H:%M:%S.%f',
    '%m-%d %H:%M:%S.%f',
    '%b %d %H:%M:%S',
]
```

## Error Code Extraction Patterns

```python
ERROR_CODE_PATTERNS = [
    r'error[:\s]*(?:code[:\s]*)?([A-Z0-9\-_]+)',
    r'code[:\s]*([A-Z0-9\-_]+)',
    r'\[([A-Z]{2,}\d+)\]',
    r'0x[0-9A-Fa-f]+',
    r'E\d{4,}',
]
```

## Multi-line Log Handling

```python
def parse_multiline_logs(lines, pattern):
    """Handle logs that span multiple lines."""
    events = []
    current_event = None
    continuation_lines = []
    
    for line in lines:
        match = re.match(pattern, line)
        
        if match:
            if current_event:
                if continuation_lines:
                    current_event['message'] += '\n' + '\n'.join(continuation_lines)
                events.append(current_event)
            
            current_event = match.groupdict()
            continuation_lines = []
        else:
            if current_event and line.strip():
                continuation_lines.append(line.rstrip())
    
    if current_event:
        if continuation_lines:
            current_event['message'] += '\n' + '\n'.join(continuation_lines)
        events.append(current_event)
    
    return events
```

## Event Aggregation

```python
def aggregate_events(events, gap_threshold_seconds=300):
    """Group events into sessions based on time gaps."""
    if not events:
        return []
    
    sessions = []
    current_session = [events[0]]
    
    for event in events[1:]:
        prev_time = parse_timestamp(current_session[-1].get('timestamp'))
        curr_time = parse_timestamp(event.get('timestamp'))
        
        if curr_time and prev_time:
            gap = (curr_time - prev_time).total_seconds()
            if gap > gap_threshold_seconds:
                sessions.append(current_session)
                current_session = []
        
        current_session.append(event)
    
    if current_session:
        sessions.append(current_session)
    
    return sessions
```

## RAG Chunk Output Format

```python
{
    'chunk_id': 'log:{source_file}:{log_index}:{content_hash}',
    'source_system': 'diagnostic_log',
    'source_type': 'log_event',
    'title': '{module}: {message[:50]}',
    'text': 'Time: ...\nModule: ...\nLevel: ...\nMessage: ...',
    'language': 'en',
    'tags': {
        'rag_type': 'curated',
        'log_level': '...',
        'module': '...',
        'module_category': '...',
        'severity': 5,
        'error_codes': [],
        'is_fault': True/False,
    },
    'provenance': {
        'source_path': '...',
        'log_line': 123,
        'timestamp': '...',
        'content_hash': '...',
    }
}
```
