from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Iterator, Optional, Tuple, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import tempfile
import re
import cv2
import numpy as np
from PIL import Image
from pdf2image import convert_from_path
from .ocr_processor import OCRProcessor

class FileHandler(ABC):
	"""Base class for handling different file formats"""
	
	@abstractmethod
	def validate_file(self, file_path: Path) -> bool:
		"""Validate if the file is in the correct format"""
		pass
	
	@abstractmethod
	def read_content(self, file_path: Path) -> str:
		"""Read and return the content of the file"""
		pass

class TXTHandler(FileHandler):
	"""Handler for plain text files"""
	
	def validate_file(self, file_path: Path) -> bool:
		return file_path.suffix.lower() == '.txt'
	
	def read_content(self, file_path: Path) -> str:
		with open(file_path, 'r', encoding='utf-8') as file:
			return file.read()




class PDFHandler(FileHandler):
	def __init__(self, force_ocr: bool = False, max_pages: int = 50, psm: int = 3, raster_scale: float = 2.0, fast_preprocess: bool = False, parallel_workers: int = 1,
				 reprocess_below_conf: float = 55.0, min_chars_reprocess: int = 200, ocr_word_conf_threshold: int = 30,
				 process_pool: bool = False, auto_tune_thresholds: bool = False, reprocess_logic: str = 'or'):
		self.force_ocr = force_ocr
		self.max_pages = max_pages
		self.raster_scale = raster_scale if raster_scale > 0 else 2.0
		self.fast_preprocess = bool(fast_preprocess)
		self.parallel_workers = int(parallel_workers) if int(parallel_workers) > 0 else 1
		# Initialize OCR with configurable per-word confidence threshold
		self.ocr = OCRProcessor(psm=psm, conf_threshold=int(ocr_word_conf_threshold))
		# Adaptive reprocess thresholds
		self.reprocess_below_conf = float(reprocess_below_conf)
		self.min_chars_reprocess = int(min_chars_reprocess)
		self.process_pool = bool(process_pool)
		self.auto_tune_thresholds = bool(auto_tune_thresholds)
		self.reprocess_logic = reprocess_logic if reprocess_logic in ('or','and') else 'or'
		# Accurate tracking of whether OCR path was used
		self.last_used_ocr: bool = False
		# Timing and performance stats for last run
		self.last_stats = {
			"used_ocr": False,
			"psm": psm,
			"raster_scale": self.raster_scale,
			"fast_preprocess": self.fast_preprocess,
			"parallel_workers": self.parallel_workers,
			"process_pool": self.process_pool,
			"reprocess_logic": self.reprocess_logic,
			"auto_tuned": False,
			"tuned_conf": None,
			"tuned_min_chars": None,
			"pages": 0,
			"per_page_secs": [],
			"total_ocr_sec": 0.0,
			"extraction_sec": 0.0,
			"rasterizer": "",
		}
	
	def validate_file(self, file_path: Path) -> bool:
		return file_path.suffix.lower() == '.pdf'
	
	def read_content(self, file_path: Path, page_range: Optional[Tuple[int, int]] = None, max_pages: Optional[int] = None) -> str:
		"""Read content from PDF with optional page range"""
		pages_to_process = max_pages if max_pages is not None else self.max_pages
		self.last_used_ocr = False
		
		if page_range:
			start_page, end_page = page_range
			pages_to_process = min(end_page - start_page + 1, pages_to_process)
		
		if self.force_ocr:
			return self._process_with_ocr(file_path, pages_to_process, page_range)
		
		try:
			import fitz
			doc = fitz.open(file_path)
			text_parts = []
			start_time = time.time()
			
			start_idx = (page_range[0] - 1) if page_range else 0
			end_idx = min(page_range[1] if page_range else doc.page_count, 
						 start_idx + pages_to_process)
			
			print(f"Processing pages {start_idx + 1} to {end_idx} from {file_path.name}")
			
			for page_num in range(start_idx, end_idx):
				page = doc[page_num]
				# Try different rotations if text extraction fails
				rotations = [0, 90, 180, 270]
				text = ""
				for rotation in rotations:
					if rotation != 0:
						page.set_rotation(rotation)
					text = page.get_text()
					if text.strip():
						break
				
				if text.strip():
					text_parts.append(text)
					print(f"Processed page {page_num + 1}")
				else:
					print(f"Page {page_num + 1} is empty or failed to extract")
			
			doc.close()
			combined_text = '\n\n'.join(text_parts)
			print(f"Total extracted text length: {len(combined_text)}")
			# Record extraction timing when not using OCR
			self.last_stats = {
				"used_ocr": False,
				"psm": self.ocr.psm,
				"raster_scale": self.raster_scale,
				"fast_preprocess": self.fast_preprocess,
				"parallel_workers": self.parallel_workers,
				"pages": end_idx - start_idx,
				"per_page_secs": [],
				"total_ocr_sec": 0.0,
				"extraction_sec": time.time() - start_time,
				"rasterizer": "pymupdf_text",
			}
			
			# Use needs_ocr to determine if OCR is needed
			if self.needs_ocr(combined_text):
				print("Text extraction insufficient, falling back to OCR")
				return self._process_with_ocr(file_path, pages_to_process)
			
			# If we reach here, we didn't need OCR
			self.last_used_ocr = False
			return combined_text
			
		except ImportError:
			print("PyMuPDF not found, falling back to pdf2image + OCR")
			return self._process_with_ocr(file_path, pages_to_process)

	def needs_ocr(self, content: str) -> bool:
		"""Check if OCR is needed based on content extraction success"""
		# If force_ocr is True, always use OCR
		if self.force_ocr:
			return True
		# If no text was extracted or text is too short, use OCR
		return not content or len(content.strip()) < 100
	
	def _process_with_ocr(self, file_path: Path, pages_to_process: int, page_range: Optional[Tuple[int, int]] = None) -> str:
		"""OCR processing that prefers PyMuPDF rasterization, falling back to pdf2image.
		This avoids requiring Poppler on Windows when PyMuPDF is available."""
		first_page = page_range[0] if page_range else 1
		last_page = min(
			first_page + pages_to_process - 1,
			page_range[1] if page_range else first_page + pages_to_process - 1
		)
		self.last_used_ocr = True
		ocr_start = time.time()
		per_page_times: List[float] = []
		pages_count = 0
		rasterizer_used = ""
		result_text = ""
		auto_tuned_flag = False
		tuned_conf_val = None
		tuned_chars_val = None

		# Attempt PyMuPDF rasterization
		# Helper to OCR a single PIL image with timing
		def _ocr_page_image(idx: int, pil_img: Image.Image) -> Tuple[int, str, float, bool]:
			t0 = time.time()
			text_out = ""
			reprocessed = False
			try:
				# Pass 1: fast recognize (collect avg confidence and char count)
				img_local = pil_img.convert('L') if pil_img.mode != 'L' else pil_img
				text_fast, avg_conf_fast, chars_fast = self.ocr.recognize(img_local, mode='fast')
				text_out = text_fast
				# Decide if reprocess with full pipeline
				reprocess_cond = (
					(avg_conf_fast < self.reprocess_below_conf) and (chars_fast < self.min_chars_reprocess)
					if self.reprocess_logic == 'and'
					else (avg_conf_fast < self.reprocess_below_conf) or (chars_fast < self.min_chars_reprocess)
				)
				if reprocess_cond:
					# Pass 2: full enhancement and recognition via OCRProcessor
					text_full, avg_conf_full, chars_full = self.ocr.recognize(pil_img, mode='full')
					# Confidence-aware merge (prefer full if clearly better in conf or much longer)
					if (avg_conf_full >= avg_conf_fast + 3.0) or (len(text_full) > int(1.1 * len(text_fast))):
						text_out = text_full
					reprocessed = True
			except Exception:
				text_out = ""
				reprocessed = False
			return (idx, text_out, time.time() - t0, reprocessed)

		# Process-pool worker wrapper (module-level function defined below)

		try:
			import fitz
			doc = fitz.open(str(file_path))
			# Prepare images
			images_to_ocr: List[Tuple[int, Image.Image]] = []
			for pno in range(first_page - 1, min(last_page, doc.page_count)):
				page = doc[pno]
				mat = fitz.Matrix(self.raster_scale, self.raster_scale)
				pix = page.get_pixmap(matrix=mat, alpha=False)
				img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
				images_to_ocr.append((pno + 1, img))
				print(f"Queued page {pno + 1} for OCR (PyMuPDF raster)")

			# Optional auto-tune thresholds using first few pages (fast only)
			if self.auto_tune_thresholds and images_to_ocr:
				sample_n = min(4, len(images_to_ocr))
				confs: List[float] = []
				lens: List[int] = []
				for idx, img in images_to_ocr[:sample_n]:
					try:
						_t, conf_s, len_s = self.ocr.recognize(img, mode='fast')
						if conf_s >= 0:
							confs.append(conf_s)
						lens.append(len_s)
					except Exception:
						continue
				if confs and lens:
					avg_conf = sum(confs) / len(confs)
					# 20th percentile for chars (doc-shape heuristic)
					lens_sorted = sorted(lens)
					p20_idx = max(0, int(0.2 * len(lens_sorted)) - 1)
					p20_chars = lens_sorted[p20_idx]
					# Less conservative: allow higher conf before reprocess and lower char floor
					self.reprocess_below_conf = max(40.0, min(65.0, avg_conf - 10.0))
					self.min_chars_reprocess = max(80, min(400, p20_chars))
					auto_tuned_flag = True
					tuned_conf_val = self.reprocess_below_conf
					tuned_chars_val = self.min_chars_reprocess

			# Process in parallel if configured
			results: List[Tuple[int, str, float, bool]] = []
			if self.parallel_workers > 1 and self.process_pool:
				# Use process-based parallelism: write images to temp files
				import os
				from concurrent.futures import ProcessPoolExecutor
				tmp_dir = Path(tempfile.gettempdir()) / "td_ocr_pages"
				tmp_dir.mkdir(parents=True, exist_ok=True)
				tmp_paths: List[Tuple[int, Path]] = []
				for idx, img in images_to_ocr:
					p = tmp_dir / f"{Path(file_path).stem}_p{idx}.png"
					img.save(p, format='PNG')
					tmp_paths.append((idx, p))
				with ProcessPoolExecutor(max_workers=self.parallel_workers) as ex:
					futs = [ex.submit(_ocr_page_worker, idx, str(p), self.ocr.psm, int(self.ocr.conf_threshold), float(self.reprocess_below_conf), int(self.min_chars_reprocess), self.reprocess_logic) for idx, p in tmp_paths]
					for f in as_completed(futs):
						results.append(f.result())
				# cleanup temp files
				for _, p in tmp_paths:
					try:
						os.remove(p)
					except Exception:
						pass
			elif self.parallel_workers > 1:
				with ThreadPoolExecutor(max_workers=self.parallel_workers) as ex:
					futs = [ex.submit(_ocr_page_image, idx, img) for idx, img in images_to_ocr]
					for f in as_completed(futs):
						results.append(f.result())
			else:
				for idx, img in images_to_ocr:
					results.append(_ocr_page_image(idx, img))

			# Aggregate
			results.sort(key=lambda t: t[0])
			text_parts: List[str] = []
			reproc_count = 0
			for idx, txt, dt, did_reprocess in results:
				per_page_times.append(dt)
				pages_count += 1
				if did_reprocess:
					reproc_count += 1
				if txt:
					text_parts.append(txt)
			doc.close()
			if text_parts:
				rasterizer_used = "pymupdf_raster"
				result_text = "\n\n".join(text_parts)
				reproc_total_count = reproc_count
		except Exception as e:
			print(f"PyMuPDF rasterization failed or unavailable: {e}")

		# Fallback to pdf2image if needed
		if not result_text:
			try:
				import os
				poppler_path = os.environ.get('POPPLER_PATH') or os.environ.get('POPDIR')
				if poppler_path and os.path.exists(poppler_path):
					images = convert_from_path(
						str(file_path),
						first_page=first_page,
						last_page=last_page,
						dpi=int(144 * self.raster_scale),
						grayscale=True,
						thread_count=2,
						timeout=120,
						poppler_path=poppler_path
					)
				else:
					images = convert_from_path(
						str(file_path),
						first_page=first_page,
						last_page=last_page,
						dpi=int(144 * self.raster_scale),
						grayscale=True,
						thread_count=2,
						timeout=120
					)
				# Process pdf2image results in parallel
				results2: List[Tuple[int, str, float, bool]] = []
				if self.parallel_workers > 1:
					with ThreadPoolExecutor(max_workers=self.parallel_workers) as ex:
						futs = [ex.submit(_ocr_page_image, idx, img) for idx, img in enumerate(images, start=first_page)]
						for f in as_completed(futs):
							results2.append(f.result())
				else:
					for idx, img in enumerate(images, start=first_page):
						results2.append(_ocr_page_image(idx, img))

				results2.sort(key=lambda t: t[0])
				text_parts: List[str] = []
				reproc_count2 = 0
				for idx, txt, dt, did_reprocess in results2:
					per_page_times.append(dt)
					pages_count += 1
					if did_reprocess:
						reproc_count2 += 1
					if txt:
						text_parts.append(txt)
				rasterizer_used = "pdf2image"
				result_text = "\n\n".join(text_parts)
				reproc_total_count = reproc_count2
			except Exception as e:
				print(f"Error during PDF processing fallback: {e}")

		# Finalize stats and return result
		total_ocr_sec = time.time() - ocr_start
		self.last_stats = {
			"used_ocr": True,
			"psm": self.ocr.psm,
			"raster_scale": self.raster_scale,
			"fast_preprocess": self.fast_preprocess,
			"parallel_workers": self.parallel_workers,
			"process_pool": self.process_pool,
			"reprocess_logic": self.reprocess_logic,
			"pages": pages_count,
			"per_page_secs": per_page_times,
			"total_ocr_sec": total_ocr_sec,
			"extraction_sec": 0.0,
			"rasterizer": rasterizer_used,
			"reprocessed_pages": int(locals().get('reproc_total_count', 0)),
			"reprocess_threshold_conf": self.reprocess_below_conf,
			"reprocess_threshold_chars": self.min_chars_reprocess,
			"auto_tuned": auto_tuned_flag,
			"tuned_conf": tuned_conf_val,
			"tuned_min_chars": tuned_chars_val,
		}
		return result_text

	def _process_single_page(self, file_path: Path, page_num: int) -> str:
		"""Process a single page from a PDF file with OCR"""
		try:
			images = convert_from_path(
				file_path,
				first_page=page_num,
				last_page=page_num,
				dpi=400,  # Increased DPI for better quality
				grayscale=True,
				thread_count=2,
				use_pdftocairo=True
			)
			
			if not images:
				print(f"No image generated for page {page_num}")
				return ""
			
			image = images[0]
			print(f"Processing page {page_num} with OCR")
			enhanced = self._enhance_image(image)
			text = self.ocr.process_image(enhanced)
			
			if text and text.strip():
				return self._post_process_text(text)
			else:
				print(f"No text extracted from page {page_num}")
				return ""
				
		except Exception as e:
			print(f"Error processing page {page_num}: {e}")
			return ""

	def _enhance_image(self, image):
		"""Enhance image for better OCR results"""
		img_array = np.array(image)
		
		# Convert to grayscale if needed
		if len(img_array.shape) == 3:
			gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
		else:
			gray = img_array
		
		# Apply bilateral filter for noise reduction while preserving edges
		denoised = cv2.bilateralFilter(gray, 9, 75, 75)
		
		# Apply CLAHE for contrast enhancement
		clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
		enhanced = clahe.apply(denoised)
		
		# Apply Otsu's thresholding
		_, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
		
		# Avoid dilation which can merge inter-word gaps; instead use a gentle opening to reduce noise
		kernel = np.ones((2,2), np.uint8)
		opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
		
		return Image.fromarray(opened)

	def _post_process_text(self, text: str) -> str:
		"""Post-process OCR text: preserve notations, filter headers, stitch paragraphs"""
		# Preserve mathematical symbols by padding with spaces
		text = re.sub(r'([∫∑∏√∆∇∈∉∋∌∩∪⊂⊃⊆⊇≈≠≡≤≥])', r' \1 ', text)

		# Preserve musical terms by padding with spaces
		musical_terms = ['tempo', 'allegro', 'andante', 'forte', 'piano',
					 'chord', 'scale', 'note', 'rhythm', 'melody']
		for term in musical_terms:
			text = re.sub(rf'\b{term}\b', lambda m: f' {m.group(0)} ', text,
						 flags=re.IGNORECASE)

		# Split into lines for filtering
		lines = [ln for ln in re.split(r'[\r\n]+', text) if ln is not None]

		# Identify repeated uppercase lines that likely are running headers/footers
		from collections import Counter
		def canon(s: str) -> str:
			return re.sub(r'\s+', ' ', s.strip().upper())
		cand = [canon(ln) for ln in lines if 3 <= len(ln.strip()) <= 40 and ln.strip().isupper()]
		counts = Counter(cand)
		repeated_headers = {h for h, c in counts.items() if c >= 3}

		months = {"JANUARY","FEBRUARY","MARCH","APRIL","MAY","JUNE","JULY","AUGUST","SEPTEMBER","OCTOBER","NOVEMBER","DECEMBER"}
		header_keywords = {"OCTOBER","OCT","VOLUME","VOL","NO","NUMBER","ISSUE","CONTENTS","INDEX"}

		filtered: List[str] = []
		for ln in lines:
			l = ln.strip()
			if not l:
				continue
			U = l.upper()
			# Drop if repeated uppercase header/footer line
			if canon(l) in repeated_headers:
				continue
			# Patterns like "52 OCTOBER" or "OCTOBER 52"
			if re.match(r'^\d{1,4}\s+[A-Z]{3,}$', U) or re.match(r'^[A-Z]{3,}\s+\d{1,4}$', U):
				tok = re.sub(r'\d+', '', U).strip()
				if tok in months or tok in header_keywords:
					continue
			# Standalone page number
			if re.fullmatch(r'\d{1,4}', l):
				continue
			# Short TitleCase phrase followed or preceded by page number (e.g., "Sacrifice 65" or "65 Sacrifice")
			if re.match(r'^(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,5})\s+\d{1,4}$', l):
				continue
			if re.match(r'^\d{1,4}\s+(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,5})$', l):
				continue
			filtered.append(l)

		# Paragraph stitching: merge line-wrapped sentences while preserving blank paragraph breaks
		def stitch_paragraphs(txt: str) -> str:
			out_paras: List[str] = []
			buf: List[str] = []
			for raw in txt.split('\n'):
				line = raw.strip()
				# blank line -> paragraph boundary
				if line == '':
					if buf:
						out_paras.append(' '.join(buf).strip())
						buf = []
					# preserve a single blank separator
					if not out_paras or out_paras[-1] != '':
						out_paras.append('')
					continue
				if not buf:
					buf.append(line)
					continue
				prev = buf[-1]
				# Hyphenated break: join without space when next line starts lowercase
				if prev.endswith('-') and (line and line[0].islower()):
					buf[-1] = prev[:-1] + line
					continue
				# If previous does not end in sentence punctuation, join with space
				if not re.search(r'[\.!?\:\;]\"?$', prev) and (line and (line[0].islower() or len(prev) < 80)):
					buf[-1] = prev + ' ' + line
				else:
					buf.append(line)
			# flush any remaining buffer
			if buf:
				out_paras.append(' '.join(buf).strip())
			# collapse multiple blank separators to single
			collapsed: List[str] = []
			for p in out_paras:
				if p == '':
					if not collapsed or collapsed[-1] != '':
						collapsed.append('')
				else:
					collapsed.append(p)
			return '\n\n'.join([p for p in collapsed])

		joined = '\n'.join(filtered)
		# Gentle whitespace normalization before stitching
		joined = re.sub(r'[\t]+', ' ', joined)
		joined = re.sub(r'\u00AD', '', joined)  # soft hyphen removal
		joined = stitch_paragraphs(joined)
		# Normalize excessive blank lines
		joined = re.sub(r'\n{3,}', '\n\n', joined)
		return joined.strip()






