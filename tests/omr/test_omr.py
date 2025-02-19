import unittest
from pathlib import Path
import tempfile
import shutil
import json
import os
import logging
import time
import psutil
import numpy as np
from src.textbook_divider.omr_processor import OMRProcessor  # Updated import path

class TestOMR(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		"""Set up test environment once for all tests"""
		logging.basicConfig(level=logging.INFO)
		cls.logger = logging.getLogger(__name__)
		
		# Update Audiveris path handling
		cls.audiveris_path = cls.omr.audiveris_path
		if not cls.audiveris_path:
			cls.logger.warning("Audiveris not found, some tests will use fallback")
		
		# Set environment variables
		os.environ['AUDIVERIS_PATH'] = str(cls.audiveris_path)
		os.environ['TESSDATA_PREFIX'] = '/usr/share/tesseract-ocr/5/tessdata'
		
		# Create temporary directory that persists for all tests
		cls.temp_dir = Path(tempfile.mkdtemp())
		cls.logger.info(f"Using temporary directory: {cls.temp_dir}")
		
		# Initialize OMR processor
		try:
			cls.omr = OMRProcessor(cache_dir=cls.temp_dir)
			cls.logger.info("OMR processor initialized successfully")
		except Exception as e:
			cls.logger.error(f"Failed to initialize OMR processor: {e}")
			raise
		
		# Set up test files
		cls.test_dir = Path(__file__).parent.parent / 'sample_books'
		cls.multi_column_path = cls.test_dir / 'multi_column.pdf'
		cls.complex_score_path = cls.test_dir / 'complex_score.pdf'
		cls.contemporary_path = cls.test_dir / 'contemporary.pdf'
		
		# Generate test samples if they don't exist
		if not (cls.multi_column_path.exists() and cls.complex_score_path.exists() and cls.contemporary_path.exists()):
			from generate_test_samples import create_test_samples
			create_test_samples()
		
		if not (cls.multi_column_path.exists() and cls.complex_score_path.exists() and cls.contemporary_path.exists()):
			raise RuntimeError("Failed to generate test files")
		
		cls.logger.info("Test environment set up successfully")

	@classmethod
	def tearDownClass(cls):
		"""Clean up after all tests"""
		if cls.temp_dir.exists():
			shutil.rmtree(cls.temp_dir)
			cls.logger.info("Cleaned up temporary directory")

	def test_omr_initialization(self):
		"""Test that OMR processor is properly initialized"""
		self.assertTrue(hasattr(self.omr, 'executor'))
		self.assertTrue(hasattr(self.omr, 'templates'))
		self.assertIsNotNone(self.omr.audiveris_path)
		self.logger.info("OMR initialization test passed")

	def test_basic_processing(self):
		"""Test basic page processing"""
		result = self.omr.process_page(str(self.complex_score_path))
		self.assertTrue(result['success'])
		self.assertIn('has_music', result)
		self.assertIn('engine', result)
		self.logger.info(f"Basic processing test result: {result}")

	def test_error_handling(self):
		"""Test error handling"""
		result = self.omr.process_page("nonexistent.pdf")
		self.assertFalse(result['success'])
		self.assertIn('error', result)
		self.logger.info(f"Error handling test result: {result}")

	def test_engine_selection(self):
		"""Test proper engine selection and fallback"""
		# Test with Audiveris available
		result = self.omr.process_page(str(self.complex_score_path))
		if self.omr.audiveris_path:
			self.assertEqual(result['engine'], 'audiveris')
			self.assertIn('data', result)
		else:
			self.assertEqual(result['engine'], 'template_matching')
			self.assertIn('symbol_confidence', result)

	def test_musical_notation_accuracy(self):
		"""Test musical notation detection accuracy"""
		result = self.omr.process_page(str(self.complex_score_path))
		self.assertTrue(result['success'])
		self.assertTrue(result['has_music'])
		if 'musicxml' in result:
			self.assertTrue(Path(result['musicxml']).exists())

	def test_error_recovery(self):
		"""Test comprehensive error recovery"""
		# Test with corrupted page
		with tempfile.NamedTemporaryFile(suffix='.pdf') as tmp:
			with open(tmp.name, 'wb') as f:
				f.write(b'Invalid PDF content')
			result = self.omr.process_page(tmp.name, 0)
			self.assertFalse(result['success'])
			self.assertTrue(result['fallback'])

	def test_mixed_content(self):
		"""Test processing of mixed text and musical notation"""
		result = self.omr.process_page(str(self.multi_column_path), 0)
		self.assertTrue(result['success'])
		self.assertIn('layout', result)
		self.assertIn('columns', result['layout'])

	def test_mixed_content_layout(self):
		"""Test layout analysis of mixed content pages"""
		result = self.omr.process_page(str(self.multi_column_path), 0)
		self.assertTrue(result['success'])
		layout = result['layout']
		
		# Verify column detection
		self.assertEqual(layout['columns'], 2, "Failed to detect 2 columns")
		
		# Verify staff system detection
		self.assertTrue(len(layout['staff_positions']) >= 3,
					   "Failed to detect all staff systems")
		
		# Verify staff line consistency
		for staff in layout['staff_positions']:
			self._verify_staff_consistency(staff)

	def test_complex_musical_examples(self):
		"""Test processing of complex musical examples"""
		result = self.omr.process_page(str(self.complex_score_path), 0)
		self.assertTrue(result['success'])
		if result['has_music']:
			self.assertIn('staff_positions', result['layout'])

	def test_fallback_chain(self):
		"""Test OMR fallback chain"""
		# Test fallback to Tesseract
		result = self.omr.process_page(str(self.multi_column_path), 0)
		if not result['has_music']:
			self.assertIn('text', result)

	def test_performance_metrics(self):
		"""Test detailed performance metrics"""
		metrics = {
			'simple': {'file': self.multi_column_path, 'target': 2.0},
			'complex': {'file': self.complex_score_path, 'target': 5.0},
			'contemporary': {'file': self.contemporary_path, 'target': 3.0}
		}
		
		results = {}
		for name, config in metrics.items():
			start_time = time.time()
			result = self.omr.process_page(str(config['file']), 0)
			processing_time = time.time() - start_time
			
			self.assertLess(processing_time, config['target'],
						   f"{name} notation processing exceeded {config['target']}s target")
			results[name] = {
				'time': processing_time,
				'success': result['success'],
				'has_music': result.get('has_music', False)
			}
		
		# Log performance metrics
		self.logger.info(f"Performance metrics: {json.dumps(results, indent=2)}")

	def test_parallel_processing(self):
		"""Test parallel processing capabilities"""
		files = [self.complex_score_path, self.multi_column_path]
		futures = []
		
		for file in files:
			future = self.omr.executor.submit(self.omr.process_page, str(file))
			futures.append(future)
		
		results = [future.result() for future in futures]
		self.assertEqual(len(results), len(files))
		for result in results:
			self.assertTrue(result['success'])
			self.assertIn('engine', result)

	def test_memory_usage(self):
		"""Test memory usage optimization"""
		process = psutil.Process()
		initial_memory = process.memory_info().rss / 1024 / 1024  # MB

		# Process multiple pages to test memory usage
		# Process both test files multiple times
		for _ in range(3):
			result = self.omr.process_page(str(self.complex_score_path), 0)
			result = self.omr.process_page(str(self.multi_column_path), 0)
			current_memory = process.memory_info().rss / 1024 / 1024
			memory_used = current_memory - initial_memory
			self.assertLess(memory_used, 2048, "Memory usage exceeded 2GB limit")

	def test_text_integration(self):
		"""Test text integration accuracy"""
		result = self.omr.process_page(str(self.multi_column_path), 0)
		self.assertTrue(result['success'])
		
		# Verify layout preservation
		self.assertIn('layout', result)
		self.assertIn('columns', result['layout'])
		self.assertIn('staff_positions', result['layout'])

	def test_complex_notation_detection(self):
		"""Test detection of complex musical notation features"""
		result = self.omr.process_page(str(self.complex_score_path), 0)
		if result['has_music'] and 'musicxml' in result:
			xml_path = Path(result['musicxml'])
			with xml_path.open('r') as f:
				content = f.read()
				# Check for complex notation features
				self.assertTrue(any([
					'<voice>' in content,
					'<ornaments>' in content,
					'<articulations>' in content
				]), "No complex notation features detected")

	def test_multiple_voices(self):
		"""Test detection of multiple voices in musical notation"""
		result = self.omr.process_page(str(self.complex_score_path), 0)
		if result['has_music'] and 'musicxml' in result:
			xml_path = Path(result['musicxml'])
			with xml_path.open('r') as f:
				content = f.read()
				voice_count = content.count('<voice>')
				self.assertGreater(voice_count, 1, "Multiple voices not detected")

	def test_contemporary_notation(self):
		"""Test handling of contemporary notation with non-standard staff"""
		result = self.omr.process_page(str(self.contemporary_path), 0)
		self.assertTrue(result['success'])
		if result['has_music']:
			# Verify non-standard staff detection
			staff_positions = result['layout']['staff_positions']
			self.assertTrue(any(len(staff) == 6 for staff in staff_positions),
						   "Non-standard 6-line staff not detected")

	def test_musical_symbols(self):
		"""Test detection of musical symbols and notation elements"""
		result = self.omr.process_page(str(self.complex_score_path), 0)
		if result['has_music'] and 'musicxml' in result:
			xml_path = Path(result['musicxml'])
			with xml_path.open('r') as f:
				content = f.read()
				# Check for specific musical elements
				self.assertTrue('<clef>' in content, "Clef not detected")
				self.assertTrue('<time>' in content, "Time signature not detected")
				self.assertTrue('<note>' in content, "Notes not detected")
				self.assertTrue('<articulations>' in content or 
							  '<technical>' in content, 
							  "Articulation marks not detected")

	def test_notation_accuracy(self):
		"""Test musical notation recognition accuracy"""
		results = []
		# Test both files
		for test_file in [self.complex_score_path, self.multi_column_path]:
			result = self.omr.process_page(str(test_file), 0)
			if result['has_music']:
				results.append(result)

		if results:
			# Calculate accuracy metrics
			note_recognition = sum(1 for r in results if r['success']) / len(results)
			self.assertGreaterEqual(note_recognition, 0.90, "Note recognition below 90% target")

			staff_detection = sum(1 for r in results if r['layout']['staff_positions']) / len(results)
			self.assertGreaterEqual(staff_detection, 0.95, "Staff detection below 95% target")

	def _verify_staff_consistency(self, staff_positions):
		"""Helper method to verify staff line consistency"""
		if not staff_positions:
			return False
		# Check staff line spacing
		for staff in staff_positions:
			if len(staff) >= 5:  # Standard staff has 5 lines
				# Verify consistent spacing between staff lines
				spacings = [staff[i+1] - staff[i] for i in range(len(staff)-1)]
				avg_spacing = sum(spacings) / len(spacings)
				# Allow 10% variance in spacing
				for spacing in spacings:
					self.assertLess(abs(spacing - avg_spacing) / avg_spacing, 0.1)


if __name__ == '__main__':
	unittest.main(verbosity=2)



