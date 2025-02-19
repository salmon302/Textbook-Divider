import unittest
from pathlib import Path
import json
from textbook_divider.main import TextbookDivider
from textbook_divider.chapter_detector import Chapter
from textbook_divider.text_processor import TextBlock
from textbook_divider.file_handler import PDFHandler  # Fix import path
from textbook_divider.omr_processor import OMRProcessor
from .test_utils import log_test_case, log_test_data, get_test_logger

logger = get_test_logger(__name__)

class TestImprovements(unittest.TestCase):
	def setUp(self):
		self.test_dir = Path(__file__).parent
		self.sample_dir = self.test_dir / "sample_books"
		self.output_dir = self.test_dir / "output"
		self.divider = TextbookDivider(language='eng')
		
		# Ensure output directory exists
		self.output_dir.mkdir(parents=True, exist_ok=True)
		logger.info(f"Test directories setup - sample_dir: {self.sample_dir}, output_dir: {self.output_dir}")
	
	@log_test_case
	def test_enhanced_chapter_detection(self):
		"""Test improved chapter detection with confidence scoring"""
		test_content = """
		Chapter 1: Introduction
		This is the introduction content.
		
		1.1 Subsection
		This is a subsection.
		
		Chapter 2 - Advanced Topics
		This is the advanced content.
		"""
		log_test_data(test_content, "Test Content")
		
		chapters = self.divider.chapter_detector.detect_chapters(test_content)
		log_test_data([{
			'number': ch.number,
			'title': ch.title,
			'is_subchapter': getattr(ch, 'is_subchapter', False),
			'confidence': getattr(ch, 'confidence', None),
			'parent_chapter': getattr(ch, 'parent_chapter', None)
		} for ch in chapters], "Detected Chapters")
		
		self.assertEqual(len(chapters), 3)
		self.assertTrue(hasattr(chapters[0], 'confidence'))
		self.assertTrue(chapters[1].is_subchapter)
		self.assertEqual(chapters[1].parent_chapter, 1)
	
	@log_test_case
	def test_text_block_processing(self):
		"""Test enhanced text block processing"""
		test_content = """
		• First list item
		• Second list item
		
		Normal paragraph text.
		
		> This is a quote
		> Multiple lines
		
		```python
		def test():
			pass
		```
		"""
		
		log_test_data(test_content, "Test Content")
		
		processor = self.divider.text_processor
		blocks = processor._split_into_blocks(test_content)
		log_test_data([{
			'type': b.block_type,
			'content': b.content[:50] + '...' if len(b.content) > 50 else b.content
		} for b in blocks], "Processed Blocks")
		
		self.assertTrue(any(b.block_type == 'list' for b in blocks))
		self.assertTrue(any(b.block_type == 'quote' for b in blocks))
		self.assertTrue(any(b.block_type == 'paragraph' for b in blocks))
	
	@log_test_case
	def test_metadata_generation(self):
		"""Test metadata generation and storage"""
		test_file = self.sample_dir / "sample.txt"
		output_dir = self.output_dir / "metadata_test"
		logger.info(f"Processing test file: {test_file}")
		
		# Process book
		self.divider.process_book(str(test_file), str(output_dir))
		
		# Check metadata file
		metadata_file = output_dir / "sample_metadata.json"
		self.assertTrue(metadata_file.exists())
		
		with open(metadata_file, 'r') as f:
			metadata = json.load(f)
		log_test_data(metadata, "Chapter Structure Metadata")
		log_test_data(metadata, "Generated Metadata")
		
		self.assertIn('processing_stats', metadata)
		self.assertIn('detected_chapters', metadata['processing_stats'])
		self.assertIn('processing_time', metadata['processing_stats'])
	
	@log_test_case
	def test_error_handling(self):
		"""Test enhanced error handling"""
		with self.assertRaises(ValueError):
			# Test invalid file format
			logger.info("Testing invalid file format")
			self.divider.process_book("nonexistent.xyz", str(self.output_dir))
		
		with self.assertRaises(ValueError):
			# Test empty content
			empty_file = self.output_dir / "empty.txt"
			empty_file.touch()
			self.divider.process_book(str(empty_file), str(self.output_dir))
	
	@log_test_case
	def test_formatting_preservation(self):
		"""Test preservation of text formatting"""
		test_content = """
		Chapter 1: Typography Test
		
		This text has *emphasis* and **strong** formatting.
		
		1. First item
		2. Second item
		
		> Important quote
		> With multiple lines
		"""
		
		processor = self.divider.text_processor
		log_test_data(test_content, "Test Content")
		
		processed = processor.clean_text(test_content)
		log_test_data(processed, "Processed Content")
		
		self.assertIn('*emphasis*', processed)
		self.assertIn('**strong**', processed)
		self.assertIn('> Important quote', processed)

	@log_test_case
	def test_complex_formatting(self):
		"""Test handling of complex formatting features"""
		complex_file = self.sample_dir / "complex_sample.txt"
		output_dir = self.output_dir / "complex_test"
		logger.info(f"Processing complex file: {complex_file}")
		
		# Process book
		output_files = self.divider.process_book(str(complex_file), str(output_dir))
		log_test_data(output_files, "Generated Output Files")
		
		# Verify chapter structure
		self.assertEqual(len(output_files), 2)  # Two main chapters
		
		# Read first chapter content
		with open(output_files[0], 'r') as f:
			chapter1_content = f.read()
		log_test_data(chapter1_content[:200] + '...', "First Chapter Content Preview")
		
		# Read second chapter content
		with open(output_files[1], 'r') as f:
			chapter2_content = f.read()
		log_test_data(chapter2_content[:200] + '...', "Second Chapter Content Preview")
		
		# Check formatting preservation in Chapter 1
		self.assertIn('*emphasized*', chapter1_content)
		self.assertIn('**bold**', chapter1_content)
		self.assertIn('```python', chapter1_content)
		self.assertIn('> Important quote block', chapter1_content)
		
		# Check formatting preservation in Chapter 2
		self.assertIn('| Header 1 |', chapter2_content)
		
	@log_test_case
	def test_nested_chapter_structure(self):
		"""Test detection and handling of nested chapter structure"""
		complex_file = self.sample_dir / "complex_sample.txt"
		output_dir = self.output_dir / "nested_test"
		logger.info(f"Processing file for nested structure: {complex_file}")
		
		# Process book
		self.divider.process_book(str(complex_file), str(output_dir))
		
		# Check metadata
		metadata_file = output_dir / "complex_sample_metadata.json"
		with open(metadata_file, 'r') as f:
			metadata = json.load(f)
		
		# Verify chapter detection includes subchapters
		self.assertGreaterEqual(metadata['processing_stats']['detected_chapters'], 4)  # 2 main + 2 sub per chapter

	@log_test_case
	def test_pdf_processing(self):
		"""Test processing of PDF files"""
		test_file = Path("/home/seth-n/CLionProjects/Textbook Divider/data/input/Arnold Schoenberg, Gerald Strang, Leonard Stein - Fundamentals of Musical Composition (1982, Faber & Faber) - libgen.li.pdf")
		output_dir = self.output_dir / "schoenberg_test"
		logger.info(f"Processing PDF file: {test_file}")
		
		# Initialize handlers with forced OCR and more pages
		pdf_handler = PDFHandler(force_ocr=True, max_pages=10)  # Process first 10 pages
		self.divider.file_handlers['.pdf'] = pdf_handler
		
		# Process book
		try:
			output_files = self.divider.process_book(str(test_file), str(output_dir))
			log_test_data(output_files, "Generated Output Files")
		except Exception as e:
			# Log the extracted content for debugging
			content = pdf_handler.read_content(test_file)
			log_test_data(content[:1000], "Extracted Content Preview")
			raise
		
		# Verify output directory exists
		self.assertTrue(output_dir.exists())
		
		# Check metadata file
		metadata_file = output_dir / f"{test_file.stem}_metadata.json"
		self.assertTrue(metadata_file.exists())
		
		with open(metadata_file, 'r') as f:
			metadata = json.load(f)
		log_test_data(metadata, "PDF Processing Metadata")
		
		# Verify basic metadata structure
		self.assertIn('processing_stats', metadata)
		self.assertIn('detected_chapters', metadata['processing_stats'])
		self.assertIn('processing_time', metadata['processing_stats'])
		
		# Check content of first chapter if available
		if output_files:
			with open(output_files[0], 'r') as f:
				first_chapter = f.read()
				log_test_data(first_chapter[:500], "First Chapter Preview")
				
			# Verify chapter contains meaningful content
			self.assertGreater(len(first_chapter), 100)  # Should have substantial content

	@log_test_case
	def test_omr_integration(self):
		"""Test OMR integration with chapter detection"""
		test_file = self.sample_dir / "complex_score.pdf"
		output_dir = self.output_dir / "omr_test"
		logger.info(f"Processing file with OMR: {test_file}")
		
		# Initialize OMR processor
		self.divider.omr_processor = OMRProcessor()
		
		# Process book
		output_files = self.divider.process_book(str(test_file), str(output_dir))
		
		# Check metadata
		metadata_file = output_dir / f"{test_file.stem}_metadata.json"
		with open(metadata_file, 'r') as f:
			metadata = json.load(f)
		log_test_data(metadata, "OMR Processing Metadata")
		
		# Verify OMR processing stats
		self.assertIn('omr_stats', metadata.get('processing_stats', {}))
		omr_stats = metadata['processing_stats']['omr_stats']
		self.assertGreaterEqual(omr_stats.get('staff_detection_rate', 0), 0.95)
		self.assertGreaterEqual(omr_stats.get('note_recognition_rate', 0), 0.90)

	@log_test_case
	def test_mixed_content_handling(self):
		"""Test handling of mixed text and musical content"""
		test_file = self.sample_dir / "mixed_layout.pdf"
		output_dir = self.output_dir / "mixed_content_test"
		logger.info(f"Processing mixed content file: {test_file}")
		
		# Process book
		output_files = self.divider.process_book(str(test_file), str(output_dir))
		
		# Check first chapter content
		with open(output_files[0], 'r') as f:
			content = f.read()
			log_test_data(content[:500], "Mixed Content Preview")
		
		# Verify musical notation markers
		self.assertIn('```music', content)
		self.assertIn('```', content)
		
		# Check metadata
		metadata_file = output_dir / f"{test_file.stem}_metadata.json"
		with open(metadata_file, 'r') as f:
			metadata = json.load(f)
		
		# Verify mixed content stats
		stats = metadata['processing_stats']
		self.assertIn('musical_sections', stats)
		self.assertIn('text_sections', stats)
		self.assertGreater(stats['musical_sections'], 0)
		self.assertGreater(stats['text_sections'], 0)

	@log_test_case
	def test_omr_error_recovery(self):
		"""Test OMR error recovery and fallback mechanisms"""
		test_file = self.sample_dir / "corrupted_score.pdf"
		output_dir = self.output_dir / "omr_error_test"
		logger.info(f"Testing OMR error recovery: {test_file}")
		
		# Process book
		output_files = self.divider.process_book(str(test_file), str(output_dir))
		
		# Check metadata for error recovery info
		metadata_file = output_dir / f"{test_file.stem}_metadata.json"
		with open(metadata_file, 'r') as f:
			metadata = json.load(f)
		log_test_data(metadata, "Error Recovery Metadata")
		
		# Verify error recovery
		stats = metadata['processing_stats']
		self.assertIn('omr_recovery_attempts', stats)
		self.assertGreater(stats['omr_recovery_attempts'], 0)
		self.assertTrue(stats.get('recovery_successful', False))


if __name__ == '__main__':
	unittest.main()