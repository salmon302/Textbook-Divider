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

class TestSchoenbergPage42(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		cls.base_dir = Path("/home/seth-n/CLionProjects/Textbook Divider")
		cls.input_file = cls.base_dir / "data/input/Arnold Schoenberg, Gerald Strang, Leonard Stein - Fundamentals of Musical Composition (1982, Faber & Faber) - libgen.li.pdf"
		cls.output_dir = cls.base_dir / "tests/phase_3_5/output/schoenberg_p42"
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
				self.logger.error(f"Failed to extract page: {e}")
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

	def test_text_extraction(self):
		self.logger.info("Testing text extraction")
		page_image = self.extract_page(42)
		
		# Load and preprocess image
		img = cv2.imread(str(page_image))
		gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
		
		# Apply thresholding
		_, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
		
		# Save preprocessed image
		self.save_debug_image(binary, "preprocessed")
		
		# Convert to PIL Image
		pil_image = Image.fromarray(binary)
		
		try:
			# Direct OCR with simple config
			text = pytesseract.image_to_string(
				pil_image,
				config='--psm 3 --oem 1'
			)
			
			if text and len(text.strip()) > 0:
				# Save results
				ocr_output = {
					"text_content": text,
					"text_length": len(text),
					"timestamp": self.timestamp
				}
				with open(self.debug_dir / f"ocr_results_{self.timestamp}.json", 'w') as f:
					json.dump(ocr_output, f, indent=2)
				
				self.assertTrue(len(text.strip()) > 0)
				self.logger.info(f"Successfully extracted {len(text)} characters")
			else:
				self.fail("No text content extracted")
				
		except Exception as e:
			self.logger.error(f"OCR failed: {str(e)}")
			self.fail(f"OCR failed with error: {str(e)}")

	def test_musical_notation_detection(self):
		self.logger.info("Testing musical notation detection")
		page_image = self.extract_page(42)
		img_array = cv2.imread(str(page_image))
		self.assertIsNotNone(img_array, "Failed to load image")
		
		music_regions = self.omr_processor.detect_staves(img_array)
		self.assertIsNotNone(music_regions)
		self.assertTrue(len(music_regions) > 0)
		
		detection_results = {
			"num_regions": len(music_regions),
			"regions": [{"x": int(r[0]), "y": int(r[1]), 
						"w": int(r[2]), "h": int(r[3])} 
					   for r in music_regions]
		}
		
		with open(self.debug_dir / f"music_regions_{self.timestamp}.json", 'w') as f:
			json.dump(detection_results, f, indent=2)
		
		self.save_debug_image(img_array, "music_detection", detection_results["regions"])
		self.logger.info(f"Detected {len(music_regions)} musical regions")

if __name__ == '__main__':
	unittest.main(verbosity=2)