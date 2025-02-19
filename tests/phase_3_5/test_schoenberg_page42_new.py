#!/usr/bin/env python3
import unittest
import sys
import os
from pathlib import Path
import logging
import cv2
import numpy as np
from PIL import Image, ImageEnhance
import json
from datetime import datetime
import time
from textbook_divider.file_handler import PDFHandler
from textbook_divider.omr_processor import OMRProcessor
from textbook_divider.ocr_processor import OCRProcessor

class NumpyEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, (np.integer, np.floating)):
			return float(obj)
		elif isinstance(obj, np.ndarray):
			return obj.tolist()
		elif isinstance(obj, np.bool_):
			return bool(obj)
		elif isinstance(obj, (complex, np.complex64, np.complex128)):
			return [obj.real, obj.imag]
		return super().default(obj)

class TestSchoenbergPage42(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		cls.metrics = {"timing": {}, "accuracy": {}, "performance": {}}
		
		log_file = Path(__file__).parent / f"test_log_{cls.timestamp}.log"
		logging.basicConfig(
			level=logging.DEBUG,
			format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
			handlers=[
				logging.FileHandler(log_file),
				logging.StreamHandler(sys.stdout)
			]
		)
		cls.logger = logging.getLogger(__name__)
		
		cls.base_dir = Path(__file__).parent.parent.parent
		cls.input_file = cls.base_dir / "data/input/Arnold Schoenberg, Gerald Strang, Leonard Stein - Fundamentals of Musical Composition (1982, Faber & Faber) - libgen.li.pdf"
		cls.output_dir = cls.base_dir / "tests/phase_3_5/output/schoenberg_p42"
		cls.debug_dir = cls.output_dir / "debug"
		cls.debug_dir.mkdir(parents=True, exist_ok=True)
		
		cls.file_handler = PDFHandler()
		cls.omr_processor = OMRProcessor()
		cls.ocr_processor = OCRProcessor()
		
		cls.config = {
			"timestamp": cls.timestamp,
			"input_file": str(cls.input_file),
			"output_dir": str(cls.output_dir),
			"debug_dir": str(cls.debug_dir),
			"test_parameters": {
				"ocr_confidence_threshold": 0.7,
				"staff_detection_threshold": 0.8,
				"symbol_confidence_threshold": 0.75
			}
		}
		with open(cls.debug_dir / "test_config.json", 'w') as f:
			json.dump(cls.config, f, indent=2, cls=NumpyEncoder)

	def setUp(self):
		self.start_time = time.time()
		self.logger.info(f"Starting test at {datetime.now()}")

	def tearDown(self):
		duration = time.time() - self.start_time
		self.logger.info(f"Test duration: {duration:.2f} seconds")
		self.__class__.metrics["timing"][self._testMethodName] = duration

	def save_debug_image(self, image, name: str, annotations=None):
		debug_path = self.debug_dir / f"{name}_{self.timestamp}.png"
		if isinstance(image, np.ndarray):
			annotated_img = image.copy()
			if annotations:
				for ann in annotations:
					cv2.rectangle(annotated_img, 
								(ann['x'], ann['y']), 
								(ann['x'] + ann['w'], ann['y'] + ann['h']), 
								(0, 255, 0), 2)
			cv2.imwrite(str(debug_path), annotated_img)
		elif isinstance(image, Image.Image):
			image.save(str(debug_path))
		self.logger.debug(f"Saved debug image: {debug_path}")
		return debug_path

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

	def test_page_extraction(self):
		self.logger.info("Testing page extraction")
		page_image = self.extract_page(42)
		self.assertTrue(page_image.exists())
		img_size = page_image.stat().st_size
		self.assertTrue(img_size > 0)
		self.logger.info(f"Extracted page size: {img_size} bytes")
		img = cv2.imread(str(page_image))
		self.save_debug_image(img, "extracted_page")

	def test_text_extraction(self):
		self.logger.info("Testing text extraction")
		page_image = self.extract_page(42)
		pil_image = Image.open(str(page_image))
		
		stages = {
			"rgb": pil_image.convert('RGB'),
			"contrast": ImageEnhance.Contrast(pil_image).enhance(2.5),
			"sharpness": ImageEnhance.Sharpness(pil_image).enhance(2.5),
			"grayscale": ImageEnhance.Contrast(pil_image.convert('L')).enhance(2.0),
			"brightness": ImageEnhance.Brightness(pil_image).enhance(1.5)
		}
		
		text_content = None
		for stage_name, stage_img in stages.items():
			try:
				self.save_debug_image(stage_img, f"ocr_{stage_name}")
				stage_text = self.ocr_processor.process_image(stage_img)
				if stage_text and len(stage_text.strip()) > 0:
					text_content = stage_text
					self.logger.info(f"Successfully extracted text using {stage_name} stage")
					break
			except Exception as e:
				self.logger.warning(f"OCR failed for {stage_name} stage: {str(e)}")
				continue
		
		if text_content:
			ocr_output = {
				"text_content": text_content,
				"text_length": len(text_content),
				"timestamp": self.timestamp
			}
			with open(self.debug_dir / f"ocr_results_{self.timestamp}.json", 'w') as f:
				json.dump(ocr_output, f, indent=2)
			
			self.assertTrue(len(text_content.strip()) > 0)
			self.logger.info(f"Extracted {len(text_content)} characters of text")
		else:
			self.logger.error("No text content extracted from any preprocessing stage")
			self.fail("OCR failed to extract any text content")

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
			"regions": [{"x": float(r[0]), "y": float(r[1]), 
						"w": float(r[2]), "h": float(r[3])} 
					   for r in music_regions]
		}
		
		with open(self.debug_dir / f"music_regions_{self.timestamp}.json", 'w') as f:
			json.dump(detection_results, f, indent=2)
		
		self.save_debug_image(img_array, "music_detection", detection_results["regions"])
		self.logger.info(f"Detected {len(music_regions)} musical regions")

if __name__ == '__main__':
	unittest.main(verbosity=2)