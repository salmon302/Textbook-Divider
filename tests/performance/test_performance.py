#!/usr/bin/env python3

import unittest
import time
import psutil
import os
from pathlib import Path
import logging
from textbook_divider.file_handler import PDFHandler
from textbook_divider.chapter_detector import ChapterDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestPerformance(unittest.TestCase):
	def setUp(self):
		self.pdf_handler = PDFHandler()
		self.chapter_detector = ChapterDetector()
		self.test_dir = Path(__file__).parent
		self.input_dir = self.test_dir.parent / 'input'
		self.metrics_dir = self.test_dir / 'metrics'
		self.metrics_dir.mkdir(exist_ok=True)
		self.process = psutil.Process()
		
	def test_processing_speed(self):
		"""Test processing speed for books of increasing size"""
		test_files = [
			("Schoenberg", "Arnold Schoenberg, Gerald Strang, Leonard Stein - Fundamentals of Musical Composition (1982, Faber & Faber) - libgen.li.pdf", 200),
			("Lewin", "David Lewin - Generalized Musical Intervals and Transformations (2007).pdf", 300),
			("Tymoczko", "(Oxford Studies in Music Theory) Dmitri Tymoczko - A Geometry of Music_ Harmony and Counterpoint in the Extended Common Practice-Oxford University Press (2011).pdf", 400),
			("Erdahl", "Fred LErdahl - Tonal Pitch Space-Oxford University Press (2001).pdf", 400)
		]
		
		results = {}
		for name, filename, expected_pages in test_files:
			file_path = self.input_dir / filename
			if not file_path.exists():
				logger.warning(f"Test file not found: {filename}")
				continue
				
			logger.info(f"\nTesting {name} ({expected_pages} pages)")
			
			# Measure processing time
			start_time = time.time()
			initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
			
			content = self.pdf_handler.read_content(file_path)
			chapters = self.chapter_detector.detect_chapters(content)
			
			end_time = time.time()
			peak_memory = self.process.memory_info().rss / 1024 / 1024  # MB
			
			# Calculate metrics
			processing_time = end_time - start_time
			memory_usage = peak_memory - initial_memory
			pages_processed = len(content.split('\n\n'))
			time_per_page = processing_time / pages_processed if pages_processed > 0 else 0
			
			results[name] = {
				'total_time': processing_time,
				'pages_processed': pages_processed,
				'time_per_page': time_per_page,
				'peak_memory_mb': peak_memory,
				'memory_usage_mb': memory_usage,
				'chapters_found': len(chapters)
			}
			
			# Assert performance targets from workflow
			if 'musical' in filename.lower() or 'mathematical' in filename.lower():
				self.assertLess(time_per_page, 4.0)  # < 4s/page for notation
			elif 'geometry' in filename.lower():
				self.assertLess(time_per_page, 6.0)  # < 6s/page for complex diagrams
			else:
				self.assertLess(time_per_page, 2.0)  # < 2s/page for base text
			
			# Memory usage targets
			self.assertLess(memory_usage, 2048)  # < 2GB peak
			self.assertLess(peak_memory - memory_usage, 1024)  # < 1GB sustained
			
		# Save results
		self.save_performance_metrics(results)
		
	def save_performance_metrics(self, results: dict):
		"""Save performance metrics to file"""
		metrics_file = self.metrics_dir / 'performance_metrics.txt'
		with open(metrics_file, 'w') as f:
			f.write("Performance Test Results\n")
			f.write("=======================\n\n")
			
			for name, metrics in results.items():
				f.write(f"{name}:\n")
				f.write(f"  Total Time: {metrics['total_time']:.2f}s\n")
				f.write(f"  Pages Processed: {metrics['pages_processed']}\n")
				f.write(f"  Time per Page: {metrics['time_per_page']:.2f}s\n")
				f.write(f"  Peak Memory: {metrics['peak_memory_mb']:.1f}MB\n")
				f.write(f"  Memory Usage: {metrics['memory_usage_mb']:.1f}MB\n")
				f.write(f"  Chapters Found: {metrics['chapters_found']}\n\n")

if __name__ == '__main__':
	unittest.main()