#!/bin/bash

# Default values
DEBUG=false
PAGE_RANGE=""
TEST_PATTERN="test_book"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
	case $1 in
		--debug)
			DEBUG=true
			shift
			;;
		--pages)
			PAGE_RANGE="$2"
			shift 2
			;;
		--pattern)
			TEST_PATTERN="$2"
			shift 2
			;;
		*)
			echo "Unknown option: $1"
			exit 1
			;;
	esac
done

# Export environment variables
export DEBUG
export PAGE_RANGE

# Run tests with specified pattern
echo "Running tests with configuration:"
echo "- Debug mode: $DEBUG"
echo "- Page range: ${PAGE_RANGE:-full book}"
echo "- Test pattern: $TEST_PATTERN"
echo

python -m pytest -v "core/test_textbook_divider.py" -k "$TEST_PATTERN"