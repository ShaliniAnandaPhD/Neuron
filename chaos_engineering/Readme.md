# AI Agent Chaos Engineering Test Suite

A production-ready chaos engineering framework for testing AI agent resilience, recovery mechanisms, and data integrity under catastrophic failures.

## Overview

This test suite simulates real-world failure scenarios to validate that your multi-agent AI system can:
- Detect failures within 1 second
- Recover failed agents within 2 seconds
- Maintain 100% data integrity during failures

## Features

- **Multiple Chaos Injection Types**:
  - Network failures (packet loss, latency)
  - Agent timeouts and crashes
  - Memory pressure and leaks
  - CPU throttling
  - Cascading failures

- **Comprehensive Monitoring**:
  - Real-time failure detection
  - Recovery time measurement
  - Data integrity validation
  - Performance metrics collection

- **Production-Ready**:
  - Async/await architecture
  - Configurable test scenarios
  - Detailed logging and tracing
  - Integration with observability platforms

## Architecture

```
chaos_engineering/
├── __init__.py
├── agent.py              # Agent implementation with health states
├── chaos_injector.py     # Failure injection mechanisms
├── monitor.py            # Health monitoring and detection
├── orchestrator.py       # Recovery orchestration
├── metrics.py           # Metrics collection and reporting
├── test_scenarios.py    # Predefined test scenarios
├── main.py             # Main test runner
└── config.yaml         # Configuration file
```

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure your test scenario in `config.yaml`

3. Run the chaos test:
```bash
python main.py --scenario cascade-failure
```

## Test Scenarios

### 1. Cascade Failure
Tests system resilience when multiple agents fail simultaneously.

### 2. Network Partition
Simulates network splits and communication failures.

### 3. Resource Exhaustion
Tests behavior under memory and CPU pressure.

### 4. Slow Death
Gradual degradation leading to eventual failure.

## Success Criteria

| Metric | Threshold | Description |
|--------|-----------|-------------|
| Detection Time | < 1s | Time to detect agent failure |
| Recovery Time | < 2s | Time to restore failed agents |
| Data Integrity | 100% | No lost tasks during failure |

## Integration

### With Observability Platforms

```python
# Example: W&B Weave integration
from chaos_engineering import ChaosTest
import weave

weave.init('chaos-test')
test = ChaosTest(trace_enabled=True)
results = await test.run_scenario('cascade-failure')
```

### With CI/CD

```yaml
# Example: GitHub Actions
- name: Run Chaos Tests
  run: |
    python main.py --scenario all --report junit
```

## Monitoring

The suite provides real-time monitoring during test execution:

```
[19:52:41] CHAOS: Initiating cascade failure scenario
[19:52:41] CHAOS: Forcing TIMEOUT state for Agent E
[19:52:41] CHAOS: Forcing TIMEOUT state for Agent F
[19:52:41] MONITOR: Failure detected in 0.892s
[19:52:41] RECOVERY: Initiating recovery protocol
[19:52:42] RECOVERY: Recovery complete in 1.2s
[19:52:45] TEST: All tasks processed successfully

┌───────────────────────────────────┐
│         RESILIENCE REPORT         │
└───────────────────────────────────┘
 • Failure Detection: 0.892s [PASSED]
 • Recovery Time: 1.2s [PASSED]
 • Data Integrity: 100% [PASSED]
```

## Configuration

Edit `config.yaml` to customize test parameters:

```yaml
chaos:
  network:
    packet_loss: 0.4  # 40% packet loss
    latency_ms: 500   # Additional latency
  agents:
    failure_count: 2  # Number of agents to fail
    failure_type: timeout
  duration_seconds: 60
```

## Development

To add new chaos scenarios:

1. Create a new scenario in `test_scenarios.py`
2. Implement the injection logic in `chaos_injector.py`
3. Add monitoring rules in `monitor.py`

## License

MIT License