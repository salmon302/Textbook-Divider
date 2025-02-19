#!/usr/bin/env python3

import unittest
from pathlib import Path
import sys
import json
from textbook_divider.processor import process_file

class TestPDFProcessing(unittest.TestCase):
	def setUp(self):
		self.test_dir = Path(__file__).parent
		self.input_dir = self.test_dir.parent / "input"
		self.output_dir = self.test_dir / "output"
		
	def test_text_based_pdf(self):
		"""Test processing of text-based PDF"""
		pdf_path = self.input_dir / "David Lewin - Generalized Musical Intervals and Transformations (2007).pdf"
		self.assertTrue(pdf_path.exists(), "Test PDF not found")
		try:
			process_file(pdf_path)
			output_file = self.output_dir / "Lewin_GMIT_output.json"
			self.assertTrue(output_file.exists(), "Output file not created")
			
			with open(output_file) as f:
				result = json.load(f)
			self.assertIn("chapters", result)
			self.assertGreater(len(result["chapters"]), 0)
			
		except Exception as e:
			self.fail(f"Processing failed: {str(e)}")
			
	def test_complex_layout(self):
		"""Test processing of PDF with complex layout"""
		pdf_path = self.input_dir / "Arnold Schoenberg, Gerald Strang, Leonard Stein - Fundamentals of Musical Composition (1982, Faber & Faber) - libgen.li.pdf"
		self.assertTrue(pdf_path.exists(), "Test PDF not found")
		try:
			process_file(pdf_path)
			output_file = self.output_dir / "Schoenberg_Fundamentals_output.json"
			self.assertTrue(output_file.exists(), "Output file not created")
			
			with open(output_file) as f:
				result = json.load(f)
			self.assertIn("features_detected", result.get("metadata", {}))
			
		except Exception as e:
			self.fail(f"Processing failed: {str(e)}")
			
	def test_mathematical_content(self):
		"""Test processing of PDF with mathematical content"""
		pdf_path = self.input_dir / "Fred LErdahl - Tonal Pitch Space-Oxford University Press (2001).pdf"
		self.assertTrue(pdf_path.exists(), "Test PDF not found")
		try:
			process_file(pdf_path)
			output_file = self.output_dir / "Erdahl_PitchSpace_output.json"
			self.assertTrue(output_file.exists(), "Output file not created")
			
			with open(output_file) as f:
				result = json.load(f)
			self.assertTrue(
				result.get("metadata", {}).get("features_detected", {}).get("mathematical_formulas"),
				"Mathematical formulas not detected"
			)
			
		except Exception as e:
			self.fail(f"Processing failed: {str(e)}")
			
	def test_figures_and_diagrams(self):
		"""Test processing of PDF with figures and diagrams"""
		pdf_path = self.input_dir / "(Oxford Studies in Music Theory) Dmitri Tymoczko - A Geometry of Music_ Harmony and Counterpoint in the Extended Common Practice-Oxford University Press (2011).pdf"
		self.assertTrue(pdf_path.exists(), "Test PDF not found")
		try:
			process_file(pdf_path)
			output_file = self.output_dir / "Tymoczko_Geometry_output.json"
			self.assertTrue(output_file.exists(), "Output file not created")
			
			with open(output_file) as f:
				result = json.load(f)
			self.assertTrue(
				result.get("metadata", {}).get("features_detected", {}).get("complex_figures"),
				"Complex figures not detected"
			)
			
		except Exception as e:
			self.fail(f"Processing failed: {str(e)}")

if __name__ == '__main__':
	unittest.main()