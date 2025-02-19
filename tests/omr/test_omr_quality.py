#!/usr/bin/env python3

import unittest
import json
from pathlib import Path
import logging
from textbook_divider.omr_processor import OMRProcessor
from textbook_divider.text_processor import TextProcessor

class TestOMRQuality(unittest.TestCase):
	def setUp(self):
		self.logger = logging.getLogger(__name__)
		self.processor = OMRProcessor()
		self.text_processor = TextProcessor()
		self.test_dir = Path(__file__).parent.parent
		self.sample_dir = self.test_dir / 'sample_books'
		self.metrics_dir = self.test_dir / 'metrics'
		self.metrics_dir.mkdir(exist_ok=True)
		
		# Ground truth data for accuracy testing
		self.ground_truth = {
			'basic_score.pdf': {
				'staff_count': 1,
				'note_count': 2,
				'clef_type': 'treble',
				'time_signature': '4/4'
			},
			'complex_score.pdf': {
				'staff_count': 3,
				'note_count': 6,
				'voices': 2,
				'has_ornaments': True
			}
		}

	def test_notation_accuracy(self):
		"""Test musical notation recognition accuracy"""
		results = {}
		
		for filename, truth in self.ground_truth.items():
			file_path = self.sample_dir / filename
			if not file_path.exists():
				continue
				
			result = self.processor.process_page(str(file_path))
			self.assertTrue(result['success'])
			
			# Calculate accuracy metrics
			if result['engine'] == 'audiveris':
				accuracy = self._calculate_audiveris_accuracy(result['data'], truth)
			else:
				accuracy = self._calculate_template_accuracy(result, truth)
			
			# Assert accuracy targets
			self.assertGreaterEqual(accuracy['note_recognition'], 0.90,
								  "Note recognition below 90% target")
			self.assertGreaterEqual(accuracy['staff_detection'], 0.95,
								  "Staff detection below 95% target")
			self.assertGreaterEqual(accuracy['symbol_classification'], 0.85,
								  "Symbol classification below 85% target")
			
			results[filename] = accuracy
		
		self.save_metrics(results, 'notation_accuracy.json')

	def test_text_integration(self):
		"""Test text integration accuracy with musical content"""
		test_files = ['mixed_layout.pdf', 'multi_column.pdf']
		results = {}
		
		for filename in test_files:
			file_path = self.sample_dir / filename
			if not file_path.exists():
				continue
			
			result = self.processor.process_page(str(file_path))
			self.assertTrue(result['success'])
			
			# Verify layout preservation
			layout_score = self._verify_layout_preservation(result)
			self.assertGreaterEqual(layout_score, 0.90,
								  "Layout preservation below 90%")
			
			# Verify format retention
			format_score = self._verify_format_retention(result)
			self.assertGreaterEqual(format_score, 0.90,
								  "Format retention below 90%")
			
			results[filename] = {
				'layout_preservation': layout_score,
				'format_retention': format_score
			}
		
		self.save_metrics(results, 'text_integration_accuracy.json')

	def _calculate_audiveris_accuracy(self, data, truth):
		"""Calculate accuracy metrics for Audiveris output"""
		detected_notes = len(data.get('notes', []))
		detected_staves = len(data.get('staves', []))
		
		return {
			'note_recognition': min(1.0, detected_notes / truth['note_count']),
			'staff_detection': min(1.0, detected_staves / truth['staff_count']),
			'symbol_classification': self._calculate_symbol_accuracy(data)
		}

	def _calculate_template_accuracy(self, result, truth):
		"""Calculate accuracy metrics for template matching"""
		confidence = result.get('symbol_confidence', {})
		return {
			'note_recognition': confidence.get('notes', 0),
			'staff_detection': len(result.get('staff_positions', [])) / truth['staff_count'],
			'symbol_classification': confidence.get('clefs', 0)
		}

	def _verify_layout_preservation(self, result):
		"""Verify layout preservation in mixed content"""
		if 'layout' not in result:
			return 0.0
			
		layout = result['layout']
		score = 0.0
		
		# Check column detection
		if 'columns' in layout:
			score += 0.5
		
		# Check staff positioning
		if 'staff_positions' in layout:
			score += 0.5
			
		return score

	def _verify_format_retention(self, result):
		"""Verify format retention in processed content"""
		if not result.get('has_music'):
			return 0.0
			
		score = 0.0
		
		# Check musical notation format
		if result['engine'] == 'audiveris' and 'data' in result:
			score += 0.6
		elif 'symbol_confidence' in result:
			score += 0.4
			
		# Check text formatting
		if 'text' in result and len(result['text']) > 0:
			score += 0.4
			
		return min(1.0, score)

	def _calculate_symbol_accuracy(self, data):
		"""Calculate symbol classification accuracy"""
		total_symbols = 0
		correct_symbols = 0
		
		for symbol_type in ['notes', 'clefs', 'time_signatures']:
			if symbol_type in data:
				total_symbols += len(data[symbol_type])
				correct_symbols += sum(1 for s in data[symbol_type] 
									if s.get('confidence', 0) > 0.85)
		
		return correct_symbols / total_symbols if total_symbols > 0 else 0.0

	def test_enhanced_staff_detection(self):
		"""Test enhanced staff detection with various scales"""
		test_files = ['basic_score.pdf', 'complex_score.pdf', 'low_res_score.pdf']
		
		for filename in test_files:
			file_path = self.sample_dir / filename
			if not file_path.exists():
				continue
				
			result = self.processor.process_page(str(file_path))
			self.assertTrue(result['success'])
			
			# Verify staff detection
			staff_positions = result.get('staff_positions', [])
			self.assertGreater(len(staff_positions), 0, 
							  f"No staff lines detected in {filename}")
			
			# Verify staff line spacing
			for staff in staff_positions:
				self.assertEqual(len(staff), 5, 
							   f"Invalid staff line count in {filename}")
				spacings = [staff[i+1] - staff[i] for i in range(4)]
				avg_spacing = sum(spacings) / len(spacings)
				max_deviation = max(abs(s - avg_spacing) for s in spacings)
				self.assertLess(max_deviation / avg_spacing, 0.2,
							  f"Inconsistent staff spacing in {filename}")

	def test_error_recovery(self):
		"""Test error recovery mechanisms"""
		test_cases = [
			('corrupted_score.pdf', True),  # Should recover
			('low_res_score.pdf', True),    # Should handle low resolution
			('modern_score.pdf', True),     # Should handle modern notation
		]
		
		for filename, should_recover in test_cases:
			file_path = self.sample_dir / filename
			if not file_path.exists():
				continue
				
			result = self.processor.process_page(str(file_path))
			
			if should_recover:
				self.assertTrue(result['success'],
							  f"Failed to recover from {filename}")
				self.assertTrue(result.get('recovery_attempted', False),
							  f"No recovery attempted for {filename}")
			
			# Verify error details
			if not result['success']:
				error_details = result.get('error_details', {})
				self.assertIn('type', error_details)
				self.assertIn('message', error_details)
				self.assertIn('recovery_possible', error_details)

	def test_mixed_content_handling(self):
		"""Test handling of mixed text and musical content"""
		test_files = ['mixed_layout.pdf', 'multi_column.pdf']
		
		for filename in test_files:
			file_path = self.sample_dir / filename
			if not file_path.exists():
				continue
				
			result = self.processor.process_page(str(file_path))
			self.assertTrue(result['success'])
			
			# Verify mixed content detection
			self.assertTrue(result.get('has_music', False),
						   f"Failed to detect music in {filename}")
			
			# Verify staff positions in mixed content
			staff_positions = result.get('staff_positions', [])
			self.assertGreater(len(staff_positions), 0,
							  f"No staff lines detected in {filename}")
			
			# Verify symbol detection in mixed content
			confidence = result.get('symbol_confidence', {})
			self.assertGreater(confidence.get('notes', 0), 0.7,
							  f"Low note detection confidence in {filename}")

	def save_metrics(self, results: dict, filename: str):
		"""Save quality metrics to JSON file"""
		metrics_file = self.metrics_dir / filename
		with open(metrics_file, 'w') as f:
			json.dump(results, f, indent=2)
		self.logger.info(f"Quality metrics saved to {metrics_file}")

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	unittest.main(verbosity=2)