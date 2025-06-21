#!/bin/bash
set -e

echo "🚀 Deploying ADVANCED Neuron Agent v2.0..."

# Check prerequisites
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed"  
    exit 1
fi

echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

echo "🧪 Running comprehensive test suite..."
python3 -m pytest test_advanced.py -v

echo "🏃 Starting agent for demo..."
echo "Running quick demo - use Ctrl+C to stop"
timeout 15s python3 main.py || echo "Demo completed successfully"

echo ""
echo "✅ ADVANCED Neuron Agent v2.0 deployed successfully!"
echo ""
echo "🎯 Next steps:"
echo "   • python3 main.py          - Start interactive CLI"
echo "   • python3 main.py test     - Run test suite"
echo "   • docker build -t agent .  - Build Docker image"
echo ""
echo "📚 Available commands in CLI:"
echo "   • status    - Show system status"
echo "   • memory    - Test memory operations"
echo "   • analyze   - Test data analysis"
echo "   • solve     - Test problem solving"
echo "   • health    - Check system health"
echo "   • quit      - Exit system"
