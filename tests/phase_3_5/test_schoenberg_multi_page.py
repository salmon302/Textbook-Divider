#!/usr/bin/env python3
import unittest
import sys
import os
from pathlib import Path
import logging
import cv2
import numpy as np
from PIL import Image
import pytesseract
import json
from datetime import datetime
from textbook_divider.file_handler import PDFHandler
from textbook_divider.omr_processor import OMRProcessor

class TestSchoenbergMultiPage(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		cls.base_dir = Path("/home/seth-n/CLionProjects/Textbook Divider")
		cls.input_file = cls.base_dir / "data/input/Arnold Schoenberg, Gerald Strang, Leonard Stein - Fundamentals of Musical Composition (1982, Faber & Faber) - libgen.li.pdf"
		cls.output_dir = cls.base_dir / "tests/phase_3_5/output/schoenberg_multi"
		cls.debug_dir = cls.output_dir / "debug"
		cls.debug_dir.mkdir(parents=True, exist_ok=True)
		
		logging.basicConfig(
			level=logging.DEBUG,
			format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
			handlers=[
				logging.FileHandler(cls.debug_dir / f"test_log_{cls.timestamp}.log"),
				logging.StreamHandler(sys.stdout)
			]
		)
		cls.logger = logging.getLogger(__name__)
		
		cls.file_handler = PDFHandler()
		cls.omr_processor = OMRProcessor()
		
		# Pages to test (focusing on sections with musical notation)
		cls.test_pages = [30, 42, 57, 71, 96]

	def extract_page(self, page_num: int) -> Path:
		output_path = self.output_dir / f"page{page_num}.png"
		if not output_path.exists():
			try:
				import fitz
				doc = fitz.open(self.input_file)
				page = doc[page_num - 1]
				pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
				pix.save(str(output_path))
				doc.close()
			except Exception as e:
				self.logger.error(f"Failed to extract page {page_num}: {e}")
				raise
		return output_path

	def save_debug_image(self, image, name: str, annotations=None):
		debug_path = self.debug_dir / f"{name}_{self.timestamp}.png"
		if isinstance(image, np.ndarray):
			annotated_img = image.copy()
			if annotations:
				for ann in annotations:
					x, y = int(ann['x']), int(ann['y'])
					w, h = int(ann['w']), int(ann['h'])
					cv2.rectangle(annotated_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
			cv2.imwrite(str(debug_path), annotated_img)
		elif isinstance(image, Image.Image):
			image.save(str(debug_path))
		self.logger.debug(f"Saved debug image: {debug_path}")
		return debug_path

	def process_page(self, page_num: int):
		self.logger.info(f"Processing page {page_num}")
		page_image = self.extract_page(page_num)
		
		# Load and preprocess image
		img = cv2.imread(str(page_image))
		gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
		
		# Apply thresholding
		_, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
		
		# Save preprocessed image
		self.save_debug_image(binary, f"preprocessed_p{page_num}")
		
		# Process text
		pil_image = Image.fromarray(binary)
		try:
			text = pytesseract.image_to_string(
				pil_image,
				config='--psm 3 --oem 1'
			)
			
			if text and len(text.strip()) > 0:
				ocr_output = {
					"page": page_num,
					"text_content": text,
					"text_length": len(text),
					"timestamp": self.timestamp
				}
				with open(self.debug_dir / f"ocr_results_p{page_num}_{self.timestamp}.json", 'w') as f:
					json.dump(ocr_output, f, indent=2)
				self.logger.info(f"Page {page_num}: Extracted {len(text)} characters")
			else:
				self.logger.error(f"Page {page_num}: No text content extracted")
				return False
		except Exception as e:
			self.logger.error(f"Page {page_num}: OCR failed - {str(e)}")
			return False
		
		# Process musical notation
		try:
			music_regions = self.omr_processor.detect_staves(img)
			if music_regions and len(music_regions) > 0:
				detection_results = {
					"page": page_num,
					"num_regions": len(music_regions),
					"regions": [{"x": int(r[0]), "y": int(r[1]), 
							   "w": int(r[2]), "h": int(r[3])} 
							  for r in music_regions]
				}
				with open(self.debug_dir / f"music_regions_p{page_num}_{self.timestamp}.json", 'w') as f:
					json.dump(detection_results, f, indent=2)
				
				self.save_debug_image(img, f"music_detection_p{page_num}", detection_results["regions"])
				self.logger.info(f"Page {page_num}: Detected {len(music_regions)} musical regions")
			else:
				self.logger.warning(f"Page {page_num}: No musical regions detected")
		except Exception as e:
			self.logger.error(f"Page {page_num}: OMR failed - {str(e)}")
			return False
		
		return True

	def test_multiple_pages(self):
		results = {}
		for page_num in self.test_pages:
			success = self.process_page(page_num)
			results[page_num] = success
			
		# Save overall results
		with open(self.debug_dir / f"multi_page_results_{self.timestamp}.json", 'w') as f:
			json.dump({
				"timestamp": self.timestamp,
				"pages_processed": len(self.test_pages),
				"success_rate": sum(results.values()) / len(results),
				"results": results
			}, f, indent=2)
		
		# Assert overall success rate
		success_rate = sum(results.values()) / len(results)
		self.assertGreater(success_rate, 0.8, "Overall success rate below 80%")

if __name__ == '__main__':
	unittest.main(verbosity=2)