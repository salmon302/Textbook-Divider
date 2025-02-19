#!/bin/bash

# Make scripts directory executable
chmod -R +x scripts/

echo "Running basic tests..."
python3 -m unittest scripts/test_basic.py

echo "Running OCR tests..."
python3 -m unittest scripts/test_ocr.py

echo "Running OMR tests..."
python3 -m unittest scripts/test_omr.py

echo "Running book tests..."
python3 -m unittest scripts/test_real_books.py

echo "Running performance tests..."
python3 -m unittest scripts/test_performance.py

echo "Running plugin system tests..."
python3 -m unittest scripts/test_plugin_system.py

echo "Evaluating accuracy..."
python3 scripts/evaluate_accuracy.py

echo "Running benchmarks..."
python3 scripts/run_benchmarks.py

echo "All tests completed."