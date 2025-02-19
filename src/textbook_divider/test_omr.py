import unittest
from pathlib import Path
from textbook_divider.omr_processor import OMRProcessor
import logging
import os
import tempfile
from PIL import Image
import numpy as np

class TestOMRProcessor(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		logging.basicConfig(level=logging.INFO)
		cls.test_dir = Path(__file__).parent.parent.parent / 'tests'
		cls.test_dir.mkdir(exist_ok=True)
		cls.omr = OMRProcessor(cache_dir=cls.test_dir / 'cache' / 'omr')
		
	def setUp(self):
		"""Create temporary test files"""
		self.temp_dir = Path(tempfile.mkdtemp())
		
	def tearDown(self):
		"""Clean up temporary files"""
		import shutil
		if self.temp_dir.exists():
			shutil.rmtree(self.temp_dir)
	
	def test_init(self):
		"""Test Audiveris initialization"""
		self.assertTrue(hasattr(self.omr, 'audiveris'))
		self.assertTrue(hasattr(self.omr, 'Score'))
		self.assertTrue(hasattr(self.omr, 'Book'))
	
	def test_process_page_with_music(self):
		"""Test processing a page with musical notation"""
		sample_path = self.test_dir / 'sample_books' / 'schoenberg_fundamentals.pdf'
		if not sample_path.exists():
			self.skipTest("Sample book not found")
			
		result = self.omr.process_page(str(sample_path), 0)
		self.assertTrue(result['success'])
		self.assertIn('has_music', result)
		
		if result['has_music']:
			self.assertIn('musicxml', result)
			self.assertTrue(Path(result['musicxml']).exists())
			if result.get('midi'):
				self.assertTrue(Path(result['midi']).exists())

	def test_process_page_no_music(self):
		"""Test processing a page without musical notation"""
		# Create a test PDF with just text
		text_pdf = self.temp_dir / "text_only.pdf"
		img = Image.new('RGB', (800, 1000), color='white')
		img.save(str(text_pdf))
		
		result = self.omr.process_page(str(text_pdf), 0)
		self.assertTrue(result['success'])
		self.assertFalse(result['has_music'])
		self.assertIn('text', result)

	def test_process_multiple_pages(self):
		"""Test processing multiple pages"""
		sample_path = self.test_dir / 'sample_books' / 'schoenberg_fundamentals.pdf'
		if not sample_path.exists():
			self.skipTest("Sample book not found")
			
		results = self.omr.process_pages(str(sample_path), 0, 2)
		self.assertEqual(len(results), 3)
		for result in results:
			self.assertIn('success', result)
			self.assertIn('has_music', result)

	def test_cache_functionality(self):
		"""Test caching mechanism"""
		sample_path = self.test_dir / 'sample_books' / 'schoenberg_fundamentals.pdf'
		if not sample_path.exists():
			self.skipTest("Sample book not found")
			
		# First run - should process
		result1 = self.omr.process_page(str(sample_path), 0)
		
		# Second run - should use cache
		result2 = self.omr.process_page(str(sample_path), 0)
		
		self.assertEqual(result1, result2)

	def test_error_handling(self):
		"""Test error handling with invalid input"""
		# Test with non-existent file
		result = self.omr.process_page("nonexistent.pdf", 0)
		self.assertFalse(result['success'])
		self.assertIn('error', result)
		
		# Test with invalid page number
		sample_path = self.test_dir / 'sample_books' / 'schoenberg_fundamentals.pdf'
		if sample_path.exists():
			result = self.omr.process_page(str(sample_path), 9999)
			self.assertFalse(result['success'])
			self.assertIn('error', result)

if __name__ == '__main__':
	unittest.main()
