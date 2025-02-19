#!/usr/bin/env python3

import unittest
import time
import psutil
import os
from pathlib import Path
import logging
import json
from textbook_divider.omr_processor import OMRProcessor

class TestOMRPerformance(unittest.TestCase):
	def setUp(self):
		self.logger = logging.getLogger(__name__)
		self.processor = OMRProcessor()
		self.test_dir = Path(__file__).parent.parent
		self.sample_dir = self.test_dir / 'sample_books'
		self.metrics_dir = self.test_dir / 'metrics'
		self.metrics_dir.mkdir(exist_ok=True)
		self.process = psutil.Process()

	def test_processing_times(self):
		"""Test processing times for different types of musical content"""
		test_files = {
			'simple': {
				'file': 'basic_score.pdf',
				'target': 2.0  # Target: < 2s/page
			},
			'complex': {
				'file': 'complex_score.pdf',
				'target': 5.0  # Target: < 5s/page
			},
			'mixed': {
				'file': 'mixed_layout.pdf',
				'target': 3.0  # Target: < 3s/page
			}
		}

		results = {}
		for test_type, config in test_files.items():
			file_path = self.sample_dir / config['file']
			if not file_path.exists():
				self.logger.warning(f"Test file not found: {config['file']}")
				continue

			# Measure processing time
			start_time = time.time()
			initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
			
			result = self.processor.process_page(str(file_path))
			
			end_time = time.time()
			peak_memory = self.process.memory_info().rss / 1024 / 1024  # MB
			
			processing_time = end_time - start_time
			memory_usage = peak_memory - initial_memory

			# Assert performance targets
			self.assertLess(processing_time, config['target'],
						  f"{test_type} processing exceeded target time")
			self.assertLess(memory_usage, 2048,  # < 2GB
						  f"{test_type} processing exceeded memory target")

			results[test_type] = {
				'processing_time': processing_time,
				'memory_usage': memory_usage,
				'engine_used': result.get('engine', 'unknown'),
				'success': result['success']
			}

		self.save_metrics(results)

	def test_memory_management(self):
		"""Test memory usage and cleanup"""
		initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
		peak_memory = initial_memory
		
		# Process multiple files to test memory handling
		test_files = ['complex_score.pdf', 'multi_column.pdf', 'contemporary.pdf']
		for _ in range(3):  # Multiple iterations to check for memory leaks
			for file in test_files:
				file_path = self.sample_dir / file
				if not file_path.exists():
					continue
				
				result = self.processor.process_page(str(file_path))
				current_memory = self.process.memory_info().rss / 1024 / 1024
				peak_memory = max(peak_memory, current_memory)
				
				# Check memory cleanup
				self.assertLess(current_memory - initial_memory, 2048,
							  "Memory usage exceeded 2GB limit")

		# Verify overall memory usage
		final_memory = self.process.memory_info().rss / 1024 / 1024
		self.assertLess(final_memory - initial_memory, 512,
					   "Memory not properly cleaned up")

	def test_jvm_heap_management(self):
		"""Test JVM heap management for Audiveris"""
		if not self.processor.audiveris_path:
			self.skipTest("Audiveris not available")

		initial_memory = self.process.memory_info().rss / 1024 / 1024
		file_path = self.sample_dir / 'complex_score.pdf'
		
		# Process file multiple times to test JVM heap stability
		for _ in range(5):
			result = self.processor.process_page(str(file_path))
			self.assertTrue(result['success'])
			current_memory = self.process.memory_info().rss / 1024 / 1024
			self.assertLess(current_memory - initial_memory, 2048,
						  "JVM heap exceeded limit")

	def save_metrics(self, results: dict):
		"""Save performance metrics to JSON file"""
		metrics_file = self.metrics_dir / 'omr_performance_metrics.json'
		with open(metrics_file, 'w') as f:
			json.dump(results, f, indent=2)
		self.logger.info(f"Performance metrics saved to {metrics_file}")

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	unittest.main(verbosity=2)