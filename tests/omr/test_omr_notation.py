import unittest
from pathlib import Path
import json
import logging
from textbook_divider.omr_processor import OMRProcessor
from .test_utils import log_test_case, log_test_data, get_test_logger

logger = get_test_logger(__name__)

class TestOMRNotation(unittest.TestCase):
	def setUp(self):
		self.test_dir = Path(__file__).parent.parent
		self.sample_dir = self.test_dir / "sample_books"
		self.output_dir = self.test_dir / "output"
		self.omr = OMRProcessor(cache_dir=self.output_dir / "omr_cache")
		
	@log_test_case
	def test_notation_accuracy(self):
		"""Test musical notation detection accuracy"""
		test_files = {
			'basic': self.sample_dir / 'single_staff.pdf',
			'complex': self.sample_dir / 'complex_score.pdf',
			'contemporary': self.sample_dir / 'contemporary.pdf'
		}
		
		accuracy_metrics = {}
		for test_type, file_path in test_files.items():
			result = self.omr.process_page(str(file_path), 0)
			self.assertTrue(result['success'])
			self.assertTrue(result['has_music'])
			
			# Verify staff detection
			self.assertGreater(len(result['layout']['staff_positions']), 0)
			
			# Store metrics
			accuracy_metrics[test_type] = {
				'staff_count': len(result['layout']['staff_positions']),
				'processing_time': result.get('processing_time', 0)
			}
			
		log_test_data(accuracy_metrics, "Notation Detection Metrics")
		
	@log_test_case
	def test_error_recovery(self):
		"""Test comprehensive error recovery"""
		# Test with malformed notation
		result = self.omr.process_page(str(self.sample_dir / 'malformed.pdf'), 0)
		self.assertTrue(result['success'])  # Should succeed with fallback
		self.assertIn('fallback', result)
		self.assertTrue(result['fallback'])
		
		# Test with poor quality scan
		result = self.omr.process_page(str(self.sample_dir / 'poor_quality.pdf'), 0)
		self.assertTrue(result['success'])
		self.assertIn('error', result)
		
		# Verify fallback chain
		self.assertIn('text', result)  # Should fall back to OCR
		
	@log_test_case
	def test_mixed_content(self):
		"""Test mixed content handling"""
		result = self.omr.process_page(str(self.sample_dir / 'multi_column.pdf'), 0)
		self.assertTrue(result['success'])
		
		# Verify layout detection
		self.assertGreater(result['layout']['columns'], 1)
		self.assertTrue(result['has_music'])
		
		# Check staff positions in relation to text
		staff_positions = result['layout']['staff_positions']
		self.assertGreater(len(staff_positions), 0)
		
	@log_test_case
	def test_performance_metrics(self):
		"""Test performance targets"""
		test_cases = {
			'simple': self.sample_dir / 'single_staff.pdf',
			'complex': self.sample_dir / 'complex_score.pdf',
			'mixed': self.sample_dir / 'multi_column.pdf'
		}
		
		performance_metrics = {}
		for case_type, file_path in test_cases.items():
			result = self.omr.process_page(str(file_path), 0)
			self.assertTrue(result['success'])
			
			# Store metrics
			performance_metrics[case_type] = {
				'processing_time': result.get('processing_time', 0),
				'memory_usage': result.get('memory_usage', {})
			}
			
			# Verify performance targets
			if case_type == 'simple':
				self.assertLess(result.get('processing_time', 0), 2.0)
			elif case_type == 'complex':
				self.assertLess(result.get('processing_time', 0), 5.0)
			else:  # mixed
				self.assertLess(result.get('processing_time', 0), 3.0)
		
		log_test_data(performance_metrics, "Performance Metrics")

if __name__ == '__main__':
	unittest.main()