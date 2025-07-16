#!/bin/bash

echo "🚀 Setting up Neuron Framework T1 Test Environment..."

# Create project structure
mkdir -p neuron-framework-t1
cd neuron-framework-t1

# Create directory structure
mkdir -p {src/{agents,core,models},tests,data/{test_images,test_cases},config,logs}

echo "📁 Created directory structure"

# Create __init__.py files for Python packages
touch src/__init__.py
touch src/agents/__init__.py
touch src/core/__init__.py
touch src/models/__init__.py
touch tests/__init__.py
touch config/__init__.py

echo "📦 Created Python package structure"

# Initialize Python environment
echo "🐍 Setting up Python virtual environment..."
python -m venv venv

# Activate virtual environment
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

echo "✅ Virtual environment activated"

# Install requirements
echo "📥 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Python packages installed"

# Create .gitignore
cat > .gitignore << EOF
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# Environment variables
.env

# Logs
logs/
*.log

# Test outputs
test_outputs/
*.pytest_cache/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Weave cache
.weave/
EOF

echo "📝 Created .gitignore"

# Set permissions for execution
chmod +x run_t1_test.py

echo ""
echo "🎉 Project setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Add your API keys to .env file:"
echo "   - OPENAI_API_KEY=your_key_here"
echo "   - ANTHROPIC_API_KEY=your_key_here"
echo ""
echo "2. Add test images to data/test_images/:"
echo "   - pristine_car.jpg (undamaged vehicle)"
echo "   - damaged_car.jpg (damaged vehicle)"
echo ""
echo "3. Run the test:"
echo "   python run_t1_test.py"
echo ""
echo "4. Run with pytest:"
echo "   pytest tests/test_t1_system.py -v"
echo ""
echo "🔗 View results in Weave dashboard after running tests"