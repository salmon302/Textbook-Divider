# Textbook Divider Tests

## Test Organization
- `core/` - Core functionality tests
- `ocr/` - OCR-related tests
- `omr/` - OMR-related tests
- `performance/` - Performance testing
- `utils/` - Test utilities

## Quick Start

### Running Book Tests
Use `run_book_tests.sh` to execute tests with various configurations:

```bash
# Run all book tests
./run_book_tests.sh

# Run with debug output
./run_book_tests.sh --debug

# Test specific page range
./run_book_tests.sh --pages "1-10"

# Test specific test pattern
./run_book_tests.sh --pattern "test_pdf"
```

### Test Options
- `--debug`: Enable detailed debug output
- `--pages`: Specify page range (e.g., "1-10")
- `--pattern`: Filter tests by pattern

### Examples
```bash
# Test introduction section with debug
./run_book_tests.sh --debug --pages "1-20"

# Test middle chapters
./run_book_tests.sh --pages "50-70"

# Run only PDF tests with debug
./run_book_tests.sh --debug --pattern "test_pdf"
```

## Performance Testing
- Tests now include per-page timing metrics
- Debug mode provides detailed processing information
- Section testing allows focused performance analysis

## Test Data
- `sample_books/` - Test book samples
- `data/` - Test data and fixtures
- `ground_truth/` - Expected results
