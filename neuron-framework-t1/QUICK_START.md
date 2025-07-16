# T1 Hot-Swap Test - Quick Start Guide

## 🚀 Setup (5 minutes)

### 1. Create Project Structure
```bash
# Run the setup script
chmod +x setup_project.sh
./setup_project.sh
```

### 2. Add API Keys
Edit `.env` file:
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

### Option 1: Direct Execution
```bash
python run_t1_test.py
```

### Option 2: Pytest
```bash
pytest tests/test_t1_system.py -v
```

## 📊 Expected Output

```
🚀 Starting T1 Hot-Swap Test...
📊 Weave Project: neuron-framework-t1-hotswap

🧪 Running 2 test cases...

📊 Running Test 1/2: High confidence conflict between pristine image and total loss text
✅ Success: True
📈 Metrics:
   total_duration: 3.2
   conflict_detection_time: 1.8
   swap_duration: 0.3
   accuracy_preserved: True
   conflict_detected: True
   swap_executed: True

📋 Success Criteria:
   ✅ conflict_detection_under_2s: True
   ✅ swap_under_500ms: True
   ✅ accuracy_within_2pct: True

🎯 T1 Test Summary:
   Total Tests: 2
   Passed: 2
   Success Rate: 100.0%
```

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
- Go to https://wandb.ai/[your-entity]/neuron-framework-t1-hotswap
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