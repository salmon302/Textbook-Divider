# Test Workflow for Textbook Divider

## 1. Sample Data Preparation
- Test corpus from input directory:
	1. Schoenberg - Fundamentals of Musical Composition
		 - Expected features: Numbered chapters, exercises, musical examples
		 - Size: Medium (~200 pages)
		 - Special handling: Musical notation, figures
	
	2. David Lewin - Generalized Musical Intervals
		 - Expected features: Mathematical notation, complex formatting
		 - Size: Large (>300 pages)
		 - Special handling: Mathematical equations, diagrams
	
	3. Tymoczko - A Geometry of Music
		 - Expected features: Complex figures, multi-level chapters
		 - Size: Large (>400 pages)
		 - Special handling: 3D visualizations, graphs
	
	4. Erdahl - Tonal Pitch Space
		 - Expected features: Technical diagrams, formulas
		 - Size: Large (>400 pages)
		 - Special handling: Mathematical notation, tables

## 2. Testing Phases

### Phase 1: Basic Chapter Detection
1. Test with Schoenberg's Fundamentals:
	 - Verify standard chapter numbering
	 - Test exercise section detection
	 - Validate musical example preservation

2. Test with Lewin's GMIT:
	 - Verify mathematical content preservation
	 - Test section and subsection detection
	 - Validate definition and theorem blocks

3. Test with Tymoczko's Geometry:
	 - Verify multi-level chapter structure
	 - Test figure and diagram preservation
	 - Validate cross-references

4. Test with Erdahl's Pitch Space:
	 - Verify complex section numbering
	 - Test mathematical notation handling
	 - Validate table preservation

### Phase 2: OCR Quality Verification
1. Compare OCR accuracy across books:
	 - Mathematical notation accuracy
	 - Musical notation recognition
	 - Multi-column layout handling
	 - Figure and diagram quality

### Phase 3: Performance Testing
1. Process books in increasing size order:
	 - Schoenberg (~200 pages)
	 - Lewin (>300 pages)
	 - Tymoczko & Erdahl (>400 pages)
2. Monitor and log:
	 - Processing time per page
	 - Memory usage patterns
	 - OCR processing speed
	 - Chapter detection accuracy

### Phase 4: Error Handling
1. Test with specific book features:
	 - Musical notation in Schoenberg
	 - Mathematical formulas in Lewin
	 - Complex diagrams in Tymoczko
	 - Dense technical content in Erdahl

## 3. Quality Metrics Tracking

### Accuracy Metrics
- Chapter Detection (per book):
	- Target F1 Score: > 0.9
	- Baseline measurements needed for each
- Content Preservation:
	- Text accuracy: > 0.95
	- Mathematical notation: > 0.90
	- Musical notation: > 0.85
	- Figures/diagrams: > 0.90

### Performance Metrics
- Processing Speed:
	- Base text: < 2s/page
	- With notation: < 4s/page
	- With complex diagrams: < 6s/page
- Memory Usage:
	- Peak: < 2GB/1000 pages
	- Sustained: < 1GB

## 4. Test Data Organization
- input/: Original PDFs
- tests/ground_truth/: Expected chapter structures
- tests/output/: Processing results
- tests/metrics/: Performance logs

## 5. Automated Testing
1. Run basic tests: `python -m unittest tests/test_basic.py`
2. Run book-specific tests: `python -m unittest tests/test_books.py`
3. Generate accuracy reports: `python scripts/evaluate_accuracy.py`
4. Compare with ground truth: `python scripts/compare_results.py`
5. Run performance benchmarks: `python scripts/run_benchmarks.py`
6. Execute error handling tests: `python scripts/test_error_cases.py`