import unittest
from pathlib import Path
import time
import json
import difflib
import Levenshtein
from textbook_divider.file_handler import PDFHandler
from textbook_divider.ocr_processor import OCRProcessor
from .test_utils import log_test_case, log_test_data, get_test_logger

logger = get_test_logger(__name__)

class TestOCRQuality(unittest.TestCase):
	def setUp(self):
		self.test_dir = Path(__file__).parent
		self.output_dir = self.test_dir / "output" / "ocr_quality"
		self.output_dir.mkdir(parents=True, exist_ok=True)
		
		# Test files
		self.test_file = Path("/home/seth-n/CLionProjects/Textbook Divider/data/input/Arnold Schoenberg, Gerald Strang, Leonard Stein - Fundamentals of Musical Composition (1982, Faber & Faber) - libgen.li.pdf")
		
		# Initialize handlers
		self.pdf_handler = PDFHandler(force_ocr=True)
		self.ocr = OCRProcessor(enable_gpu=False)
		
		# Quality metrics thresholds
		self.thresholds = {
			'min_confidence': 80.0,
			'min_word_accuracy': 0.85,
			'max_processing_time': 30.0,  # seconds
			'min_text_length': 100
		}
	
	def calculate_metrics(self, ocr_text: str, expected_text: str) -> dict:
		"""Calculate OCR quality metrics"""
		# Word accuracy
		ocr_words = set(ocr_text.lower().split())
		expected_words = set(expected_text.lower().split())
		word_accuracy = len(ocr_words.intersection(expected_words)) / len(expected_words)
		
		# Character-level accuracy using Levenshtein distance
		char_accuracy = 1 - (Levenshtein.distance(ocr_text, expected_text) / len(expected_text))
		
		# Confidence score from OCR
		confidence = self.ocr.get_confidence_score(ocr_text)
		
		return {
			'word_accuracy': word_accuracy,
			'char_accuracy': char_accuracy,
			'confidence': confidence,
			'text_length': len(ocr_text)
		}
	
	@log_test_case
	def test_ocr_quality_metrics(self):
		"""Test OCR quality with comprehensive metrics"""
		test_pages = [15, 20, 25]  # Test multiple pages
		results = []
		
		for page_num in test_pages:
			start_time = time.time()
			content = self.pdf_handler._process_single_page(self.test_file, page_num)
			processing_time = time.time() - start_time
			
			# Get expected text from ground truth if available
			expected_file = self.test_dir / "data" / "expected" / f"page_{page_num}.txt"
			expected_text = expected_file.read_text() if expected_file.exists() else ""
			
			# Calculate metrics
			metrics = self.calculate_metrics(content, expected_text) if expected_text else {}
			metrics['processing_time'] = processing_time
			
			# Quality assertions
			if expected_text:
				self.assertGreaterEqual(
					metrics['word_accuracy'],
					self.thresholds['min_word_accuracy'],
					f"Word accuracy below threshold on page {page_num}"
				)
			
			self.assertLess(
				processing_time,
				self.thresholds['max_processing_time'],
				f"Processing time exceeded threshold on page {page_num}"
			)
			
			self.assertGreater(
				len(content),
				self.thresholds['min_text_length'],
				f"Text length below threshold on page {page_num}"
			)
			
			# Save results
			result = {
				'page_number': page_num,
				'metrics': metrics,
				'content_preview': content[:500] if content else "No content"
			}
			results.append(result)
			
			# Save output for manual inspection
			output_file = self.output_dir / f"page_{page_num}_ocr.txt"
			output_file.write_text(content)
			
			# Save diff if expected text exists
			if expected_text:
				diff = list(difflib.unified_diff(
					expected_text.splitlines(),
					content.splitlines(),
					fromfile=f'expected_{page_num}',
					tofile=f'actual_{page_num}'
				))
				diff_file = self.output_dir / f"page_{page_num}_diff.txt"
				diff_file.write_text('\n'.join(diff))
		
		# Save overall results
		results_file = self.output_dir / "ocr_quality_results.json"
		with open(results_file, 'w') as f:
			json.dump(results, f, indent=2)
		
		logger.info(f"OCR quality results saved to: {results_file}")

if __name__ == '__main__':
	unittest.main()