# Agents

Intelligence agents that analyze narrative patterns and generate insights.

## Services

| File | Description |
|------|-------------|
| `mutation.py` | Detects narrative spin and evolution |
| `outcome.py` | Traces historical outcomes for prediction |
| `evolution.py` | Multi-temporal landscape comparison |
| `meta.py` | Strategic intelligence synthesis |
| `dominance.py` | Prevalence/velocity metrics calculation |
| `external.py` | External fact-check integration |

## Agent Descriptions

### Mutation Detector
Identifies how narratives change:
- **Siblings**: Same story, different spin (uses Discovery API)
- **Descendants**: Temporal evolution of the same narrative

### Outcome Tracer
Historical pattern analysis:
- Finds narratives >90 days old matching current pattern
- Traces T+7 to T+120 day outcomes using sparse search
- Predicts likely consequences based on precedent

### Evolution Agent
Multi-temporal comparison:
- Creates snapshots at T0 (6mo), T1 (3mo), T2 (1mo), T3 (now)
- Detects emerged, faded, persistent narratives
- Projects future trajectories

### Meta-Synthesis Agent
Generates strategic intelligence reports combining:
- Dominance analysis (prevalence, velocity, diversity)
- Conflict detection (opposing narratives)
- Evolution summary
- Outcome predictions
- External fact-checks

## Usage

```python
from agents.services.mutation import mutation_agent
from agents.services.meta import meta_agent

# Detect mutations
result = mutation_agent.detect_mutations(text="Some narrative...")

# Generate intelligence report
report = meta_agent.generate_report("Artificial Intelligence", days=30)
print(report["final_report_markdown"])
```
