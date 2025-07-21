# High-Velocity AI Pipeline

🚀 **Production-grade AI pipeline achieving 66.4ms P99 latency at 595 msg/sec throughput**

A sophisticated neural coordination system with adaptive hot-swapping, designed for high-velocity financial trading and real-time AI processing.

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Performance](https://img.shields.io/badge/P99%20latency-66.4ms-brightgreen.svg)](docs/PERFORMANCE.md)

## 🌟 Key Features

### 🔥 **Adaptive Hot-Swapping**
- **Intelligent agent switching** between OpenAI GPT-4 (quality) and GROQ Llama3 (speed)
- **Real-time performance monitoring** with automatic threshold-based swapping
- **Configurable cooldown periods** to prevent oscillation

### ⚡ **High Performance**
- **P99 latency: 66.4ms** in production testing
- **Throughput: 595+ msg/sec** sustained processing
- **Batch processing** with configurable batch sizes and intervals
- **Circuit breaker protection** for fault tolerance

### 📊 **Comprehensive Monitoring**
- **Real-time metrics** with percentile calculations (P50, P95, P99)
- **CSV export** for analysis and reporting
- **Weave tracing** integration for observability
- **Health monitoring** with automated alerts

### 🏗️ **Production Ready**
- **Docker support** with multi-stage builds
- **Kubernetes manifests** for cloud deployment
- **Configuration management** with environment variable support
- **Graceful shutdown** handling

## 🏁 Quick Start

### Prerequisites
- Python 3.8+ 
- OpenAI API key
- GROQ API key
- (Optional) Weights & Biases API key for tracing

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/your-org/high-velocity-pipeline.git
cd high-velocity-pipeline
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. **Run the pipeline**
```bash
python run_pipeline.py
```

### Development Mode
```bash
python run_pipeline.py --dev
```

### Production Configuration
```bash
python run_pipeline.py --config config/production.json
```

## 📁 Project Structure

```
high-velocity-pipeline/
├── src/                    # Core source code
│   ├── pipeline_core.py    # Main pipeline and hot-swap logic
│   ├── agent_manager.py    # AI agent coordination
│   ├── synthetic_market_data.py  # Market data simulation
│   ├── performance_monitor.py    # Monitoring and metrics
│   ├── config_manager.py   # Configuration system
│   └── circuit_breaker.py  # Fault tolerance
├── config/                 # Configuration files
│   ├── production.json     # Production settings
│   ├── development.json    # Development settings
│   └── benchmark.json      # Benchmark settings
├── scripts/                # Utility scripts
│   ├── monitor_dashboard.py  # Live monitoring
│   ├── health_checker.py   # Health validation
│   └── deployment_utils.py # Deployment automation
├── exports/                # Generated reports and data
├── logs/                   # Application logs
└── docs/                   # Documentation
```

## 🎯 Usage Examples

### Basic Usage
```bash
# Run with default settings
python run_pipeline.py

# Run for specific duration
python run_pipeline.py --duration 300

# Development mode with debug logging
python run_pipeline.py --dev

# High-performance benchmark mode
python run_pipeline.py --benchmark
```

### Configuration
```bash
# Use specific configuration file
python run_pipeline.py --config config/production.json

# Show current configuration
python run_pipeline.py --show-config

# Run health check
python run_pipeline.py --health-check
```

### Monitoring
```bash
# Live dashboard (requires 'rich' library)
python scripts/monitor_dashboard.py

# System health check
python scripts/health_checker.py

# Monitor from exported file
python scripts/monitor_dashboard.py --file exports/pipeline_report_20240101_120000.json
```

## ⚙️ Configuration

### Environment Variables
Key environment variables for configuration:

```bash
# API Keys (Required)
OPENAI_API_KEY=sk-your-openai-key-here
GROQ_API_KEY=gsk_your-groq-key-here
WANDB_API_KEY=your-wandb-key-here  # Optional

# Performance Thresholds
PIPELINE_LATENCY_THRESHOLD_MS=100
PIPELINE_TARGET_THROUGHPUT=800
PIPELINE_MESSAGE_BATCH_SIZE=100

# Agent Configuration
PIPELINE_DEFAULT_AGENT=standard
PIPELINE_MAX_AGENT_SWAPS=50

# Monitoring
PIPELINE_ENABLE_CSV_EXPORT=true
PIPELINE_EXPORT_DIRECTORY=exports
```

### Configuration Files
Use JSON configuration files for complex setups:

```json
{
  "performance_thresholds": {
    "latency_threshold_ms": 100.0,
    "safe_latency_threshold_ms": 70.0,
    "safe_throughput_threshold": 600.0
  },
  "target_performance": {
    "target_throughput": 800.0,
    "message_batch_size": 100
  },
  "agent_configuration": {
    "default_agent": "standard",
    "max_agent_swaps": 50
  }
}
```

## 📊 Performance Metrics

### Achieved Performance (Production Testing)
- **P99 Latency**: 66.4ms
- **P95 Latency**: 45.2ms  
- **Average Throughput**: 595 msg/sec
- **Success Rate**: 98.7%
- **Agent Swaps**: 5 over 70 seconds
- **Total Messages**: 41,728 processed

### Key Performance Indicators
- **Latency Percentiles**: P50, P95, P99 tracking
- **Throughput**: Real-time msg/sec calculation
- **Success Rate**: Request success percentage
- **Agent Efficiency**: Performance comparison between agents
- **System Health**: Circuit breaker status and error rates

## 🔄 Agent Hot-Swapping

The pipeline intelligently switches between two AI agents based on performance:

### Standard Agent (OpenAI GPT-4)
- **Use Case**: High-quality analysis and complex reasoning
- **Typical Latency**: 80-150ms
- **Strengths**: Superior accuracy, complex financial analysis

### Ultra-Fast Agent (GROQ Llama3)
- **Use Case**: High-speed processing and simple tasks
- **Typical Latency**: 20-60ms  
- **Strengths**: Extremely low latency, high throughput

### Swap Triggers
- **Latency Threshold**: Swap to ultra-fast when P99 > 100ms
- **Recovery Conditions**: Swap back when performance normalizes
- **Cooldown Period**: 20-second minimum between swaps
- **Circuit Breaker**: Automatic fallback on failures

## 🏥 Health Monitoring

### Real-time Monitoring
```bash
# Live dashboard
python scripts/monitor_dashboard.py

# Health check
python scripts/health_checker.py --json
```

### Monitoring Features
- **Live Performance Metrics**: Real-time P99, throughput, success rate
- **Agent Status**: Current agent, swap history, performance comparison
- **System Health**: Circuit breaker status, error rates, resource usage
- **Export Capabilities**: CSV, JSON reports for analysis

### Health Check Results
```json
{
  "overall_status": "healthy",
  "health_score": 95,
  "checks": [
    {"name": "configuration", "status": "healthy"},
    {"name": "api_connectivity", "status": "healthy"},
    {"name": "system_resources", "status": "healthy"}
  ]
}
```

## 🚀 Deployment

### Docker Deployment
```bash
# Build image
docker build -t high-velocity-pipeline .

# Run container
docker run -d --env-file .env high-velocity-pipeline

# Docker Compose
docker-compose up -d
```

### Kubernetes Deployment
```bash
# Generate manifests
python scripts/deployment_utils.py generate-manifests

# Deploy to cluster
kubectl apply -f k8s/

# Check status
kubectl get pods -l app=hvp
```

### Production Checklist
- [ ] API keys configured
- [ ] Resource limits set
- [ ] Monitoring enabled
- [ ] Log aggregation configured
- [ ] Health checks passing
- [ ] Backup and recovery tested

## 📈 Performance Tuning

### Key Configuration Parameters
```json
{
  "latency_threshold_ms": 100,      // Swap trigger threshold
  "target_throughput": 800,         // Target messages per second
  "message_batch_size": 100,        // Batch processing size
  "cooldown_period_seconds": 20     // Minimum time between swaps
}
```

### Optimization Tips
1. **Batch Size**: Larger batches improve throughput but increase latency
2. **Swap Thresholds**: Lower thresholds improve responsiveness but may cause oscillation
3. **Resource Limits**: Ensure adequate CPU and memory for target throughput
4. **Network**: Use low-latency connections to AI providers

## 🔧 Development

### Running Tests
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

### Code Quality
```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Development Workflow
1. **Feature Development**: Work in feature branches
2. **Testing**: Add unit tests for new functionality
3. **Integration Testing**: Test with real API calls in dev environment
4. **Performance Testing**: Benchmark against production metrics
5. **Documentation**: Update docs and configuration examples

## 📚 Documentation

- [**Configuration Guide**](docs/CONFIGURATION.md) - Detailed configuration options
- [**Deployment Guide**](docs/DEPLOYMENT.md) - Production deployment instructions
- [**Monitoring Guide**](docs/MONITORING.md) - Monitoring and observability
- [**Troubleshooting**](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [**API Reference**](docs/API.md) - Code documentation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Contribution Guidelines
- Follow existing code style and conventions
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass before submitting

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI** for GPT-4 API access
- **GROQ** for ultra-fast inference capabilities
- **Weights & Biases** for Weave tracing platform
- **Python Community** for excellent async libraries

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-org/high-velocity-pipeline/issues)
- **Documentation**: [Project Wiki](https://github.com/your-org/high-velocity-pipeline/wiki)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/high-velocity-pipeline/discussions)

---

⭐ **Star this repository** if you find it useful!

Built with ❤️ for high-velocity AI processing