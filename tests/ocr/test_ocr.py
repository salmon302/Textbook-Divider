#!/usr/bin/env python3

import unittest
from pathlib import Path
from textbook_divider.ocr_processor import OCRProcessor
from textbook_divider.file_handler import PDFHandler, ImageHandler
from PIL import Image
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestOCRProcessing(unittest.TestCase):
	def setUp(self):
		self.ocr = OCRProcessor(lang='eng')
		self.pdf_handler = PDFHandler()
		self.image_handler = ImageHandler()
		self.test_dir = Path(__file__).parent
		self.input_dir = self.test_dir.parent / 'input'
		self.test_data_dir = self.test_dir / 'sample_books'
		
	def test_image_preprocessing(self):
		"""Test image preprocessing steps"""
		img = Image.new('RGB', (800, 600), color='white')
		processed = self.ocr.preprocess_image(img)
		self.assertIsInstance(processed, Image.Image)
		
	def test_mathematical_notation(self):
		"""Test mathematical notation recognition"""
		test_file = self.input_dir / "David Lewin - Generalized Musical Intervals and Transformations (2007).pdf"
		if test_file.exists():
			content = self.pdf_handler.read_content(test_file, max_pages=5)
			self.assertTrue(any(char in content for char in '∫∑∏√∆∇∈'))
			self.assertTrue('theorem' in content.lower() or 'lemma' in content.lower())
			
	def test_musical_notation(self):
		"""Test musical notation recognition"""
		test_file = self.input_dir / "Arnold Schoenberg, Gerald Strang, Leonard Stein - Fundamentals of Musical Composition (1982, Faber & Faber) - libgen.li.pdf"
		if test_file.exists():
			content = self.pdf_handler.read_content(test_file, max_pages=5)
			musical_terms = ['tempo', 'allegro', 'andante', 'chord', 'scale', 'note']
			self.assertTrue(any(term in content.lower() for term in musical_terms))
			
	def test_complex_layout(self):
		"""Test handling of complex page layouts"""
		test_file = self.input_dir / "(Oxford Studies in Music Theory) Dmitri Tymoczko - A Geometry of Music_ Harmony and Counterpoint in the Extended Common Practice-Oxford University Press (2011).pdf"
		if test_file.exists():
			content = self.pdf_handler.read_content(test_file, max_pages=5)
			# Check for multi-column text preservation
			self.assertIsInstance(content, str)
			self.assertTrue(len(content) > 0)
			
	def test_figure_detection(self):
		"""Test detection and handling of figures and diagrams"""
		test_file = self.input_dir / "Fred LErdahl - Tonal Pitch Space-Oxford University Press (2001).pdf"
		if test_file.exists():
			content = self.pdf_handler.read_content(test_file, max_pages=5)
			figure_markers = ['figure', 'fig.', 'diagram', 'illustration']
			self.assertTrue(any(marker in content.lower() for marker in figure_markers))
			
	def test_text_cleaning(self):
		"""Test text cleaning and normalization"""
		test_text = "Chapter 1\nThis is a test.\nThis is-\nbroken."
		cleaned = self.ocr.clean_text(test_text)
		self.assertNotIn("-\n", cleaned)
		self.assertIn("broken", cleaned)
		
	def test_ocr_accuracy(self):
		"""Test OCR accuracy against ground truth"""
		test_pdf = self.test_data_dir / "test.pdf"
		if test_pdf.exists():
			content = self.pdf_handler.read_content(test_pdf)
			# Compare with ground truth if available
			ground_truth_file = self.test_dir / "ground_truth" / "test.pdf.txt"
			if ground_truth_file.exists():
				with open(ground_truth_file, 'r') as f:
					ground_truth = f.read()
				# Basic accuracy check (can be enhanced with more sophisticated metrics)
				self.assertGreater(len(content), 0)
				self.assertTrue(any(word in content for word in ground_truth.split()))

if __name__ == '__main__':
	unittest.main()