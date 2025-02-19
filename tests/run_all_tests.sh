#!/bin/bash

# Set up environment
echo "Setting up test environment..."
mkdir -p test_reports
mkdir -p sample_books

# Run core tests
echo "Running core tests..."
python -m pytest core/test_*.py

# Run OCR tests
echo "Running OCR tests..."
python -m pytest ocr/test_*.py

# Run OMR tests
echo "Running OMR tests..."
python -m pytest omr/test_*.py

# Run performance tests
echo "Running performance tests..."
python -m pytest performance/test_*.py

# Generate test report
echo "Generating test report..."
python utils/test_runner.py --report

# Check if any tests failed
if [ $? -eq 0 ]; then
	echo "All tests completed successfully!"
	exit 0
else
	echo "Some tests failed. Check test_reports directory for details."
	exit 1
fi
