#!/usr/bin/env python3

import unittest
from pathlib import Path
import json
import sys
import re

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from textbook_divider.processor import process_file

class TestBasicChapterDetection(unittest.TestCase):
	def setUp(self):
		self.test_dir = Path(__file__).parent.parent
		self.sample_dir = self.test_dir / "sample_books"
		self.output_dir = self.test_dir / "output"
		self.output_dir.mkdir(exist_ok=True)
		
	def test_basic_processing(self):
		"""Test basic file processing"""
		test_file = self.sample_dir / "test_sample.pdf"
		self.assertTrue(test_file.exists(), "Basic test file not found")
		
		result = process_file(test_file)
		output_file = self.output_dir / f"{test_file.stem}_output.json"
		
		with open(output_file) as f:
			data = json.load(f)
			
		self.assertTrue(data["metadata"]["extraction_success"])
	
	def test_complex_content(self):
		"""Test processing of complex content"""
		test_file = self.sample_dir / "complex_sample.txt"
		self.assertTrue(test_file.exists(), "Complex test file not found")
		
		result = process_file(test_file)
		output_file = self.output_dir / f"{test_file.stem}_output.json"
		
		with open(output_file) as f:
			data = json.load(f)
			
		self.assertTrue(data["metadata"]["extraction_success"])
	
	def test_mixed_layout(self):
		"""Test processing of mixed layout content"""
		test_file = self.sample_dir / "mixed_layout.pdf"
		self.assertTrue(test_file.exists(), "Mixed layout test file not found")
		
		result = process_file(test_file)
		output_file = self.output_dir / f"{test_file.stem}_output.json"
		
		with open(output_file) as f:
			data = json.load(f)
			
		self.assertTrue(data["metadata"]["extraction_success"])
		self.assertTrue(data["metadata"]["features_detected"]["mixed_content"])

class TestErrorHandling(unittest.TestCase):
	def setUp(self):
		self.test_dir = Path(__file__).parent.parent
		
	def test_corrupted_file(self):
		"""Test handling of corrupted files"""
		corrupted_file = self.test_dir / "sample_books" / "corrupted_score.pdf"
		self.assertTrue(corrupted_file.exists(), "Corrupted test file not found")
		
		with self.assertRaises(Exception) as context:
			process_file(corrupted_file)
		
		self.assertTrue("Invalid or corrupted file" in str(context.exception))

if __name__ == '__main__':
	unittest.main()
