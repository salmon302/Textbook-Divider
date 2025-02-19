#!/bin/bash

# Set up environment
echo "Setting up test environment..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
VENV_PATH="$PROJECT_ROOT/venv"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Create test directories if they don't exist
mkdir -p "$SCRIPT_DIR/metrics"
mkdir -p "$SCRIPT_DIR/logs"

# Run all OMR-related tests
echo "Running OMR test suite..."
cd "$PROJECT_ROOT"

echo "1. Running basic OMR tests..."
"$VENV_PATH/bin/python" -m pytest tests/test_advanced_omr.py -v --cov=textbook_divider.omr_processor --cov-report=term-missing

echo "2. Running OMR performance tests..."
"$VENV_PATH/bin/python" -m unittest tests/scripts/test_omr_performance.py -v

echo "3. Running OMR quality tests..."
"$VENV_PATH/bin/python" -m unittest tests/scripts/test_omr_quality.py -v

# Check exit status
if [ $? -eq 0 ]; then
	echo "All OMR tests completed successfully"
	echo "Check test results in tests/metrics/"
else
	echo "Some OMR tests failed"
	exit 1
fi

# Deactivate virtual environment
deactivate


