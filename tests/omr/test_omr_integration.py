#!/usr/bin/env python3

import unittest
import json
from pathlib import Path
import logging
from textbook_divider.omr_processor import OMRProcessor
from textbook_divider.text_processor import TextProcessor

class TestOMRIntegration(unittest.TestCase):
	def setUp(self):
		self.logger = logging.getLogger(__name__)
		self.processor = OMRProcessor()
		self.text_processor = TextProcessor()
		self.test_dir = Path(__file__).parent.parent
		self.sample_dir = self.test_dir / 'sample_books'
		self.metrics_dir = self.test_dir / 'metrics'
		self.metrics_dir.mkdir(exist_ok=True)

	def test_mixed_content_integration(self):
		"""Test OMR with mixed text and musical notation"""
		test_cases = [
			('mixed_layout.pdf', {'expected_staves': 2, 'expected_columns': 2}),
			('multi_column.pdf', {'expected_staves': 3, 'expected_columns': 3}),
			('complex_score.pdf', {'expected_staves': 4, 'expected_columns': 1})
		]

		results = {}
		for filename, expectations in test_cases:
			file_path = self.sample_dir / filename
			if not file_path.exists():
				continue

			result = self.processor.process_page(str(file_path))
			self.assertTrue(result['success'])

			# Verify staff detection in mixed content
			staff_positions = result.get('staff_positions', [])
			self.assertEqual(len(staff_positions), expectations['expected_staves'],
						   f"Incorrect staff count in {filename}")

			# Verify column layout
			if 'layout' in result:
				columns = result['layout'].get('columns', [])
				self.assertEqual(len(columns), expectations['expected_columns'],
							   f"Incorrect column count in {filename}")

			results[filename] = {
				'staff_count': len(staff_positions),
				'column_count': len(result.get('layout', {}).get('columns', [])),
				'engine_used': result.get('engine', 'unknown')
			}

		self.save_metrics(results, 'mixed_content_metrics.json')

	def test_fallback_chain(self):
		"""Test OMR fallback chain (Audiveris → Tesseract → Manual)"""
		test_cases = [
			('corrupted_score.pdf', 'template_matching'),
			('low_res_score.pdf', 'template_matching'),
			('basic_score.pdf', 'audiveris')
		]

		results = {}
		for filename, expected_engine in test_cases:
			file_path = self.sample_dir / filename
			if not file_path.exists():
				continue

			result = self.processor.process_page(str(file_path))
			self.assertTrue(result['success'])

			# Verify correct engine selection
			self.assertEqual(result.get('engine'), expected_engine,
						   f"Incorrect engine selection for {filename}")

			# Verify recovery information
			if expected_engine != 'audiveris':
				self.assertTrue(result.get('recovery_attempted', False),
							  f"No recovery attempted for {filename}")

			results[filename] = {
				'engine_used': result.get('engine'),
				'recovery_attempted': result.get('recovery_attempted', False),
				'success': result['success']
			}

		self.save_metrics(results, 'fallback_chain_metrics.json')

	def test_error_logging(self):
		"""Test error logging and reporting in OMR processing"""
		test_files = ['corrupted_score.pdf', 'low_res_score.pdf']
		
		for filename in test_files:
			file_path = self.sample_dir / filename
			if not file_path.exists():
				continue

			result = self.processor.process_page(str(file_path))

			# Verify error details structure
			if not result['success'] or result.get('recovery_attempted'):
				error_details = result.get('error_details', {})
				self.assertIn('type', error_details)
				self.assertIn('message', error_details)
				self.assertIn('recovery_possible', error_details)

	def save_metrics(self, results: dict, filename: str):
		"""Save integration metrics to JSON file"""
		metrics_file = self.metrics_dir / filename
		with open(metrics_file, 'w') as f:
			json.dump(results, f, indent=2)
		self.logger.info(f"Integration metrics saved to {metrics_file}")

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	unittest.main(verbosity=2)
