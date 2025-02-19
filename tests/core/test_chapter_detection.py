import unittest
from pathlib import Path
from typing import List
from textbook_divider.chapter_detector import ChapterDetector, Chapter
from .test_utils import log_test_case, log_test_data, get_test_logger

logger = get_test_logger(__name__)

class TestChapterDetection(unittest.TestCase):
	def setUp(self):
		self.detector = ChapterDetector()
		self.test_cases = {
			"standard": "Chapter 1: Introduction\nContent here\nChapter 2: Methods",
			"roman": "I. First Chapter\nContent\nII. Second Chapter",
			"nested": "1.1 Sub Chapter\nContent\n1.2 Another Sub",
			"mixed": "Chapter One: Intro\nContent\nChapter 2: Next",
			"complex": "Chapter 1 - Introduction to Methods\nWith subtitle\nContent",
			"false_positive": "As mentioned in Chapter 2, we can see..."
		}
		log_test_data(self.test_cases, "Test Cases")

	@log_test_case
	def test_standard_chapters(self):
		"""Test standard chapter format detection"""
		chapters = self.detector.detect_chapters(self.test_cases["standard"])
		log_test_data([ch.__dict__ for ch in chapters], "Detected Chapters")
		self.assertEqual(len(chapters), 2)
		self.assertEqual(chapters[0].number, 1)
		self.assertEqual(chapters[0].title, "Introduction")

	@log_test_case
	def test_roman_numerals(self):
		"""Test Roman numeral chapter detection"""
		chapters = self.detector.detect_chapters(self.test_cases["roman"])
		log_test_data([ch.__dict__ for ch in chapters], "Detected Chapters")
		self.assertEqual(len(chapters), 2)
		self.assertEqual(chapters[0].number, 1)
		self.assertEqual(chapters[1].number, 2)

	@log_test_case
	def test_nested_chapters(self):
		"""Test nested chapter structure detection"""
		chapters = self.detector.detect_chapters(self.test_cases["nested"])
		log_test_data([ch.__dict__ for ch in chapters], "Detected Chapters")
		self.assertEqual(len(chapters), 2)
		self.assertTrue(all(c.is_subchapter for c in chapters))

	@log_test_case
	def test_mixed_formats(self):
		"""Test mixed format chapter detection"""
		chapters = self.detector.detect_chapters(self.test_cases["mixed"])
		log_test_data([ch.__dict__ for ch in chapters], "Detected Chapters")
		self.assertEqual(len(chapters), 2)
		self.assertEqual(chapters[0].number, 1)
		self.assertEqual(chapters[1].number, 2)

	@log_test_case
	def test_complex_titles(self):
		"""Test complex chapter title detection"""
		chapters = self.detector.detect_chapters(self.test_cases["complex"])
		log_test_data([ch.__dict__ for ch in chapters], "Detected Chapters")
		self.assertEqual(len(chapters), 1)
		self.assertTrue(chapters[0].title.startswith("Introduction"))

	@log_test_case
	def test_false_positives(self):
		"""Test handling of false positive chapter references"""
		chapters = self.detector.detect_chapters(self.test_cases["false_positive"])
		log_test_data([ch.__dict__ for ch in chapters], "Detected Chapters")
		self.assertEqual(len(chapters), 0)

	@log_test_case
	def test_chapter_boundaries(self):
		"""Test chapter content boundary detection"""
		text = "Chapter 1\nContent 1\nChapter 2\nContent 2"
		log_test_data(text, "Input Text")
		chapters = self.detector.detect_chapters(text)
		log_test_data([ch.__dict__ for ch in chapters], "Detected Chapters")
		self.assertEqual(len(chapters), 2)
		self.assertIn("Content 1", chapters[0].content)
		self.assertIn("Content 2", chapters[1].content)

if __name__ == '__main__':
	unittest.main()