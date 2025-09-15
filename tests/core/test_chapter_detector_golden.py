import unittest
from textbook_divider.chapter_detector import ChapterDetector

GOLDEN_TEXT = """
64 OCTOBER

CHAPTER 1 Introduction

This is the first paragraph of the chapter. It continues on the next
line without punctuation and should be stitched together properly.

65 OCTOBER

Section I A PRELUDE

Here the text continues with more content that should not create a false
chapter due to headers like 65 OCTOBER. The detection should focus on
CHAPTER 1 and not on the running headers.

1937

A paragraph that contains a stand-alone year should not be treated as a
chapter title.
""".strip()

class TestChapterDetectorGolden(unittest.TestCase):
    def test_detect_chapters(self):
        det = ChapterDetector(min_confidence=0.5, enable_title_line=True)
        chapters = det.detect_chapters(GOLDEN_TEXT)
        # Expect at least one chapter, headed by CHAPTER 1 Introduction
        self.assertGreaterEqual(len(chapters), 1)
        self.assertTrue(any("Introduction" in c.title or c.title.startswith("Introduction") for c in chapters))
        # Ensure headers like "64 OCTOBER" are filtered
        for c in chapters:
            self.assertNotIn("OCTOBER", c.title.upper())
        # Ensure '1937' isn't turned into a chapter
        self.assertFalse(any(c.title.strip() == "1937" for c in chapters))

if __name__ == '__main__':
    unittest.main(verbosity=2)
