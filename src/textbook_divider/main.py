from pathlib import Path
from typing import List, Dict, Any
import logging
import json

from .plugin_system import PluginManager
from .file_handler import PDFHandler
from .chapter_detector import ChapterDetector, Chapter
from .text_processor import TextProcessor

logger = logging.getLogger(__name__)

class TextbookDivider:
	"""Main application class for processing and dividing textbooks"""
	
	def __init__(self, language: str = 'eng', plugin_dir: Path = None, max_pages: int = 50):
		self.language = language
		self.plugin_manager = PluginManager(plugin_dir)
		self.chapter_detector = ChapterDetector()
		self.text_processor = TextProcessor()
		
		# Initialize file handlers
		self.file_handlers = {
			'.pdf': PDFHandler(force_ocr=False, max_pages=max_pages)
		}
		
		logger.info(f"Initialized TextbookDivider with plugins: {self.plugin_manager.list_plugins()}")

	
	def process_book(self, input_path: str, output_dir: str, page_range: tuple = None) -> List[str]:
		"""Process a book and save chapters to output directory
		
		Args:
			input_path: Path to the input book file
			output_dir: Directory to save the processed chapters
			page_range: Optional tuple of (start_page, end_page) to process specific pages
			
		Returns:
			List of paths to the generated chapter files
		"""
		input_path = Path(input_path)
		output_dir = Path(output_dir)
		output_dir.mkdir(parents=True, exist_ok=True)
		
		if not input_path.exists():
			raise FileNotFoundError(f"Input file not found: {input_path}")
			
		# Get appropriate file handler
		handler = self.file_handlers.get(input_path.suffix.lower())
		if not handler:
			raise ValueError(f"Unsupported file format: {input_path.suffix}")
			
		# Process content with optional page range
		content = handler.read_content(input_path, page_range=page_range)
		
		# Process with OCR if needed
		if handler.needs_ocr(content):
			ocr_plugin = self.plugin_manager.get_plugin("ocr_processor")
			if ocr_plugin:
				ocr_result = ocr_plugin.process(content)
				if ocr_result["success"]:
					content = ocr_result["text"]
					
		# Check for musical notation
		omr_plugin = self.plugin_manager.get_plugin("omr_processor")
		if omr_plugin:
			omr_result = omr_plugin.process(content)
			if omr_result["success"] and omr_result["has_music"]:
				# Handle musical content
				content = self._process_musical_content(content, omr_result)
		
		# Detect and process chapters
		chapters = self.chapter_detector.detect_chapters(content)
		output_files = []
		
		# Save chapters
		for chapter in chapters:
			chapter_file = output_dir / f"{input_path.stem}_Chapter_{chapter.number:03d}.txt"
			with open(chapter_file, 'w') as f:
				f.write(chapter.content)
			output_files.append(str(chapter_file))
			
		# Save metadata
		metadata = {
			"title": input_path.stem,
			"chapters": len(chapters),
			"plugins_used": self.plugin_manager.list_plugins(),
			"processing_stats": {
				"ocr_used": handler.needs_ocr(content),
				"musical_content_detected": omr_result["has_music"] if omr_plugin else False
			}
		}
		
		metadata_file = output_dir / f"{input_path.stem}_metadata.json"
		with open(metadata_file, 'w') as f:
			json.dump(metadata, f, indent=2)
			
		return output_files
	
	def _process_musical_content(self, content: str, omr_result: Dict[str, Any]) -> str:
		"""Process content with musical notation"""
		# Add musical notation markers
		if omr_result["staff_positions"]:
			# Convert staff positions to markdown-style musical notation blocks
			for staff in omr_result["staff_positions"]:
				content = content.replace(
					f"Staff at position {staff}",
					f"```music\n{staff}\n```"
				)
		return content


def main():
	import argparse
	
	parser = argparse.ArgumentParser(description='Process and divide textbooks into chapters')
	parser.add_argument('input_file', help='Path to the input book file')
	parser.add_argument('output_dir', help='Directory to save the processed chapters')
	parser.add_argument('--plugin-dir', help='Directory containing plugins')
	parser.add_argument('--max-pages', type=int, default=50, help='Maximum number of pages to process')
	parser.add_argument('--page-range', type=str, help='Page range to process (e.g. 1-10)')
	
	args = parser.parse_args()
	
	# Parse page range if provided
	page_range = None
	if args.page_range:
		try:
			start, end = map(int, args.page_range.split('-'))
			page_range = (start, end)
		except ValueError:
			print("Invalid page range format. Use start-end (e.g. 1-10)")
			return 1
	
	divider = TextbookDivider(plugin_dir=args.plugin_dir, max_pages=args.max_pages)
	try:
		output_files = divider.process_book(args.input_file, args.output_dir, page_range=page_range)
		print(f"Successfully processed book into {len(output_files)} chapters")
		for file in output_files:
			print(f"Created file: {file}")
		return 0
	except Exception as e:
		print(f"Error processing book: {e}")
		return 1

if __name__ == '__main__':
	exit(main())
