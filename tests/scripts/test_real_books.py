#!/usr/bin/env python3

import unittest
import json
from pathlib import Path
import logging
import gc
import psutil
import os
from textbook_divider.omr_processor import OMRProcessor
from textbook_divider.text_processor import TextProcessor

class TestRealWorldBooks(unittest.TestCase):
	def setUp(self):
		self.logger = logging.getLogger(__name__)
		self.processor = OMRProcessor()
		self.text_processor = TextProcessor()
		self.data_dir = Path("/home/seth-n/CLionProjects/Textbook Divider/data")
		self.input_dir = self.data_dir / "input"
		self.output_dir = self.data_dir / "output"
		self.metrics_dir = Path("/home/seth-n/CLionProjects/Textbook Divider/tests/metrics")
		
		# Set memory limit (80% of available memory)
		self.memory_limit = psutil.virtual_memory().available * 0.8

	def tearDown(self):
		# Cleanup after each test
		gc.collect()
		if hasattr(self, 'processor'):
			del self.processor
		gc.collect()

	def _run_test_with_memory_check(self, book_path: Path, output_path: Path, expectations: dict, book_id: str):
		"""Run a single test with memory monitoring"""
		try:
			# Create output directory if it doesn't exist
			output_path.mkdir(parents=True, exist_ok=True)
			
			# Process book with memory monitoring
			result = self.processor.process_book(str(book_path), str(output_path))
			
			# Verify and save results
			self._verify_book_processing(result, book_id, expectations)
			
			# Cleanup temporary files
			for temp_file in output_path.glob("*_temp_*.png"):
				try:
					temp_file.unlink()
				except OSError as e:
					self.logger.warning(f"Failed to remove temporary file {temp_file}: {str(e)}")
					
		except MemoryError:
			self.logger.error(f"Memory limit exceeded while processing {book_id}", exc_info=True)
			raise
		except Exception as e:
			self.logger.error(f"Error processing {book_id}: {str(e)}", exc_info=True)
			raise

	def test_schoenberg_fundamentals(self):
		"""Test Schoenberg's Fundamentals of Musical Composition"""
		book_path = self.input_dir / "Arnold Schoenberg, Gerald Strang, Leonard Stein - Fundamentals of Musical Composition (1982, Faber & Faber) - libgen.li.pdf"
		output_path = self.output_dir / "schoenberg_fundamentals"
		
		self._run_test_with_memory_check(book_path, output_path, {
			'expected_notation_count': 150,
			'expected_chapters': 12,
			'mixed_content': True
		}, "schoenberg")

	def test_lewin_intervals(self):
		"""Test Lewin's Generalized Musical Intervals"""
		book_path = self.input_dir / "David Lewin - Generalized Musical Intervals and Transformations (2007).pdf"
		output_path = self.output_dir / "lewin_intervals"
		
		self._run_test_with_memory_check(book_path, output_path, {
			'expected_notation_count': 80,
			'expected_chapters': 9,
			'math_notation': True
		}, "lewin")

	def test_tymoczko_geometry(self):
		"""Test Tymoczko's Geometry of Music"""
		book_path = self.input_dir / "(Oxford Studies in Music Theory) Dmitri Tymoczko - A Geometry of Music_ Harmony and Counterpoint in the Extended Common Practice-Oxford University Press (2011).pdf"
		output_path = self.output_dir / "tymoczko_geometry"
		
		self._run_test_with_memory_check(book_path, output_path, {
			'expected_notation_count': 200,
			'expected_chapters': 10,
			'geometric_diagrams': True
		}, "tymoczko")

	def test_lerdahl_pitch_space(self):
		"""Test Lerdahl's Tonal Pitch Space"""
		book_path = self.input_dir / "Fred LErdahl - Tonal Pitch Space-Oxford University Press (2001).pdf"
		output_path = self.output_dir / "lerdahl_pitch_space"
		
		self._run_test_with_memory_check(book_path, output_path, {
			'expected_notation_count': 120,
			'expected_chapters': 8,
			'tree_structures': True
		}, "lerdahl")

	def _verify_book_processing(self, result, book_id, expectations):
		"""Verify book processing results and save metrics"""
		self.assertTrue(result.get('success', False), f"Book processing failed for {book_id}")
		
		metrics = {
			'notation_count': len(result.get('musical_notation', [])),
			'chapter_count': len(result.get('chapters', [])),
			'processing_time': result.get('processing_time'),
			'memory_usage': result.get('memory_usage'),
			'error_count': len(result.get('errors', [])),
			'recovery_count': len(result.get('recoveries', [])),
			'peak_memory': psutil.Process().memory_info().rss / 1024 / 1024  # MB
		}
		
		# Verify expectations
		self.assertGreaterEqual(metrics['notation_count'], 
							  expectations['expected_notation_count'] * 0.8,
							  f"Insufficient notation detection in {book_id}")
		
		self.assertEqual(metrics['chapter_count'],
						expectations['expected_chapters'],
						f"Incorrect chapter count in {book_id}")
		
		# Save metrics
		self._save_metrics(metrics, f"test_{book_id}_metrics.json")

	def _save_metrics(self, metrics: dict, filename: str):
		"""Save test metrics to JSON file"""
		metrics_file = self.metrics_dir / filename
		with open(metrics_file, 'w') as f:
			json.dump(metrics, f, indent=2)
		self.logger.info(f"Test metrics saved to {metrics_file}")

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	unittest.main(verbosity=2)