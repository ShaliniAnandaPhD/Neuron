# T1 Hot-Swap Test - Quick Start Guide

## 🚀 Setup (5 minutes)

### 1. Create Project Structure
```bash
# Run the setup script
chmod +x setup_project.sh
./setup_project.sh
```

### 2. Add API Keys
Copy `.env.example` to `.env` and fill in your keys:
```bash
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
WEAVE_PROJECT_NAME=neuron-framework-t1-hotswap
WEAVE_ENTITY=your-wandb-entity
```

### 3. Add Test Images
```bash
# Add these files to data/test_images/
# - pristine_car.jpg (clean, undamaged vehicle)
# - damaged_car.jpg (moderately damaged vehicle)

# You can download from:
# - Unsplash: https://unsplash.com/s/photos/car
# - Pexels: https://www.pexels.com/search/car/
```

## 🧪 Run Tests

### Unit tests (no API keys needed)
```bash
python -m pytest tests -v
```
The OpenAI and Anthropic clients are mocked. The live end-to-end test is
skipped unless you opt in (below).

### Live T1 run (calls the real APIs)
```bash
python run_t1_test.py
# or, through pytest:
RUN_LIVE_T1=1 python -m pytest tests/test_t1_system.py -v
```

### Models
| Role | Default | Override with |
|------|---------|---------------|
| Primary vision model (OpenAI) | `gpt-5.6-sol` | `PRIMARY_VISION_MODEL`, `PRIMARY_VISION_REASONING_EFFORT` (default `none`) |
| Fallback vision model (Claude) | `claude-sonnet-5-5` | `FALLBACK_VISION_MODEL`, `FALLBACK_VISION_EFFORT` (default `low`) |

These replace the retired `gpt-4-vision-preview` and `claude-3-sonnet-20240229`.
The Claude call enables server-side refusal fallback (`fallbacks: "default"`),
so if a safety classifier declines a request the API retries it on another
Claude model within the same call. Weave tracing is optional: without the
`weave` package installed, the agents run and log events to the standard logger.



## 🎯 Success Criteria

T1 passes when ALL criteria are met:

| Criterion | Target | Measures |
|-----------|--------|----------|
| **Conflict Detection** | < 2 seconds | Time from input to conflict alert |
| **Model Swap** | < 500ms | Fallback model execution time |
| **Accuracy Preservation** | ±2% | Confidence delta between models |

## 🔍 Troubleshooting

### Common Issues:

**1. Import Errors**
```bash
# Ensure you're in project root and venv is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**2. API Key Issues**
```bash
# Check .env file exists and has correct keys
cat .env
# Ensure no spaces around = in .env file
```

**3. Missing Images**
```bash
# Use mock data for initial testing
# Real images required for production validation
```

**4. Weave Connection Issues**
```bash
# Login to Weights & Biases
wandb login
# Or set WANDB_API_KEY in .env
```

## 📈 View Results

1. **Console Output**: Real-time test results
2. **Weave Dashboard**: Detailed traces and metrics
3. **Log Files**: Stored in `logs/` directory

### Weave Dashboard
- Go to https://wandb.ai/[------]/neuron-framework-t1-hotswap
- View execution traces, timing metrics, and model comparisons
- Analyze conflict detection patterns and swap efficiency

## 🔧 Customization

### Adjust Test Parameters
Edit `config/config.py`:
```python
CONFIDENCE_THRESHOLD = 0.8  # Conflict detection sensitivity
SWAP_TIMEOUT = 5.0         # Max swap time (seconds)
ACCURACY_TOLERANCE = 0.02   # ±2% accuracy requirement
```

### Add More Test Cases
Edit `tests/test_t1_system.py`:
```python
def generate_test_cases():
    return [
        # Add your test cases here
        {
            'id': 'custom_test',
            'description': 'Your custom scenario',
            'claim_data': {
                'claim_id': 'CUSTOM_001',
                'visual_evidence': your_image_data,
                'text_description': 'Your damage description',
                'metadata': {'expected_conflict': True}
            }
        }
    ]
```

## 🎉 Next Steps

After T1 passes:
1. **Run T2**: Multi-agent consensus testing
2. **Scale Testing**: Increase test case volume
3. **Production Deploy**: Use results for deployment decisions
4. **Monitor**: Set up continuous monitoring

## 📞 Support

If you encounter issues:
1. Check the console output for error details
2. Review Weave traces for execution flow
3. Verify API keys and network connectivity
4. Ensure all dependencies are installed correctly
