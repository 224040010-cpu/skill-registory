# Evidence Fusion - Reference

## Full API

### EvidenceFuser

```python
class EvidenceFuser:
    def __init__(
        self, 
        config: Optional[FusionConfig] = None,
        llm_client: Optional[Any] = None
    ):
        """
        Initialize fuser.
        
        Args:
            config: FusionConfig for options
            llm_client: OpenAI/Anthropic client for LLM fusion
        """
    
    def fuse(self, retrieval_result: RetrievalResult) -> FusionResult:
        """Run full fusion pipeline"""
    
    def fuse_from_evidence(
        self, 
        evidence: list[EvidenceItem], 
        query: str
    ) -> FusionResult:
        """Direct fusion from evidence list"""
    
    def set_llm_client(self, client: Any) -> None:
        """Set LLM client after init"""
```

### FusionConfig

```python
@dataclass
class FusionConfig:
    # Evidence thresholds
    min_evidence_score: float = 0.3
    strong_evidence_threshold: float = 0.7
    max_evidence_items: int = 20
    
    # Confidence thresholds
    high_confidence_threshold: float = 0.8
    medium_confidence_threshold: float = 0.5
    
    # LLM settings
    use_llm_fusion: bool = True
    llm_model: str = "gpt-4"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 2000
    
    # Rule engine settings
    enable_deduplication: bool = True
    enable_same_source_merge: bool = True
    enable_evidence_boosting: bool = True
    
    # Output settings
    max_root_causes: int = 3
    max_actions: int = 5
    generate_ticket: bool = True
```

## Enums

### TicketCategory

```python
class TicketCategory(str, Enum):
    HARDWARE = "hardware"
    SOFTWARE = "software"
    FIRMWARE = "firmware"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    VEHICLE_COMPATIBILITY = "vehicle_compatibility"
    USER_ERROR = "user_error"
    UNKNOWN = "unknown"
```

### TicketPriority

```python
class TicketPriority(str, Enum):
    P1_CRITICAL = "P1"   # Safety issue
    P2_HIGH = "P2"       # Functional issue
    P3_MEDIUM = "P3"     # Minor issue
    P4_LOW = "P4"        # Enhancement
```

### ActionType

```python
class ActionType(str, Enum):
    REMOTE_FIX = "remote_fix"
    FIRMWARE_UPDATE = "firmware_update"
    CONFIG_CHANGE = "config_change"
    HARDWARE_CHECK = "hardware_check"
    HARDWARE_REPLACE = "hardware_replace"
    ESCALATE = "escalate"
    MONITOR = "monitor"
    CONTACT_VEHICLE = "contact_vehicle"
```

### ActionPriority

```python
class ActionPriority(str, Enum):
    IMMEDIATE = "immediate"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
```

## Data Types

### RootCauseCandidate

```python
@dataclass
class RootCauseCandidate:
    candidate_id: str
    cause_summary: str
    cause_detail: str
    cause_category: TicketCategory
    confidence: float
    confidence_level: ConfidenceLevel
    confidence_reasoning: str
    supporting_evidence: list[str]  # Evidence IDs
    related_error_codes: list[str]
    related_cases: list[str]
    related_components: list[str]
    vehicle_specific: bool
    vehicle_info: Optional[dict]
```

### RecommendedAction

```python
@dataclass
class RecommendedAction:
    action_id: str
    action_summary: str
    action_steps: list[str]
    action_type: ActionType
    priority: ActionPriority
    requires_onsite: bool
    requires_parts: list[str]
    estimated_time_minutes: int
    related_cause_id: Optional[str]
    reference_docs: list[str]
    success_criteria: str
```

### TicketPayload

```python
@dataclass
class TicketPayload:
    title: str
    description: str
    category: TicketCategory
    priority: TicketPriority
    component: str
    affected_product: str
    firmware_version: str
    device_sn: str
    site_id: str
    region: str
    vehicle_brand: str
    vehicle_model: str
    root_cause_summary: str
    recommended_action: str
    related_cases: list[str]
    related_error_codes: list[str]
    auto_generated: bool = True
    confidence_score: float = 0.0
    requires_review: bool = True
    
    def to_jira_fields(self) -> dict:
        """Convert to JIRA-compatible format"""
```

## With LLM Client

```python
from openai import OpenAI
from src.fusion import EvidenceFuser, FusionConfig

# OpenAI
config = FusionConfig(llm_model="gpt-4")
client = OpenAI(api_key="...")
fuser = EvidenceFuser(config=config, llm_client=client)

# Anthropic
from anthropic import Anthropic
config = FusionConfig(llm_model="claude-3-opus")
client = Anthropic(api_key="...")
fuser = EvidenceFuser(config=config, llm_client=client)
```

## Rule Engine Details

### Boost Factors

```python
BOOST_FACTORS = {
    "exact_error_code_match": 1.3,
    "case_with_resolution": 1.25,
    "vehicle_specific": 1.2,
    "fmea_match": 1.15,
    "multiple_sources_agree": 1.2,
}
```

### PreFusionResult

```python
@dataclass
class PreFusionResult:
    deduplicated_evidence: list[EvidenceItem]
    merged_evidence: list[EvidenceItem]
    boosted_evidence: list[EvidenceItem]
    processed_evidence: list[EvidenceItem]
    conflicts: list[ConflictInfo]
    original_count: int
    after_dedup_count: int
    has_exact_error_match: bool
    has_case_match: bool
    has_vehicle_specific: bool
```

## Full Pipeline Example

```python
from src.retrieval import RetrievalRouter, RetrievalExecutor
from src.fusion import EvidenceFuser, FusionConfig
from openai import OpenAI

# Setup
router = RetrievalRouter()
executor = RetrievalExecutor()
config = FusionConfig(
    use_llm_fusion=True,
    max_root_causes=3,
    generate_ticket=True,
)
fuser = EvidenceFuser(config=config, llm_client=OpenAI())

# Execute
query = "Charger SN123 shows error 0x3001 with BMW iX, charging fails after SLAC"
plan = router.route(query)
retrieval = executor.execute(plan)
fusion = fuser.fuse(retrieval)

# Results
print(f"Problem: {fusion.problem_summary}")
print(f"Category: {fusion.problem_category.value}")
print(f"Confidence: {fusion.overall_confidence:.0%}")

print("\nRoot Causes:")
for rc in fusion.root_cause_candidates:
    print(f"  [{rc.confidence:.0%}] {rc.cause_summary}")

print("\nActions:")
for action in fusion.recommended_actions:
    print(f"  [{action.priority.value}] {action.action_summary}")
    if action.requires_onsite:
        print(f"    ⚠️ Requires on-site visit")

if fusion.ticket_payload:
    print(f"\nTicket: {fusion.ticket_payload.title}")
    print(f"Priority: {fusion.ticket_payload.priority.value}")
```
