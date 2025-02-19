from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Iterator
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
	def __init__(self, force_ocr: bool = False, max_pages: int = 50):
		self.ocr = OCRProcessor()
		self.force_ocr = force_ocr
		self.max_pages = max_pages
	
	def validate_file(self, file_path: Path) -> bool:
		return file_path.suffix.lower() == '.pdf'
	
	def read_content(self, file_path: Path, page_range: tuple = None, max_pages: int = None) -> str:
		"""Read content from PDF with optional page range"""
		pages_to_process = max_pages if max_pages is not None else self.max_pages
		
		if page_range:
			start_page, end_page = page_range
			pages_to_process = min(end_page - start_page + 1, pages_to_process)
		
		if self.force_ocr:
			return self._process_with_ocr(file_path, pages_to_process, page_range)
		
		try:
			import fitz
			doc = fitz.open(file_path)
			text_parts = []
			
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
			
			# Use needs_ocr to determine if OCR is needed
			if self.needs_ocr(combined_text):
				print("Text extraction insufficient, falling back to OCR")
				return self._process_with_ocr(file_path, pages_to_process)
			
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
	
	def _process_with_ocr(self, file_path: Path, pages_to_process: int, page_range: tuple = None) -> str:
		text_parts = []
		with tempfile.TemporaryDirectory() as temp_dir:
			try:
				first_page = page_range[0] if page_range else 1
				last_page = min(first_page + pages_to_process - 1, 
							  page_range[1] if page_range else first_page + pages_to_process - 1)
				
				images = convert_from_path(
					file_path,
					first_page=first_page,
					last_page=last_page,
					dpi=300,  # Lower DPI for faster processing
					grayscale=True,  # Convert to grayscale
					thread_count=4,
					timeout=120  # Increased timeout
				)
				
				for i, image in enumerate(images, 1):
					print(f"Processing page {i} with OCR")
					try:
						# Basic image preprocessing
						enhanced = self._enhance_image(image)
						text = self.ocr.process_image(enhanced)
						
						if text and text.strip():
							cleaned_text = self._post_process_text(text)
							if cleaned_text:
								text_parts.append(cleaned_text)
						else:
							print(f"No text extracted from page {i}")
							
					except Exception as e:
						print(f"Error processing page {i}: {e}")
						continue
				
				if not text_parts:
					print("No text could be extracted from any page")
					return ""
					
				return '\n\n'.join(text_parts)
				
			except Exception as e:
				print(f"Error during PDF processing: {e}")
				return ""

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
		
		# Apply slight dilation to connect broken text
		kernel = np.ones((2,2), np.uint8)
		dilated = cv2.dilate(binary, kernel, iterations=1)
		
		return Image.fromarray(dilated)

	
	def _post_process_text(self, text: str) -> str:
		"""Post-process OCR text to preserve special notations"""
		# Preserve mathematical symbols
		text = re.sub(r'([∫∑∏√∆∇∈∉∋∌∩∪⊂⊃⊆⊇≈≠≡≤≥])', r' \1 ', text)
		
		# Preserve musical terms
		musical_terms = ['tempo', 'allegro', 'andante', 'forte', 'piano',
						'chord', 'scale', 'note', 'rhythm', 'melody']
		for term in musical_terms:
			text = re.sub(rf'\b{term}\b', lambda m: f' {m.group(0)} ', text,
						 flags=re.IGNORECASE)
		
		# Clean up spacing
		text = re.sub(r'\s+', ' ', text)
		text = re.sub(r'(?<=[.,!?:;])\s*(?=[A-Z])', '\n', text)
		
		return text.strip()






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