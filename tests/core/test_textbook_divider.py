import os
import time
import unittest
from pathlib import Path
from typing import List, Dict, Optional
import json
from textbook_divider.main import TextbookDivider
from textbook_divider.chapter_detector import Chapter

class TestTextbookDivider(unittest.TestCase):
	def setUp(self):
		self.current_dir = Path(__file__).parent
		self.sample_dir = self.current_dir / "sample_books"
		self.output_dir = self.current_dir / "output"
		self.ground_truth_dir = self.current_dir / "ground_truth"
		self.divider = TextbookDivider()
		self.debug = os.getenv('DEBUG', 'false').lower() == 'true'
		self.page_range = self._parse_page_range(os.getenv('PAGE_RANGE', ''))
		
		# Create output directory if it doesn't exist
		self.output_dir.mkdir(parents=True, exist_ok=True)
	
	def _parse_page_range(self, range_str: str) -> Optional[tuple[int, int]]:
		"""Parse page range from environment variable (e.g., '1-10')"""
		if not range_str:
			return None
		try:
			start, end = map(int, range_str.split('-'))
			return (start, end)
		except ValueError:
			print(f"Invalid page range format: {range_str}. Expected format: 'start-end'")
			return None

	def debug_print(self, *args, **kwargs):
		"""Print debug information if DEBUG=true"""
		if self.debug:
			print(*args, **kwargs)

	def process_with_metrics(self, input_file: Path, output_dir: Path) -> Dict:
		"""Process book with detailed metrics collection"""
		start_time = time.time()
		page_times = []
		
		# Process the book with optional page range
		output_files = self.divider.process_book(
			str(input_file), 
			str(output_dir),
			page_range=self.page_range,
			page_callback=lambda page_num, total: 
				self.debug_print(f"Processing page {page_num}/{total}")
		)
		
		total_time = time.time() - start_time
		
		metrics = {
			'total_time': total_time,
			'pages_processed': len(page_times),
			'avg_time_per_page': total_time / len(page_times) if page_times else 0,
			'output_files': len(output_files)
		}
		
		self.debug_print("\nProcessing Metrics:")
		self.debug_print(f"Total time: {metrics['total_time']:.2f}s")
		self.debug_print(f"Pages processed: {metrics['pages_processed']}")
		self.debug_print(f"Average time per page: {metrics['avg_time_per_page']:.2f}s")
		
		return metrics, output_files
	
	def evaluate_chapter_detection(self, detected_chapters: List[Chapter], 
								 ground_truth_file: Path) -> Dict:
		"""Evaluate chapter detection accuracy"""
		with open(ground_truth_file, 'r') as f:
			ground_truth = json.load(f)
		
		# Print debug information first
		print("\nDetected chapters:")
		for ch in detected_chapters:
			print(f"- {ch.number}: {ch.title}")
		print("\nGround truth chapters:")
		for ch in ground_truth['chapters']:
			print(f"- {ch['number']}: {ch['title']}")
		
		# Calculate base metrics
		correct_chapters = 0
		total_ground_truth = len(ground_truth['chapters'])
		total_detected = len(detected_chapters)
		
		# Count matching chapters
		for detected in detected_chapters:
			for truth in ground_truth['chapters']:
				if (detected.title.strip().upper() == truth['title'].strip().upper() and
					abs(detected.number - truth['number']) <= 1):
					correct_chapters += 1
					break
		
		# Calculate evaluation metrics
		precision = correct_chapters / total_detected if total_detected > 0 else 0
		recall = correct_chapters / total_ground_truth if total_ground_truth > 0 else 0
		f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
		
		return {
			'precision': precision,
			'recall': recall,
			'f1_score': f1_score,
			'correct_chapters': correct_chapters,
			'total_detected': total_detected,
			'total_ground_truth': total_ground_truth
		}
	
	def evaluate_text_quality(self, output_file: Path, ground_truth_file: Path) -> Dict:
		"""Evaluate text quality metrics"""
		with open(output_file, 'r') as f:
			output_text = f.read()
		with open(ground_truth_file, 'r') as f:
			ground_truth = f.read()
		
		# Calculate text similarity metrics
		words_match = len(set(output_text.split()) & set(ground_truth.split()))
		total_words_truth = len(ground_truth.split())
		
		return {
			'word_accuracy': words_match / total_words_truth if total_words_truth > 0 else 0,
			'total_words': len(output_text.split()),
			'ground_truth_words': total_words_truth
		}
	
	def test_pdf_processing(self):
		"""Test PDF processing with OCR"""
		test_file = "sample.pdf"
		sample_file = self.sample_dir / test_file
		output_dir = self.output_dir / test_file.replace(".", "_")
		ground_truth = self.ground_truth_dir / f"{test_file}.json"
		
		# Process with metrics
		metrics, output_files = self.process_with_metrics(sample_file, output_dir)
		
		# Evaluate results
		detection_metrics = self.evaluate_chapter_detection(output_files, ground_truth)
		
		self.debug_print(f"\nPDF Processing Results:")
		self.debug_print(f"Chapter Detection:")
		self.debug_print(f"- Precision: {detection_metrics['precision']:.2f}")
		self.debug_print(f"- Recall: {detection_metrics['recall']:.2f}")
		self.debug_print(f"- F1 Score: {detection_metrics['f1_score']:.2f}")
		
		self.assertGreater(detection_metrics['f1_score'], 0.7, 
						  "Chapter detection accuracy below threshold")
	
	def test_text_processing(self):
		"""Test plain text processing"""
		test_file = "sample.txt"
		sample_file = self.sample_dir / test_file
		output_dir = self.output_dir / test_file.replace(".", "_")
		ground_truth = self.ground_truth_dir / f"{test_file}.json"
		
		# Process with metrics
		metrics, output_files = self.process_with_metrics(sample_file, output_dir)
		
		# Evaluate results
		detection_metrics = self.evaluate_chapter_detection(output_files, ground_truth)
		
		self.debug_print(f"\nText Processing Results:")
		self.debug_print(f"Processing Metrics:")
		self.debug_print(f"- Total time: {metrics['total_time']:.2f}s")
		self.debug_print(f"- Pages processed: {metrics['pages_processed']}")
		self.debug_print(f"Chapter Detection:")
		self.debug_print(f"- Precision: {detection_metrics['precision']:.2f}")
		self.debug_print(f"- Recall: {detection_metrics['recall']:.2f}")
		self.debug_print(f"- F1 Score: {detection_metrics['f1_score']:.2f}")
		
		self.assertGreater(detection_metrics['f1_score'], 0.8, 
						  "Text processing accuracy below threshold")

	def test_book_section(self):
		"""Test processing specific book sections"""
		test_file = "Schoenberg_Fundamentals.pdf"
		sample_file = self.sample_dir / test_file
		output_dir = self.output_dir / "section_test"
		
		# Test different sections
		sections = [
			(1, 10, "Introduction"),
			(50, 60, "Middle chapters"),
			(100, 110, "Later chapters")
		]
		
		for start, end, section_name in sections:
			self.debug_print(f"\nTesting section: {section_name}")
			self.page_range = (start, end)
			
			# Process section with metrics
			section_metrics, output_files = self.process_with_metrics(
				sample_file,
				output_dir / f"pages_{start}_{end}"
			)
			
			self.debug_print(f"Section Metrics:")
			self.debug_print(f"- Pages processed: {section_metrics['pages_processed']}")
			self.debug_print(f"- Total time: {section_metrics['total_time']:.2f}s")
			self.debug_print(f"- Average time per page: {section_metrics['avg_time_per_page']:.2f}s")
			self.debug_print(f"- Chapters found: {len(output_files)}")

if __name__ == '__main__':
	unittest.main()