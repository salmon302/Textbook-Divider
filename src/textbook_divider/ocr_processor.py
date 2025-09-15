import re
import os
import gc
import json
import time
import psutil
import logging
import hashlib
import multiprocessing
import tempfile
from pathlib import Path
from typing import Union, List, Dict, Optional, Any, Tuple

import cv2
import numpy as np
import PyPDF2
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont
from pdf2image import convert_from_path
from pdfminer.high_level import extract_text

from .parallel_processor import ParallelProcessor


class OCRProcessor:
	# Feature patterns for text analysis
	feature_patterns = {
		'math': [
			r'[∫∑∏√∆∇]',
			r'\$.*?\$',
			r'[=<>+\-*/^()]',
			r'\b\d+(?:\.\d+)?\b'
		],
		'music': [
			r'[♩♪♫♬𝄞𝄢]',
			r'\b(?:sharp|flat|natural)\b',
			r'\b(?:major|minor|chord)\b'
		]
	}
	SUPPORTED_LANGUAGES = {
		'eng': 'English',
		'fra': 'French',
		'deu': 'German',
		'spa': 'Spanish',
		'ita': 'Italian'
	}
	
	def __init__(self, lang: str = 'eng', enable_gpu: bool = False, cache_size: int = 1000, psm: int = 3, conf_threshold: int = 30):
		if lang not in self.SUPPORTED_LANGUAGES:
			raise ValueError(f"Unsupported language: {lang}")
		self.lang = lang
		self.enable_gpu = enable_gpu
		self.logger = logging.getLogger(__name__)
		# Configure tesseract path in a cross-platform way
		# Priority: env TESSERACT_CMD > default PATH > common Windows installs
		try:
			tcmd = os.environ.get('TESSERACT_CMD') or os.environ.get('TESSERACT_PATH')
			if tcmd and os.path.exists(tcmd):
				pytesseract.pytesseract.tesseract_cmd = tcmd
			else:
				# Check common Windows install locations if on Windows
				if os.name == 'nt':
					common_paths = [
						r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
						r"C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe"
					]
					for p in common_paths:
						if os.path.exists(p):
							pytesseract.pytesseract.tesseract_cmd = p
							break
				# Else rely on PATH; don't set hard-coded Linux path
		except Exception:
			# Fall back to default behavior; pytesseract will use PATH
			pass
		self.psm = psm if isinstance(psm, int) and 0 <= psm <= 13 else 3
		self.conf_threshold = int(conf_threshold) if isinstance(conf_threshold, int) else 30
		self.fast_preprocess = False
		self.config = self._build_tesseract_config()
		self.preprocessing_params = {
			'dpi': 400,
			'contrast_limit': 2.5,  # Reduced for better memory usage
			'denoise_strength': 7,  # Increased for better noise removal
			'sharpness': 1.5,  # Reduced to prevent artifacts
			'batch_size': 4,
			'max_image_mp': 25,  # Max megapixels before downscaling
			'chunk_size': (1024, 1024),  # Process large images in chunks
			'max_batch_memory': 1024,  # Max MB for batch processing
			'min_chunk_size': (512, 512)  # Min chunk size for processing
		}
		self.parallel_processor = ParallelProcessor(
			max_workers=min(multiprocessing.cpu_count(), 4),
			memory_limit_mb=500
		)
		self._cache = {}
		self._cache_size = cache_size
		self._cache_hits = 0
		self._cache_misses = 0
		# Use cross-platform temp directory for cache
		self._cache_dir = Path(tempfile.gettempdir()) / 'textbook_divider_cache'
		self._cache_dir.mkdir(parents=True, exist_ok=True)
		self._load_cache()
		self.stats = {'processed': 0, 'failed': 0}
		self._memory_monitor = {
			'peak': 0,
			'current': 0,
			'warnings': 0
		}

	# --- Configuration application helpers ---
	def apply_config(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
		"""Apply config values dynamically. Returns applied subset."""
		applied: Dict[str, Any] = {}
		try:
			if 'ocr_psm' in cfg and isinstance(cfg['ocr_psm'], int):
				self.psm = max(0, min(13, int(cfg['ocr_psm'])))
				applied['ocr_psm'] = self.psm
			if 'ocr_word_conf_threshold' in cfg and isinstance(cfg['ocr_word_conf_threshold'], (int, float)):
				self.conf_threshold = int(cfg['ocr_word_conf_threshold'])
				applied['ocr_word_conf_threshold'] = self.conf_threshold
			if 'fast_preprocess' in cfg and isinstance(cfg['fast_preprocess'], bool):
				self.fast_preprocess = bool(cfg['fast_preprocess'])
				applied['fast_preprocess'] = self.fast_preprocess
			if 'parallel_workers' in cfg and isinstance(cfg['parallel_workers'], int):
				workers = max(1, min(multiprocessing.cpu_count(), int(cfg['parallel_workers'])))
				self.parallel_processor = ParallelProcessor(max_workers=workers, memory_limit_mb=self.parallel_processor.memory_limit_mb if hasattr(self.parallel_processor,'memory_limit_mb') else 500)
				applied['parallel_workers'] = workers
			if 'process_pool' in cfg and isinstance(cfg['process_pool'], bool):
				# not directly used by ParallelProcessor; store for reference
				self.process_pool = bool(cfg['process_pool'])
				applied['process_pool'] = self.process_pool
			if 'raster_scale' in cfg:
				# stored for potential upstream PDF rasterization usage
				try:
					self.raster_scale = float(cfg['raster_scale'])
					applied['raster_scale'] = self.raster_scale
				except Exception:
					pass
			if 'reprocess_below_conf' in cfg:
				try:
					self.reprocess_below_conf = float(cfg['reprocess_below_conf'])
					applied['reprocess_below_conf'] = self.reprocess_below_conf
				except Exception:
					pass
			if 'min_chars_reprocess' in cfg:
				try:
					self.min_chars_reprocess = int(cfg['min_chars_reprocess'])
					applied['min_chars_reprocess'] = self.min_chars_reprocess
				except Exception:
					pass
			if 'reprocess_logic' in cfg and isinstance(cfg['reprocess_logic'], str):
				self.reprocess_logic = cfg['reprocess_logic']
				applied['reprocess_logic'] = self.reprocess_logic
			if 'auto_tune' in cfg and isinstance(cfg['auto_tune'], bool):
				self.auto_tune = bool(cfg['auto_tune'])
				applied['auto_tune'] = self.auto_tune
			if 'enable_omr' in cfg and isinstance(cfg['enable_omr'], bool):
				self.enable_omr = bool(cfg['enable_omr'])
				applied['enable_omr'] = self.enable_omr
			# Rebuild tesseract config if needed
			self.config = self._build_tesseract_config()
		except Exception as e:
			self.logger.warning(f"apply_config encountered an error: {e}")
		return applied

	def apply_config_file(self, path: Union[str, Path]) -> Dict[str, Any]:
		try:
			with open(path, 'r', encoding='utf-8') as f:
				cfg = json.load(f)
			return self.apply_config(cfg)
		except Exception as e:
			self.logger.error(f"Failed to apply config file {path}: {e}")
			return {}


	def _build_tesseract_config(self) -> str:
		config = [
			'--oem 1',  # LSTM only
			f'--psm {self.psm}',  # Page segmentation mode
			'-c lstm_choice_mode=2',
			'-c lstm_rating_coefficient=2.5',
			'-c textord_heavy_nr=1',
			'-c tessedit_pageseg_mode=1',
			'-c tessedit_do_invert=0',
			'-c textord_noise_rejwords=1',
			'-c textord_noise_rejrows=1',
			'-c textord_noise_debug_level=0',
			'-c tessedit_unrej_any_wd=0',
			'-c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,!?()-:;\'"[]{}♩♪♫♬𝄞𝄢"',
			'-c tessedit_enable_doc_dict=1',
			'-c tessedit_parallelize=1',
			'-c tessedit_ocr_engine_mode=2',
			'-c load_system_dawg=1',
			'-c language_model_penalty_non_dict_word=0.5',  # Reduced penalty
			'-c language_model_penalty_non_freq_dict_word=0.1',
			'-c tessedit_write_images=0',  # Disable debug image output
			'-c preserve_interword_spaces=1'
		]
		if self.enable_gpu:
			config.append('--opencl')
		return ' '.join(config)

	def _load_cache(self):
		"""Load cache from disk"""
		cache_file = self._cache_dir / 'ocr_cache.json'
		if cache_file.exists():
			try:
				with open(cache_file, 'r') as f:
					cache_data = json.load(f)
					# Only load cache entries that haven't expired (24 hours)
					current_time = time.time()
					self._cache = {
						k: v for k, v in cache_data.items()
						if current_time - v.get('timestamp', 0) < 86400
					}
			except Exception as e:
				self.logger.error(f"Failed to load cache: {e}")
				self._cache = {}

	def _save_cache(self):
		"""Save cache to disk"""
		cache_file = self._cache_dir / 'ocr_cache.json'
		try:
			with open(cache_file, 'w') as f:
				json.dump(self._cache, f)
		except Exception as e:
			self.logger.error(f"Failed to save cache: {e}")

	def _get_cache_key(self, image_path: str) -> str:
		"""Generate cache key from image content"""
		try:
			with open(image_path, 'rb') as f:
				return hashlib.sha256(f.read()).hexdigest()
		except Exception:
			return image_path

	def _update_cache(self, key: str, value: Any):
		"""Update cache with LRU eviction"""
		if len(self._cache) >= self._cache_size:
			# Remove oldest entries
			sorted_cache = sorted(
				self._cache.items(),
				key=lambda x: x[1].get('timestamp', 0)
			)
			for old_key, _ in sorted_cache[:len(sorted_cache)//4]:  # Remove 25% oldest
				del self._cache[old_key]
		
		self._cache[key] = {
			'data': value,
			'timestamp': time.time()
		}
		self._save_cache()

	def process_image(self, image_path: Union[str, Image.Image], preprocess: bool = True) -> str:
		try:
			if isinstance(image_path, str):
				cache_key = self._get_cache_key(image_path)
				if cache_key in self._cache:
					self._cache_hits += 1
					return self._cache[cache_key]['data']
				self._cache_misses += 1
				
				image = Image.open(image_path)
			else:
				image = image_path
				cache_key = None

			if image.mode not in ('L', 'RGB'):
				image = image.convert('RGB')

			# Optionally preprocess image (skip if already preprocessed upstream)
			if preprocess:
				enhanced_image = self.preprocess_image(image)
				if isinstance(enhanced_image, np.ndarray):
					enhanced_image = Image.fromarray(enhanced_image)
			else:
				enhanced_image = image
			
			try:
				# Prefer word-level data to better preserve spacing and line breaks
				ocr_data = pytesseract.image_to_data(
					enhanced_image,
					lang=self.lang,
					config=self.config,
					output_type=pytesseract.Output.DICT
				)

				lines: List[str] = []
				current_line_index = None
				current_words: List[str] = []

				for word, conf, line_num in zip(ocr_data.get('text', []), ocr_data.get('conf', []), ocr_data.get('line_num', [])):
					try:
						c = int(conf)
					except Exception:
						c = -1
					if isinstance(line_num, str):
						try:
							ln = int(line_num)
						except Exception:
							ln = None
					else:
						ln = line_num

					if ln != current_line_index:
						if current_words:
							lines.append(' '.join(current_words))
							current_words = []
						current_line_index = ln

					if c >= self.conf_threshold and word and word.strip():
						current_words.append(word.strip())

				if current_words:
					lines.append(' '.join(current_words))

				text = '\n'.join([ln for ln in lines if ln.strip()])

				if text and len(text.strip()) > 0:
					if cache_key:
						self._update_cache(cache_key, text)
					return text
				return ""

			except pytesseract.TesseractError as e:
				self.logger.error(f"Tesseract Error: {str(e)}")
				return ""

		except Exception as e:
			self.logger.error(f"OCR Error: {str(e)}")
			return ""

	def process_image_fast(self, image: Image.Image) -> str:
		"""Fast path: minimal filtering using image_to_string for speed."""
		try:
			if image.mode not in ('L', 'RGB'):
				image = image.convert('RGB')
			text = pytesseract.image_to_string(
				image,
				lang=self.lang,
				config=self.config
			)
			return text if text else ""
		except Exception as e:
			self.logger.error(f"Fast OCR Error: {str(e)}")
			return ""

	def recognize(self, image: Image.Image, mode: str = 'fast') -> Tuple[str, float, int]:
		"""Run OCR and return (text, avg_confidence, char_count).

		mode:
		- 'fast': minimal preprocessing (convert to L if needed)
		- 'full': use preprocess_image for enhancement
		"""
		try:
			# If the caller didn't set a valid mode, fall back to configured behavior
			if mode not in ('fast', 'full'):
				mode = 'fast' if self.fast_preprocess else 'full'
			img = image
			if mode == 'full':
				if isinstance(img, Image.Image):
					processed = self.preprocess_image(img)
					img = Image.fromarray(processed)
			elif mode == 'fast':
				if img.mode not in ('L', 'RGB'):
					img = img.convert('RGB')
			else:
				# default to fast
				if img.mode not in ('L', 'RGB'):
					img = img.convert('RGB')

			data = pytesseract.image_to_data(
				img,
				lang=self.lang,
				config=self.config,
				output_type=pytesseract.Output.DICT
			)
			# Build lines while tracking confidences
			lines: List[str] = []
			current_line_index = None
			current_words: List[str] = []
			confs: List[float] = []
			for word, conf, line_num in zip(data.get('text', []), data.get('conf', []), data.get('line_num', [])):
				try:
					c = int(conf)
				except Exception:
					c = -1
				if isinstance(line_num, str):
					try:
						ln = int(line_num)
					except Exception:
						ln = None
				else:
					ln = line_num

				if ln != current_line_index:
					if current_words:
						lines.append(' '.join(current_words))
						current_words = []
					current_line_index = ln

				if word and word.strip():
					# Accumulate confidences regardless of threshold for avg calc
					if c >= 0:
						confs.append(float(c))
					# Only include words above threshold in assembled text
					if c >= self.conf_threshold:
						current_words.append(word.strip())

			if current_words:
				lines.append(' '.join(current_words))

			text = '\n'.join([ln for ln in lines if ln.strip()])
			avg_conf = float(sum(confs) / len(confs)) if confs else 0.0
			return text, avg_conf, len(text)
		except Exception as e:
			self.logger.error(f"Recognize failed: {e}")
			return "", 0.0, 0





	# Removed older preprocess_image/clean_text duplicate implementations to avoid conflicts

	def _get_skew_angle(self, image: np.ndarray) -> float:
		edges = cv2.Canny(image, 50, 150, apertureSize=3)
		lines = cv2.HoughLines(edges, 1, np.pi/180, 100)
		if lines is not None:
			angles = []
			for rho, theta in lines[:, 0]:
				angle = np.degrees(theta) - 90
				if abs(angle) < 45:
					angles.append(angle)
			if angles:
				return float(np.median(angles))
		return 0.0

	def _rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
		(h, w) = image.shape[:2]
		center = (w // 2, h // 2)
		M = cv2.getRotationMatrix2D(center, angle, 1.0)
		return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

	def _monitor_memory(self):
		"""Monitor memory usage"""
		process = psutil.Process(os.getpid())
		mem = process.memory_info().rss / 1024 / 1024  # MB
		self._memory_monitor['current'] = mem
		self._memory_monitor['peak'] = max(self._memory_monitor['peak'], mem)
		if mem > self.preprocessing_params['max_batch_memory']:
			self._memory_monitor['warnings'] += 1
			self.logger.warning(f"High memory usage: {mem:.2f}MB")
		return mem

	def process_image_in_chunks(self, image: np.ndarray) -> str:
		"""Process large images in chunks to manage memory"""
		h, w = image.shape[:2]
		chunk_h, chunk_w = self.preprocessing_params['chunk_size']
		
		# Skip chunking for small images
		if h <= chunk_h and w <= chunk_w:
			return self.process_image(Image.fromarray(image))
		
		results = []
		for y in range(0, h, chunk_h):
			for x in range(0, w, chunk_w):
				chunk = image[y:min(y+chunk_h, h), x:min(x+chunk_w, w)]
				if chunk.size > 0:
					chunk_result = self.process_image(Image.fromarray(chunk))
					results.append(chunk_result)
				
				# Monitor and manage memory
				if self._monitor_memory() > self.preprocessing_params['max_batch_memory']:
					gc.collect()
		
		return ' '.join(results)

	def process_images(self, image_paths: List[str]) -> str:
		"""Memory-efficient batch processing"""
		results: List[str] = []
		current_batch: List[str] = []
		current_memory = 0.0
		total_memory = float(self.preprocessing_params['max_batch_memory'])
		
		for path in image_paths:
			img_size = os.path.getsize(path) / (1024 * 1024)  # MB
			if current_memory + img_size > total_memory and current_batch:
				batch_results = self._process_batch(current_batch)
				results.extend(batch_results)
				current_batch = []
				current_memory = 0.0
				gc.collect()
			
			current_batch.append(path)
			current_memory += img_size
		
		# Process remaining images
		if current_batch:
			batch_results = self._process_batch(current_batch)
			results.extend(batch_results)
		
		return '\n\n'.join(filter(None, results))

	def _process_batch(self, image_paths: List[str]) -> List[str]:
		"""Process a batch of images with memory monitoring"""
		try:
			preprocessed = self.parallel_processor.process_batch(
				items=image_paths,
				process_func=self._preprocess_single_image
			)
			
			results = []
			for img, path in zip(preprocessed['results'], image_paths):
				if img is not None:
					# Process in chunks if needed
					if img.size > self.preprocessing_params['min_chunk_size'][0] * self.preprocessing_params['min_chunk_size'][1]:
						text = self.process_image_in_chunks(img)
					else:
						text = self._process_preprocessed_image((img, path))
					results.append(text)
					
					# Monitor memory
					self._monitor_memory()
			
			return results
		except Exception as e:
			self.logger.error(f"Batch processing failed: {str(e)}")
			return []

	def _preprocess_single_image(self, image_path: str) -> Optional[np.ndarray]:
		"""Preprocess a single image"""
		try:
			image = Image.open(image_path)
			if image.mode not in ('L', 'RGB'):
				image = image.convert('RGB')

			# Process image
			processed = self.preprocess_image(image)
			return processed

		except Exception as e:
			self.logger.error(f"Preprocessing failed for {image_path}: {str(e)}")
			return None

	def _process_preprocessed_image(self, data: tuple) -> str:
		"""Process a preprocessed image"""
		preprocessed_image, image_path = data
		if preprocessed_image is None:
			return ""
			
		try:
			# Convert numpy array back to PIL Image
			image = Image.fromarray(preprocessed_image)
			
			# Run OCR
			ocr_data = pytesseract.image_to_data(
				image,
				lang=self.lang,
				config=self.config,
				output_type=pytesseract.Output.DICT
			)
			
			# Filter words by confidence (cast conf to int; -1 means no confidence)
			text_parts = []
			for word, conf in zip(ocr_data['text'], ocr_data['conf']):
				try:
					c = int(conf)
				except Exception:
					c = -1
				if c > 60 and word.strip():
					text_parts.append(word)
			text = ' '.join(text_parts)
			
			return self.clean_text(text)

		except Exception as e:
			self.logger.error(f"OCR failed for {image_path}: {str(e)}")
			return ""

	def get_stats(self) -> Dict[str, Any]:
		"""Get processing statistics"""
		total_cache_requests = self._cache_hits + self._cache_misses
		cache_hit_rate = (
			self._cache_hits / total_cache_requests * 100 
			if total_cache_requests > 0 else 0
		)
		
		return {
			'processed': self.stats['processed'],
			'failed': self.stats['failed'],
			'cache_hits': self._cache_hits,
			'cache_misses': self._cache_misses,
			'cache_hit_rate': f"{cache_hit_rate:.2f}%",
			'cache_size': len(self._cache),
			'worker_stats': self.parallel_processor.worker_stats
		}

	def get_confidence_score(self, text: str) -> float:
		"""Calculate confidence score for OCR text based on word recognition"""
		try:
			image = self._text_to_image(text)
			data = pytesseract.image_to_data(
				image,
				lang=self.lang,
				config=self.config,
				output_type=pytesseract.Output.DICT
			)
			
			confidences = [float(conf) for conf in data['conf'] if conf != '-1']
			if not confidences:
				return 0.0
				
			word_lengths = [len(word) for word in data['text'] if word.strip()]
			weighted_conf = sum(conf * length for conf, length in zip(confidences, word_lengths))
			total_length = sum(word_lengths)
			
			return weighted_conf / total_length if total_length > 0 else 0.0
			
		except Exception as e:
			self.logger.error(f"Failed to calculate confidence score: {str(e)}")
			return 0.0

	def _text_to_image(self, text: str) -> Image.Image:
		"""Convert text to image for OCR analysis"""
		width = 1000
		height = max(200, len(text.split('\n')) * 30)
		image = Image.new('L', (width, height), 255)
		draw = ImageDraw.Draw(image)
		
		try:
			font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
		except:
			font = ImageFont.load_default()
		
		draw.text((10, 10), text, font=font, fill=0)
		return image

    # Removed duplicate extract_text_with_fallback definition (kept the later one below)

	def detect_features(self, text: str) -> Dict[str, bool]:
		"""Detect mathematical and musical features in text"""
		features = {'math': False, 'music': False}
		
		for feature, patterns in self.feature_patterns.items():
			for pattern in patterns:
				if re.search(pattern, text):
					features[feature] = True
					break
		
		return features

	def preprocess_image(self, image: Image.Image) -> np.ndarray:
		"""Memory-optimized image preprocessing"""
		# Convert to numpy array with memory optimization
		img_array = np.asarray(image, dtype=np.uint8)
		
		# Free original image memory
		image.close()
		del image
		
		# Convert to grayscale efficiently
		if len(img_array.shape) == 3:
			# Use memory-efficient grayscale conversion
			gray = np.dot(img_array[...,:3], [0.2989, 0.5870, 0.1140])
			gray = gray.astype(np.uint8)
			del img_array
		else:
			gray = img_array
			
		# Process in smaller chunks for large images
		if gray.size > 25_000_000:  # >25MP
			scale_factor = np.sqrt(25_000_000 / gray.size)
			new_size = tuple(int(dim * scale_factor) for dim in gray.shape[:2][::-1])
			gray = cv2.resize(gray, new_size, interpolation=cv2.INTER_AREA)
		
		# Optimize memory usage in preprocessing steps
		angle = self._get_skew_angle(gray)
		if abs(angle) > 0.5:
			gray = self._rotate_image(gray, angle)
		
		# Apply CLAHE with memory optimization
		clahe = cv2.createCLAHE(
			clipLimit=self.preprocessing_params['contrast_limit'],
			tileGridSize=(8,8)
		)
		gray = clahe.apply(gray)
		
		# Efficient denoising
		gray = cv2.fastNlMeansDenoising(
			gray,
			None,
			self.preprocessing_params['denoise_strength'],
			7,
			21
		)
		
		# Memory-efficient binarization
		binary = cv2.adaptiveThreshold(
			gray,
			255,
			cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
			cv2.THRESH_BINARY,
			11,
			2
		)
		del gray
		
		return binary

	def clean_text(self, text: str) -> str:
		"""Clean and normalize OCR output text"""
		if not text:
			return ""
		
		# Remove musical notation and symbols
		text = re.sub(r'[♩♪♫♬𝄞𝄢]', '', text)
		text = re.sub(r'[\u2600-\u26FF]', '', text)  # Remove misc symbols
		
		# Keep only printable chars and newlines
		text = ''.join(char for char in text if char.isprintable() or char in '\n\t')
		
		# Fix common OCR errors
		text = self._fix_common_errors(text)
		text = self._fix_word_breaks(text)
		text = self._normalize_spacing(text)
		text = self._fix_paragraph_breaks(text)
		
		# Clean up chapter headings
		text = re.sub(r'(?i)ch[a-z]*\s*(\d+)', r'Chapter \1', text)
		text = re.sub(r'(?i)part\s*(\d+)', r'Part \1', text)
		text = re.sub(r'(?i)section\s*(\d+)', r'Section \1', text)
		
		return text

	def _fix_common_errors(self, text: str) -> str:
		"""Fix common OCR recognition errors with improved quotation handling"""
		replacements = {
			r'l(?=[A-Z])': 'I',
			r'(?<=\d)O|o(?=\d)': '0',
			r'(?<=\d)l(?=\d)': '1',
			r'\bI\b': '1',
			r'rn\b': 'm',
			r'\bm\b': 'in',
			r'["""]': '"',  # Handle all types of double quotes
			r'['']': "'",   # Handle all types of single quotes
			r'[-‐‐‒–—―]': '-',  # Handle all types of hyphens/dashes
			r'\s+[-]\s+': ' - ',
			r'(?<=\d),(?=\d)': '.',
			r'(?<=[a-z])\.(?=[a-z])': ' ',
			r'(?<=\d)o(?=\d)': '0',
			r'(?<=[A-Za-z])1(?=[A-Za-z])': 'l'
		}
		
		for pattern, replacement in replacements.items():
			try:
				text = re.sub(pattern, replacement, text)
			except Exception as e:
				self.logger.warning(f"Error applying replacement {pattern}: {e}")
				continue
		
		# Additional quotation mark cleanup
		text = text.replace('\u201C', '"').replace('\u201D', '"')  # Smart quotes
		text = text.replace('\u2018', "'").replace('\u2019', "'")  # Smart single quotes
		
		return text

	def _fix_word_breaks(self, text: str) -> str:
		"""Fix word breaks and hyphenation"""
		text = text.replace('\u00AD', '')
		lines = text.split('\n')
		result = []
		skip_next = False
		
		for i, line in enumerate(lines):
			if skip_next:
				skip_next = False
				continue
			if i < len(lines) - 1 and line.endswith('-'):
				next_line = lines[i + 1].lstrip()
				if next_line and next_line[0].islower():
					result.append(line[:-1] + next_line)
					skip_next = True
					continue
			result.append(line)
		
		return '\n'.join(result)

	def _normalize_spacing(self, text: str) -> str:
		"""Normalize spacing and punctuation"""
		# Collapse spaces and tabs but preserve newlines
		text = re.sub(r'[ \t]+', ' ', text)
		# Normalize excessive blank lines to at most one blank line
		text = re.sub(r'\n{3,}', '\n\n', text)
		text = re.sub(r'\s+([.,!?:;])', r'\1', text)
		text = re.sub(r'([.,!?:;])\s*([A-Z])', r'\1 \2', text)
		text = re.sub(r'\s*\(\s*', ' (', text)
		text = re.sub(r'\s*\)\s*', ') ', text)
		return text

	def _fix_paragraph_breaks(self, text: str) -> str:
		"""Fix paragraph breaks and formatting"""
		paragraphs = text.split('\n\n')
		cleaned = []
		for para in paragraphs:
			para = ' '.join(line.strip() for line in para.split('\n'))
			para = ' '.join(para.split())
			if para:
				cleaned.append(para)
		return '\n\n'.join(cleaned)

    # Removed earlier duplicate of _get_skew_angle/_rotate_image (kept single definitions below)

	def extract_text_with_fallback(self, pdf_path: str, page_num: int) -> str:
		"""Extract text using multiple fallback methods"""
		try:
			# Try PyPDF2 first
			with open(pdf_path, 'rb') as file:
				reader = PyPDF2.PdfReader(file)
				if 0 <= page_num < len(reader.pages):
					text = reader.pages[page_num].extract_text()
					if text.strip():
						return text

			# Try PDFMiner if PyPDF2 fails
			text = extract_text(pdf_path, page_numbers=[page_num])
			if text.strip():
				return text

			# OCR fallback
			images = convert_from_path(pdf_path, first_page=page_num+1, last_page=page_num+1)
			if images:
				return self.process_image(images[0])

		except Exception as e:
			self.logger.error(f"Text extraction failed for page {page_num}: {e}")
			return ""

		# If no method returned text, return empty string
		return ""