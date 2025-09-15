import unittest
from textbook_divider.chapter_detector import ChapterDetector

class TestChapterDetectorUnit(unittest.TestCase):
    def setUp(self):
        self.detector = ChapterDetector(debug=True)

    def test_is_year_like(self):
        # Access private via name mangling or rely on public behavior through validation.
        self.assertTrue(self.detector._is_year_like("1937"))
        self.assertTrue(self.detector._is_year_like("1939-40"))
        self.assertTrue(self.detector._is_year_like("1939–1940"))
        self.assertFalse(self.detector._is_year_like("123"))
        self.assertFalse(self.detector._is_year_like("Chapter 1"))

    def test_running_header_detection(self):
        self.assertTrue(self.detector._looks_like_running_header("66 OCTOBER"))
        self.assertTrue(self.detector._looks_like_running_header("OCTOBER 66"))
        self.assertFalse(self.detector._looks_like_running_header("Chapter 2: Methods"))

    def test_deduplicate_matches(self):
        # Matches: (start_pos, num, title, pattern_type, confidence)
        matches = [
            (10, '1', 'Intro', 'standard', 0.9),
            (12, 'I', 'Intro', 'ocr_chapter', 0.92),  # within window, higher conf
            (200, '2', 'Next', 'standard', 0.85),
        ]
        deduped = self.detector._deduplicate_matches(matches)
        # Should keep the higher confidence at ~start 10-12, and the later one.
        self.assertEqual(len(deduped), 2)
        self.assertEqual(deduped[0][0], 10)
        self.assertEqual(deduped[0][3], 'ocr_chapter')

if __name__ == '__main__':
    unittest.main(verbosity=2)
