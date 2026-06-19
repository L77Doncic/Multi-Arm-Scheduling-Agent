#!/bin/bash

# Multi-Arm Scheduling Agent Setup Script
# This script sets up the development environment

set -e  # Exit on error

echo "=========================================="
echo "Multi-Arm Scheduling Agent Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10.0"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    print_status "Python version $python_version is compatible"
else
    print_error "Python version $python_version is too old. Required: $required_version or higher"
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    print_warning "Virtual environment already exists"
    read -p "Do you want to recreate it? (y/N): " recreate
    if [ "$recreate" = "y" ] || [ "$recreate" = "Y" ]; then
        rm -rf venv
        python3 -m venv venv
        print_status "Virtual environment recreated"
    fi
else
    python3 -m venv venv
    print_status "Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate
print_status "Virtual environment activated"

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip
print_status "pip upgraded"

# Install requirements
echo ""
echo "Installing dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    print_status "Dependencies installed"
else
    print_warning "requirements.txt not found, skipping dependency installation"
fi

# Install project in development mode
echo ""
echo "Installing project in development mode..."
if [ -f "setup.py" ]; then
    pip install -e ".[dev]"
    print_status "Project installed in development mode"
else
    print_warning "setup.py not found, skipping project installation"
fi

# Create necessary directories
echo ""
echo "Creating output directories..."
mkdir -p outputs/{videos,logs,results,generated_code}
mkdir -p data/{datasets,scenarios}
print_status "Output directories created"

# Check for configuration files
echo ""
echo "Checking configuration files..."
if [ -f "configs/agent_config.yaml" ]; then
    print_status "Agent configuration found"
else
    print_warning "Agent configuration not found"
fi

if [ -f "configs/simulation_config.yaml" ]; then
    print_status "Simulation configuration found"
else
    print_warning "Simulation configuration not found"
fi

# Check for environment variables
echo ""
echo "Checking environment variables..."
if [ -n "$OPENAI_API_KEY" ]; then
    print_status "OPENAI_API_KEY is set"
else
    print_warning "OPENAI_API_KEY is not set"
    echo "  Please set it with: export OPENAI_API_KEY='your-api-key'"
fi

if [ -n "$ANTHROPIC_API_KEY" ]; then
    print_status "ANTHROPIC_API_KEY is set"
else
    print_warning "ANTHROPIC_API_KEY is not set"
    echo "  Please set it with: export ANTHROPIC_API_KEY='your-api-key'"
fi

# Run tests if available
echo ""
echo "Running tests..."
if [ -d "tests" ]; then
    if command -v pytest &> /dev/null; then
        pytest tests/ -v --tb=short
        print_status "Tests completed"
    else
        print_warning "pytest not found, skipping tests"
    fi
else
    print_warning "No tests directory found"
fi

echo ""
echo "=========================================="
echo "Setup completed successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Set your API keys:"
echo "   export OPENAI_API_KEY='your-api-key'"
echo "   export ANTHROPIC_API_KEY='your-api-key'"
echo "3. Run the simulation:"
echo "   python scripts/run_simulation.py --scenario data/scenarios/assembly_line.yaml"
echo "4. Run evaluation:"
echo "   python scripts/evaluate.py --dataset data/datasets/MRTA-Benchmark"
echo ""
echo "For more information, see README.md"
