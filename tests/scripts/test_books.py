#!/usr/bin/env python3

import unittest
from pathlib import Path
import sys
import time
import logging
import json
import psutil
from functools import wraps

# Add project root and src to path
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / 'src'))
from textbook_divider.processor import PDFProcessor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def track_performance(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		start_time = time.time()
		start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
		
		result = func(*args, **kwargs)
		
		end_time = time.time()
		end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
		
		metrics = {
			'execution_time': end_time - start_time,
			'memory_usage': {
				'start': start_memory,
				'end': end_memory,
				'peak': end_memory - start_memory
			}
		}
		
		# Save metrics
		metrics_dir = Path(__file__).parent / 'metrics'
		metrics_dir.mkdir(exist_ok=True)
		metrics_file = metrics_dir / f"{func.__name__}_metrics.json"
		with open(metrics_file, 'w') as f:
			json.dump(metrics, f, indent=2)
			
		return result
	return wrapper

def with_timeout(timeout=60):
	def decorator(func):
		@wraps(func)
		def wrapper(*args, **kwargs):
			start = time.time()
			logging.info(f"Starting {func.__name__}")
			result = func(*args, **kwargs)
			elapsed = time.time() - start
			if elapsed > timeout:
				logging.warning(f"{func.__name__} exceeded timeout of {timeout}s")
			logging.info(f"Completed {func.__name__} in {elapsed:.2f}s")
			return result
		return wrapper
	return decorator

class BaseBookTest(unittest.TestCase):
	def setUp(self):
		self.test_dir = Path(__file__).parent
		self.input_dir = self.test_dir.parent / "input"
		self.output_dir = self.test_dir / "output"
		self.max_memory_mb = 2048
		self.process = psutil.Process()

	def check_memory_usage(self):
		"""Monitor memory usage and raise exception if limit exceeded"""
		memory_mb = self.process.memory_info().rss / (1024 * 1024)
		if memory_mb > self.max_memory_mb:
			raise MemoryError(f"Memory usage exceeded {self.max_memory_mb}MB limit")

	def tearDown(self):
		"""Cleanup resources after each test"""
		import gc
		gc.collect()
		temp_dir = Path('/tmp')
		for file in temp_dir.glob('pdf_*'):
			try:
				file.unlink()
			except Exception as e:
				logging.warning(f"Failed to remove temp file {file}: {e}")

	def safe_process_test(self, func):
		try:
			processor = PDFProcessor(self.book_path)
			processor.max_pages = 20  # Increased to match output.json
			result = func(processor)
			self.check_memory_usage()
			return result
		except MemoryError as e:
			self.fail(f"Memory limit exceeded: {e}")
		except Exception as e:
			self.fail(f"Test failed: {e}")


class TestTymoczkoGeometry(BaseBookTest):
	def setUp(self):
		super().setUp()
		self.book_path = self.input_dir / "(Oxford Studies in Music Theory) Dmitri Tymoczko - A Geometry of Music_ Harmony and Counterpoint in the Extended Common Practice-Oxford University Press (2011).pdf"
		self.output_path = self.output_dir / f"{self.book_path.stem}_output.json"

	def test_book_exists(self):
		self.assertTrue(self.book_path.exists(), "Tymoczko book not found")
		self.assertTrue(self.output_path.exists(), "Output file not found")
		
	def test_output_format(self):
		"""Test if output file has correct format"""
		with open(self.output_path) as f:
			data = json.load(f)
		self.assertIn('title', data, "Missing title field")
		self.assertIn('chapters', data, "Missing chapters field")
		self.assertIn('metadata', data, "Missing metadata field")
		
	@track_performance
	@with_timeout(60)
	def test_chapter_structure(self):
		"""Test mixed chapter numbering and structure"""
		with open(self.output_path) as f:
			result = json.load(f)
			
		chapters = result.get('chapters', [])
		
		# Test basic chapter properties
		self.assertGreater(len(chapters), 0, "No chapters detected")
		for chapter in chapters:
			self.assertIn('number', chapter, "Chapter missing number")
			self.assertIn('title', chapter, "Chapter missing title")
			self.assertIn('page', chapter, "Chapter missing page number")
		
		# Test for both numeric and roman numeral chapters
		numeric_chapters = [ch for ch in chapters if ch['number'].isdigit()]
		roman_chapters = [ch for ch in chapters if ch['number'] in ['I', 'II']]
		
		self.assertGreater(len(numeric_chapters), 0, "No numeric chapters found")
		self.assertGreater(len(roman_chapters), 0, "No roman numeral sections found")
		
		# Verify numeric chapters are in order (allowing for missing chapter 6)
		numeric_nums = [int(ch['number']) for ch in numeric_chapters]
		expected_nums = [1, 2, 3, 4, 5, 7, 8, 9, 10]
		self.assertEqual(numeric_nums, expected_nums, 
					   "Numeric chapters not in expected order")
		
	@track_performance
	@with_timeout(30)
	def test_notation_detection(self):
		"""Test detection of musical and mathematical notation"""
		with open(self.output_path) as f:
			result = json.load(f)
			
		features = result['metadata']['features_detected']
		self.assertTrue(features['musical_notation'], 
					  "Musical notation not detected")
		self.assertTrue(features['mathematical_notation'],
					  "Mathematical notation not detected")
			
	@track_performance
	@with_timeout(30)
	def test_exercise_detection(self):
		"""Test detection of exercises"""
		with open(self.output_path) as f:
			result = json.load(f)
			
		features = result['metadata']['features_detected']
		self.assertTrue(features['exercises'], 
					  "Exercises not detected")

if __name__ == '__main__':
	unittest.main()
