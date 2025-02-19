import unittest
from pathlib import Path
from textbook_divider.omr_processor import OMRProcessor
import logging
import tempfile
import shutil
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import time
import psutil
import os
from unittest import skip

class TestAdvancedOMR(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.test_dir = Path(__file__).parent
		cls.sample_dir = cls.test_dir / 'sample_books'
		cls.omr = OMRProcessor(cache_dir=cls.test_dir / 'cache' / 'omr')
		cls.temp_dir = Path(tempfile.mkdtemp())

	@classmethod
	def tearDownClass(cls):
		if cls.temp_dir.exists():
			shutil.rmtree(cls.temp_dir)

	def generate_test_image(self, content_type='basic'):
		"""Generate test images with different musical notation patterns"""
		img = Image.new('RGB', (800, 1000), 'white')
		draw = ImageDraw.Draw(img)
		
		if content_type == 'mixed':
			# Add text and musical notation
			draw.text((50, 50), "Chapter 1: Basic Theory", fill='black')
			# Add staff lines
			y_start = 200
			for i in range(5):
				draw.line([(50, y_start + i*10), (750, y_start + i*10)], fill='black')
		elif content_type == 'complex':
			# Add complex musical notation
			y_start = 100
			# Multiple staves
			for staff in range(3):
				staff_y = y_start + staff * 100
				# Staff lines
				for i in range(5):
					draw.line([(50, staff_y + i*10), (750, staff_y + i*10)], fill='black')
				# Add clef and notes
				draw.ellipse([60, staff_y+15, 80, staff_y+35], fill='black')  # Clef
				# Add notes
				for x in range(100, 700, 100):
					draw.ellipse([x, staff_y+20, x+10, staff_y+30], fill='black')
		
		return img

	def test_mixed_content_detection(self):
		"""Test detection of mixed text and musical notation"""
		img = self.generate_test_image('mixed')
		test_pdf = self.temp_dir / "mixed_content.pdf"
		img.save(str(test_pdf))
		
		result = self.omr.process_page(str(test_pdf), 0)
		self.assertTrue(result['success'])
		self.assertTrue(result['has_music'])
		if result['has_music']:
			self.assertIn('musicxml', result)

	def test_complex_notation(self):
		"""Test processing of complex musical notation"""
		sample_path = self.sample_dir / 'complex_score.pdf'
		if not sample_path.exists():
			self.skipTest("Complex score sample not found")
		
		result = self.omr.process_page(str(sample_path), 0)
		self.assertTrue(result['success'])
		if result['has_music']:
			self.assertIn('musicxml', result)
			# Verify staff detection
			self._verify_staff_detection(result['musicxml'])

	def test_error_recovery(self):
		"""Test error recovery mechanisms"""
		# Test with corrupted PDF
		corrupt_pdf = self.temp_dir / "corrupt.pdf"
		with corrupt_pdf.open('wb') as f:
			f.write(b'Invalid PDF content')
		
		result = self.omr.process_page(str(corrupt_pdf), 0)
		self.assertFalse(result['success'])
		self.assertIn('error', result)
		self.assertIn('fallback', result)

	def test_multi_column_layout(self):
		"""Test processing of multi-column layouts"""
		sample_path = self.sample_dir / 'multi_column.pdf'
		if not sample_path.exists():
			self.skipTest("Multi-column sample not found")
		
		result = self.omr.process_page(str(sample_path), 0)
		self.assertTrue(result['success'])
		# Verify column detection
		if result['has_music']:
			self._verify_column_detection(result)

	def _verify_staff_detection(self, musicxml_path):
		"""Verify staff detection in MusicXML output"""
		import xml.etree.ElementTree as ET
		tree = ET.parse(musicxml_path)
		root = tree.getroot()
		staves = root.findall(".//staff")
		self.assertGreater(len(staves), 0, "No staff elements detected")

	def _verify_column_detection(self, result):
		"""Verify multi-column layout detection"""
		if 'layout' in result:
			self.assertIn('columns', result['layout'])
			self.assertGreater(result['layout']['columns'], 1)

	def test_notation_accuracy(self):
		"""Test accuracy of musical notation detection"""
		img = self.generate_test_image('complex')
		test_pdf = self.temp_dir / "notation_test.pdf"
		img.save(str(test_pdf))
		
		result = self.omr.process_page(str(test_pdf), 0)
		self.assertTrue(result['success'])
		if result['has_music']:
			accuracy = self._calculate_notation_accuracy(result['musicxml'])
			self.assertGreaterEqual(accuracy, 0.85, "Notation detection accuracy below threshold")

	def test_comprehensive_error_recovery(self):
		"""Test comprehensive error recovery mechanisms"""
		# Test with partially corrupted image
		img = self.generate_test_image('complex')
		# Add noise to image
		img_array = np.array(img)
		noise = np.random.normal(0, 50, img_array.shape)
		noisy_img = np.clip(img_array + noise, 0, 255).astype(np.uint8)
		test_pdf = self.temp_dir / "noisy_test.pdf"
		Image.fromarray(noisy_img).save(str(test_pdf))
		
		result = self.omr.process_page(str(test_pdf), 0)
		self.assertTrue('recovery_attempts' in result)
		if not result['success']:
			self.assertTrue('fallback_result' in result)

	def _calculate_notation_accuracy(self, musicxml_path):
		"""Calculate accuracy of musical notation detection"""
		import xml.etree.ElementTree as ET
		tree = ET.parse(musicxml_path)
		root = tree.getroot()
		
		# Count detected musical elements
		notes = len(root.findall(".//note"))
		measures = len(root.findall(".//measure"))
		staves = len(root.findall(".//staff"))
		
		# Basic accuracy calculation (can be enhanced based on ground truth)
		expected_elements = 15  # Based on our test image generation
		detected_elements = notes + measures + staves
		return min(1.0, detected_elements / expected_elements)

	def test_performance_simple_notation(self):
		"""Test processing time for simple musical notation"""
		img = self.generate_test_image('basic')
		test_pdf = self.temp_dir / "simple_perf.pdf"
		img.save(str(test_pdf))
		
		start_time = time.time()
		result = self.omr.process_page(str(test_pdf), 0)
		processing_time = time.time() - start_time
		
		self.assertTrue(result['success'])
		self.assertLess(processing_time, 2.0, "Simple notation processing exceeded time target")

	def test_performance_complex_score(self):
		"""Test processing time for complex musical scores"""
		img = self.generate_test_image('complex')
		test_pdf = self.temp_dir / "complex_perf.pdf"
		img.save(str(test_pdf))
		
		start_time = time.time()
		result = self.omr.process_page(str(test_pdf), 0)
		processing_time = time.time() - start_time
		
		self.assertTrue(result['success'])
		self.assertLess(processing_time, 5.0, "Complex score processing exceeded time target")

	def test_memory_usage(self):
		"""Test memory usage during processing"""
		img = self.generate_test_image('complex')
		test_pdf = self.temp_dir / "memory_test.pdf"
		img.save(str(test_pdf))
		
		process = psutil.Process(os.getpid())
		initial_memory = process.memory_info().rss / 1024 / 1024  # Convert to MB
		
		result = self.omr.process_page(str(test_pdf), 0)
		
		peak_memory = process.memory_info().rss / 1024 / 1024  # Convert to MB
		memory_used = peak_memory - initial_memory
		
		self.assertTrue(result['success'])
		self.assertLess(memory_used, 2048, "Memory usage exceeded 2GB threshold")

	def test_staff_detection_accuracy(self):
		"""Test accuracy of staff line detection"""
		img = self.generate_test_image('complex')
		test_pdf = self.temp_dir / "staff_test.pdf"
		img.save(str(test_pdf))
		
		result = self.omr.process_page(str(test_pdf), 0)
		self.assertTrue(result['success'])
		if result['has_music']:
			staff_accuracy = self._calculate_staff_accuracy(result['musicxml'])
			self.assertGreaterEqual(staff_accuracy, 0.95, "Staff detection accuracy below target")

	def test_symbol_classification(self):
		"""Test accuracy of musical symbol classification"""
		img = self.generate_test_image('complex')
		test_pdf = self.temp_dir / "symbol_test.pdf"
		img.save(str(test_pdf))
		
		result = self.omr.process_page(str(test_pdf), 0)
		self.assertTrue(result['success'])
		if result['has_music']:
			symbol_accuracy = self._calculate_symbol_accuracy(result['musicxml'])
			self.assertGreaterEqual(symbol_accuracy, 0.85, "Symbol classification accuracy below target")

	def _calculate_staff_accuracy(self, musicxml_path):
		"""Calculate accuracy of staff line detection"""
		import xml.etree.ElementTree as ET
		tree = ET.parse(musicxml_path)
		root = tree.getroot()
		
		# Count detected staves and staff lines
		staves = root.findall(".//staff")
		staff_lines = root.findall(".//staff-lines")
		
		# Our test image has 3 staves with 5 lines each
		expected_staves = 3
		expected_lines = 15
		
		staff_count = len(staves)
		line_count = sum(int(sl.text or 0) for sl in staff_lines)
		
		return min(1.0, (staff_count / expected_staves + line_count / expected_lines) / 2)

	def _calculate_symbol_accuracy(self, musicxml_path):
		"""Calculate accuracy of musical symbol classification"""
		import xml.etree.ElementTree as ET
		tree = ET.parse(musicxml_path)
		root = tree.getroot()
		
		# Count different types of musical symbols
		notes = len(root.findall(".//note"))
		clefs = len(root.findall(".//clef"))
		
		# Our test image has 18 notes (6 per staff * 3 staves) and 3 clefs
		expected_notes = 18
		expected_clefs = 3
		
		note_accuracy = min(1.0, notes / expected_notes)
		clef_accuracy = min(1.0, clefs / expected_clefs)
		
		return (note_accuracy + clef_accuracy) / 2

if __name__ == '__main__':
	unittest.main()