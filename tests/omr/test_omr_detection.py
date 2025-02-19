import unittest
from pathlib import Path
import cv2
import numpy as np
from textbook_divider.omr_processor import OMRProcessor
import tempfile
import os
import logging

class TestOMRDetection(unittest.TestCase):
	def setUp(self):
		self.processor = OMRProcessor()
		self.logger = logging.getLogger(__name__)
		self.test_dir = Path(tempfile.mkdtemp())
		self.sample_dir = Path(__file__).parent.parent / 'sample_books'
		
	def tearDown(self):
		if self.test_dir.exists():
			import shutil
			shutil.rmtree(self.test_dir)
		
	def create_test_image(self, with_staff=True, with_notes=True):
		"""Create a test image with musical notation"""
		img = np.full((400, 300), 255, dtype=np.uint8)
		
		if with_staff:
			# Draw 5 staff lines
			for i in range(5):
				y = 100 + i * 20
				cv2.line(img, (50, y), (250, y), 0, 2)
		
		if with_notes:
			# Draw quarter notes
			cv2.circle(img, (100, 130), 6, 0, -1)  # note head
			cv2.line(img, (106, 130), (106, 100), 0, 2)  # stem
			
			cv2.circle(img, (150, 150), 6, 0, -1)  # note head
			cv2.line(img, (156, 150), (156, 120), 0, 2)  # stem
		
		return img
	
	def test_staff_detection_audiveris(self):
		"""Test staff line detection using Audiveris"""
		if not self.processor.audiveris_path:
			self.skipTest("Audiveris not available")
			
		img = self.create_test_image(with_staff=True, with_notes=True)
		with tempfile.NamedTemporaryFile(suffix='.png') as tmp:
			cv2.imwrite(tmp.name, img)
			result = self.processor.process_page(tmp.name)
		
		self.assertTrue(result['success'])
		self.assertEqual(result['engine'], 'audiveris')
		self.assertTrue(result['has_music'])
		self.assertIn('data', result)
	
	def test_staff_detection_template(self):
		"""Test staff line detection using template matching"""
		img = self.create_test_image(with_staff=True, with_notes=False)
		
		# Force template matching by temporarily disabling Audiveris
		original_path = self.processor.audiveris_path
		self.processor.audiveris_path = None
		
		try:
			with tempfile.NamedTemporaryFile(suffix='.png') as tmp:
				cv2.imwrite(tmp.name, img)
				result = self.processor.process_page(tmp.name)
			
			self.assertTrue(result['success'])
			self.assertEqual(result['engine'], 'template_matching')
			self.assertIn('staff_positions', result)
			if result['staff_positions']:
				self.assertEqual(len(result['staff_positions'][0]), 5)
		finally:
			self.processor.audiveris_path = original_path
	
	def test_symbol_detection(self):
		"""Test musical symbol detection with both engines"""
		img = self.create_test_image(with_staff=True, with_notes=True)
		
		with tempfile.NamedTemporaryFile(suffix='.png') as tmp:
			cv2.imwrite(tmp.name, img)
			
			# Test with Audiveris if available
			if self.processor.audiveris_path:
				result = self.processor.process_page(tmp.name)
				self.assertTrue(result['success'])
				self.assertEqual(result['engine'], 'audiveris')
				self.assertIn('data', result)
			
			# Test with template matching
			self.processor.audiveris_path = None
			result = self.processor.process_page(tmp.name)
			self.assertTrue(result['success'])
			self.assertEqual(result['engine'], 'template_matching')
			self.assertIn('symbol_confidence', result)
			self.assertGreater(result['symbol_confidence']['notes'], 0.5)

	def test_layout_detection(self):
		"""Test layout detection with musical content"""
		img = self.create_test_image(with_staff=True, with_notes=True)
		test_img_path = self.test_dir / "temp_test.png"
		cv2.imwrite(str(test_img_path), img)
		
		try:
			result = self.processor.process_page(str(test_img_path))
			self.assertTrue(result['success'])
			self.assertTrue(result['has_music'])
			
			if result['engine'] == 'audiveris':
				self.assertIn('data', result)
			else:
				self.assertIn('symbol_confidence', result)
				self.assertIn('staff_positions', result)
		finally:
			if test_img_path.exists():
				test_img_path.unlink()

	def test_real_book_processing(self):
		"""Test processing with real music book sample"""
		test_file = self.sample_dir / "basic_score.pdf"
		if not test_file.exists():
			self.skipTest("Test file not found")
		
		result = self.processor.process_page(str(test_file))
		self.assertTrue(result['success'])
		self.assertTrue(result['has_music'])
		
		if result['engine'] == 'audiveris':
			self.assertIn('data', result)
		else:
			self.assertIn('symbol_confidence', result)

if __name__ == '__main__':
	unittest.main()