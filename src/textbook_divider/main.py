from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging
import json

from .plugin_system import PluginManager
from .file_handler import PDFHandler, TXTHandler
from .chapter_detector import ChapterDetector, Chapter
from .text_processor import TextProcessor

logger = logging.getLogger(__name__)

class TextbookDivider:
	"""Main application class for processing and dividing textbooks"""

	def __init__(self, language: str = 'eng', plugin_dir: Optional[Path] = None, max_pages: int = 50,
				 force_ocr: bool = False, ocr_psm: int = 3, raster_scale: float = 2.0, enable_omr: bool = False,
				 min_confidence: float = 0.5, disable_title_line: bool = False,
				 header_months: Optional[str] = None, header_keywords: Optional[str] = None,
				 fast_preprocess: bool = False, parallel_workers: int = 1,
					 reprocess_below_conf: float = 55.0, min_chars_reprocess: int = 200, ocr_word_conf_threshold: int = 30,
					 process_pool: bool = False, auto_tune_thresholds: bool = False, reprocess_logic: str = 'or'):
		self.language = language
		self.plugin_manager = PluginManager(plugin_dir)
		month_list = [m.strip() for m in header_months.split(',')] if header_months else None
		kw_list = [k.strip() for k in header_keywords.split(',')] if header_keywords else None
		self.chapter_detector = ChapterDetector(
			min_confidence=min_confidence,
			enable_title_line=not disable_title_line,
			header_months=month_list,
			header_keywords=kw_list,
		)
		self.text_processor = TextProcessor()
		self.enable_omr = enable_omr
		
		# Initialize file handlers
		self.file_handlers = {
			'.pdf': PDFHandler(
				force_ocr=force_ocr,
				max_pages=max_pages,
				psm=ocr_psm,
				raster_scale=raster_scale,
				fast_preprocess=fast_preprocess,
				parallel_workers=parallel_workers,
				reprocess_below_conf=reprocess_below_conf,
				min_chars_reprocess=min_chars_reprocess,
				ocr_word_conf_threshold=ocr_word_conf_threshold,
				process_pool=process_pool,
				auto_tune_thresholds=auto_tune_thresholds,
				reprocess_logic=reprocess_logic
			),
			'.txt': TXTHandler()
		}
		
		logger.info(f"Initialized TextbookDivider with plugins: {self.plugin_manager.list_plugins()}")

	
	def process_book(self, input_path: str, output_dir: str, page_range: Optional[Tuple[int, int]] = None) -> List[str]:
		"""Process a book and save chapters to output directory
		
		Args:
			input_path: Path to the input book file
			output_dir: Directory to save the processed chapters
			page_range: Optional tuple of (start_page, end_page) to process specific pages
			
		Returns:
			List of paths to the generated chapter files
		"""
		input_path_p = Path(input_path)
		output_dir_p = Path(output_dir)
		output_dir_p.mkdir(parents=True, exist_ok=True)
	
		if not input_path_p.exists():
			raise FileNotFoundError(f"Input file not found: {input_path}")
			
		# Get appropriate file handler
		handler = self.file_handlers.get(input_path_p.suffix.lower())
		if not handler:
			raise ValueError(f"Unsupported file format: {input_path_p.suffix}")
			
		# Process content with optional page range when supported (PDF)
		if input_path_p.suffix.lower() == '.pdf':
			content = handler.read_content(input_path_p, page_range=page_range)
		else:
			content = handler.read_content(input_path_p)
		
		# Process with OCR plugin only if handler supports OCR decision and still needs it,
		# and we haven't already performed OCR inside the handler (to avoid double-OCR).
		if (
			hasattr(handler, 'needs_ocr')
			and handler.needs_ocr(content)
			and not getattr(handler, 'last_used_ocr', False)
		):
			ocr_plugin = self.plugin_manager.get_plugin("ocr_processor")
			if ocr_plugin:
				ocr_result = ocr_plugin.process(content)
				if ocr_result["success"]:
					content = ocr_result["text"]
					
		# Check for musical notation if enabled
		omr_plugin = self.plugin_manager.get_plugin("omr_processor") if self.enable_omr else None
		omr_detected = False
		if omr_plugin and self.enable_omr:
			omr_result = omr_plugin.process(content)
			if omr_result["success"] and omr_result["has_music"]:
				# Handle musical content
				content = self._process_musical_content(content, omr_result)
				omr_detected = True
		
		# Clean content for readability (paragraph stitching, header/footer removal)
		raw_text_length = len(content) if isinstance(content, str) else 0
		try:
			content = self.text_processor.clean_text(content)
		except Exception as e:
			logger.warning(f"Text cleaning skipped due to error: {e}")

		# Detect and process chapters
		chapters = self.chapter_detector.detect_chapters(content)
		output_files = []
		# Track saved paths to avoid duplicates; prefer higher-confidence content
		saved_by_path: Dict[str, Dict[str, Any]] = {}
		
		# Save chapters
		for chapter in chapters:
			# Name subchapters as Chapter_{parent}_{sub} to avoid overwriting
			if getattr(chapter, 'is_subchapter', False) and getattr(chapter, 'parent_chapter', None) is not None:
				parent_num = int(chapter.parent_chapter) if chapter.parent_chapter is not None else 0
				child_num = int(chapter.number) if chapter.number is not None else 0
				chapter_file = output_dir_p / f"{input_path_p.stem}_Chapter_{parent_num:03d}_{child_num:02d}.txt"
			else:
				num = int(chapter.number) if chapter.number is not None else 0
				chapter_file = output_dir_p / f"{input_path_p.stem}_Chapter_{num:03d}.txt"

			path_str = str(chapter_file)
			prev = saved_by_path.get(path_str)
			if prev is None:
				# First time seeing this path; write and record
				with open(chapter_file, 'w') as f:
					f.write(chapter.content)
				saved_by_path[path_str] = {
					'confidence': getattr(chapter, 'confidence', 0.0),
					'number': chapter.number,
					'is_subchapter': getattr(chapter, 'is_subchapter', False),
					'parent_chapter': getattr(chapter, 'parent_chapter', None),
				}
				output_files.append(path_str)
			else:
				# Duplicate filename; prefer higher-confidence chapter content
				new_conf = getattr(chapter, 'confidence', 0.0)
				if new_conf > prev.get('confidence', 0.0):
					with open(chapter_file, 'w') as f:
						f.write(chapter.content)
					# Update stored metadata; do not append duplicate to output_files
					saved_by_path[path_str].update({
						'confidence': new_conf,
						'number': chapter.number,
						'is_subchapter': getattr(chapter, 'is_subchapter', False),
						'parent_chapter': getattr(chapter, 'parent_chapter', None),
					})
				# If not higher confidence, skip writing and do not append duplicate path
			
		# Save metadata (include performance stats when available)
		handler_stats = {}
		if hasattr(handler, 'last_stats'):
			handler_stats = getattr(handler, 'last_stats') or {}
		text_len = len(content) if isinstance(content, str) else 0
		metadata = {
			"title": input_path_p.stem,
			"chapters": len(saved_by_path),
			"plugins_used": self.plugin_manager.list_plugins(),
			"processing_stats": {
				"ocr_used": getattr(handler, 'last_used_ocr', False),
				"musical_content_detected": omr_detected,
				"text_length": text_len,
				"raw_text_length": raw_text_length,
				"file_handler": handler_stats,
			}
		}
		
		metadata_file = output_dir_p / f"{input_path_p.stem}_metadata.json"
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
	parser.add_argument('--force-ocr', action='store_true', help='Force OCR even if text extraction succeeds')
	parser.add_argument('--ocr-psm', type=int, default=3, help='Tesseract page segmentation mode (0-13)')
	parser.add_argument('--raster-scale', type=float, default=2.0, help='Raster scale for PDF rendering (e.g., 2.0 ~= 288 DPI)')
	parser.add_argument('--enable-omr', action='store_true', help='Enable OMR plugin for musical notation detection')
	parser.add_argument('--fast-preprocess', action='store_true', help='Use faster, minimal preprocessing and skip heavy postprocessing for speed')
	parser.add_argument('--parallel-workers', type=int, default=1, help='Number of parallel workers for page OCR (>=1)')
	# Adaptive OCR thresholds
	parser.add_argument('--reprocess-below-conf', type=float, default=55.0, help='Avg page confidence below which to reprocess with full pipeline (0-100)')
	parser.add_argument('--min-chars-reprocess', type=int, default=200, help='If page text shorter than this, reprocess with full pipeline')
	parser.add_argument('--ocr-word-conf-threshold', type=int, default=30, help='Per-word confidence threshold for inclusion (0-100)')
	parser.add_argument('--process-pool', action='store_true', help='Use process-based parallelism for OCR pages')
	parser.add_argument('--auto-tune', action='store_true', help='Auto-tune reprocess thresholds from first pages')
	# Detector tuning
	parser.add_argument('--min-confidence', type=float, default=0.5, help='Minimum confidence threshold for chapter detection')
	parser.add_argument('--disable-title-line', action='store_true', help='Disable heuristic title-line detection')
	parser.add_argument('--header-months', type=str, help='Comma-separated month tokens to treat as running headers (override)')
	parser.add_argument('--header-keywords', type=str, help='Comma-separated keywords to treat as running headers (override)')
	parser.add_argument('--reprocess-logic', type=str, choices=['or','and'], default='or', help='Reprocess when conf/char thresholds are combined by this logic')
	
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
	
	divider = TextbookDivider(plugin_dir=Path(args.plugin_dir) if args.plugin_dir else None,
							 max_pages=args.max_pages,
							 force_ocr=args.force_ocr,
							 ocr_psm=args.ocr_psm,
						  raster_scale=args.raster_scale,
							  enable_omr=args.enable_omr,
							  min_confidence=args.min_confidence,
							  disable_title_line=args.disable_title_line,
							  header_months=args.header_months,
			  header_keywords=args.header_keywords,
			  fast_preprocess=args.fast_preprocess,
			  parallel_workers=max(1, int(args.parallel_workers)),
			  reprocess_below_conf=float(args.reprocess_below_conf),
			  min_chars_reprocess=int(args.min_chars_reprocess),
			  ocr_word_conf_threshold=int(args.ocr_word_conf_threshold),
			  process_pool=bool(args.process_pool),
			  auto_tune_thresholds=bool(args.auto_tune),
			  reprocess_logic=str(args.reprocess_logic))
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
