#!/bin/bash
set -e

echo "🚀 Deploying ADVANCED Neuron Agent v2.0..."

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

echo "🧪 Running tests..."
python3 -m pytest test_advanced.py -v

echo "🏃 Starting agent for demo..."
timeout 10s python3 main.py || echo "Demo completed"

echo "✅ ADVANCED Neuron Agent v2.0 deployed successfully!"