class EPUBHandler(FileHandler):
	"""Handler for EPUB files"""
	
	def validate_file(self, file_path: Path) -> bool:
		if not file_path.suffix.lower() == '.epub':
			return False
		try:
			import ebooklib
			from ebooklib import epub
			book = epub.read_epub(str(file_path))
			return True
		except Exception:
			return False
	
	def read_content(self, file_path: Path) -> str:
		import ebooklib
		from ebooklib import epub
		import html2text
		
		book = epub.read_epub(str(file_path))
		h = html2text.HTML2Text()
		h.ignore_links = True
		
		text_content = []
		for item in book.get_items():
			if item.get_type() == ebooklib.ITEM_DOCUMENT:
				html_content = item.get_content().decode('utf-8')
				text_content.append(h.handle(html_content))
		
		return '\n\n'.join(text_content)

class ImageHandler(FileHandler):
	"""Handler for image files"""
	
	SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp'}
	
	def __init__(self, lang: str = 'eng'):
		self.ocr = OCRProcessor(lang=lang)
	
	def validate_file(self, file_path: Path) -> bool:
		return file_path.suffix.lower() in self.SUPPORTED_FORMATS
	
	def read_content(self, file_path: Path) -> str:
		return self.ocr.process_image(str(file_path))


# Module-level process worker for OCR (for ProcessPoolExecutor)
def _ocr_page_worker(idx: int, img_path: str, psm: int, conf_threshold: int, reprocess_below_conf: float, min_chars_reprocess: int, reprocess_logic: str = 'or') -> Tuple[int, str, float, bool]:
	"""Worker executed in a separate process. Loads image, runs fast OCR, optionally reprocesses with full pipeline.

	Returns: (page_index, text, elapsed_seconds, reprocessed)
	"""
	import time as _t
	from PIL import Image as _Image
	start = _t.time()
	reprocessed = False
	try:
		ocr = OCRProcessor(psm=int(psm), conf_threshold=int(conf_threshold))
		img = _Image.open(img_path)
		if img.mode != 'L' and img.mode != 'RGB':
			img = img.convert('RGB')
		text_fast, conf_fast, chars_fast = ocr.recognize(img, mode='fast')
		text_out = text_fast
		cond_and = (reprocess_logic == 'and' and (conf_fast < float(reprocess_below_conf)) and (chars_fast < int(min_chars_reprocess)))
		cond_or = (reprocess_logic != 'and' and ((conf_fast < float(reprocess_below_conf)) or (chars_fast < int(min_chars_reprocess))))
		if cond_and or cond_or:
			text_full, conf_full, chars_full = ocr.recognize(img, mode='full')
			if (conf_full >= conf_fast + 3.0) or (len(text_full) > int(1.1 * len(text_fast))):
				text_out = text_full
			reprocessed = True
		img.close()
	except Exception:
		text_out = ""
		reprocessed = False
	return (idx, text_out, _t.time() - start, reprocessed)