# Phase 3.5: Real-World Testing

This directory contains the test suite for Phase 3.5 of the Textbook Divider project, focusing on real-world testing with music theory textbooks.

## Test Books

The test suite covers four major music theory textbooks:
- Schoenberg's Fundamentals of Musical Composition
- Lewin's Generalized Musical Intervals
- Tymoczko's Geometry of Music
- Lerdahl's Tonal Pitch Space

## Test Infrastructure

### Components
- `test_music_theory_books.py`: Main test suite implementation
- `run_music_tests.py`: Test runner with reporting capabilities
- `run_tests.sh`: Shell script for test execution and environment setup
- `requirements.txt`: Required Python dependencies

### Metrics Tracked
- OCR/OMR accuracy
- Processing speed
- Memory usage
- Mixed content quality
- Error rates
- Staff detection accuracy
- Note recognition accuracy

## Running Tests

1. Setup:
```bash
# Install dependencies
pip install -r requirements.txt
```

2. Run Tests:
```bash
# Run all tests
./run_tests.sh

# Run specific book tests
./run_tests.sh --book schoenberg
./run_tests.sh --book lewin
./run_tests.sh --book tymoczko
./run_tests.sh --book lerdahl
```

## Test Reports

Reports are generated in the `output` directory:
- Individual book analysis files (`*_analysis.json`)
- Comprehensive test reports with timestamps
- Test execution logs

## Performance Requirements

- Staff Detection: >88% accuracy
- Note Recognition: >85% accuracy
- Mixed Content Quality: >80%
- Memory Usage: <1024MB per section
- Processing Time: <35s per page