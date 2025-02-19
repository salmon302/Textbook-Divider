#!/bin/bash

# Set up environment
BASE_DIR="/home/seth-n/CLionProjects/Textbook Divider"
OUTPUT_DIR="$BASE_DIR/tests/phase_3_5/output"
LOG_FILE="$OUTPUT_DIR/test_run_$(date +%Y%m%d_%H%M%S).log"

# Default values
BOOK="all"
DEBUG=false
ANALYZE_ONLY=false

# Help message
show_help() {
	echo "Usage: $0 [options]"
	echo "Options:"
	echo "  -b, --book BOOK    Test specific book (schoenberg|lewin|tymoczko|all)"
	echo "  -d, --debug        Enable debug output"
	echo "  -a, --analyze      Only analyze existing results"
	echo "  -h, --help         Show this help message"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
	case $1 in
		-b|--book)
			BOOK="$2"
			shift 2
			;;
		-d|--debug)
			DEBUG=true
			shift
			;;
		-a|--analyze)
			ANALYZE_ONLY=true
			shift
			;;
		-h|--help)
			show_help
			exit 0
			;;
		*)
			echo "Unknown option: $1"
			show_help
			exit 1
			;;
	esac
done

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Activate virtual environment if it exists
if [ -d "$BASE_DIR/venv" ]; then
    source "$BASE_DIR/venv/bin/activate"
fi

# Install requirements if needed
if [ -f "$BASE_DIR/tests/phase_3_5/requirements.txt" ]; then
    pip install -r "$BASE_DIR/tests/phase_3_5/requirements.txt"
fi

# Set environment variables
export DEBUG

# Start logging
echo "Starting music theory book tests at $(date)" | tee -a "$LOG_FILE"

# Run tests or analysis
if [ "$ANALYZE_ONLY" = true ]; then
	echo "Analyzing existing test results..." | tee -a "$LOG_FILE"
	python3 "$BASE_DIR/tests/phase_3_5/run_music_tests.py" --analyze 2>&1 | tee -a "$LOG_FILE"
else
	echo "Running tests for: $BOOK" | tee -a "$LOG_FILE"
	python3 "$BASE_DIR/tests/phase_3_5/run_music_tests.py" --book "$BOOK" 2>&1 | tee -a "$LOG_FILE"
fi

TEST_EXIT_CODE=${PIPESTATUS[0]}

# Print summary
echo -e "\nTest execution completed at $(date)" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "Test reports directory: $OUTPUT_DIR" | tee -a "$LOG_FILE"

exit $TEST_EXIT_CODE