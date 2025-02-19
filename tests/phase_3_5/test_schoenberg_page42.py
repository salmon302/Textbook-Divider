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

class TestSchoenbergPage42(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Enhanced logging setup with performance tracking
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
        
        # Setup directories
        cls.base_dir = Path(__file__).parent.parent.parent
        cls.input_file = cls.base_dir / "data/input/Arnold Schoenberg, Gerald Strang, Leonard Stein - Fundamentals of Musical Composition (1982, Faber & Faber) - libgen.li.pdf"
        cls.output_dir = cls.base_dir / "tests/phase_3_5/output/schoenberg_p42"
        cls.debug_dir = cls.output_dir / "debug"
        cls.debug_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize processors
        cls.file_handler = PDFHandler()
        cls.omr_processor = OMRProcessor()
        cls.ocr_processor = OCRProcessor()
        
        # Save test configuration
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
            json.dump(cls.config, f, indent=2)
    
    def setUp(self):
        self.start_time = time.time()
        self.logger.info(f"Starting test at {datetime.now()}")

    def tearDown(self):
        duration = time.time() - self.start_time
        self.logger.info(f"Test duration: {duration:.2f} seconds")
        self.__class__.metrics["timing"][self._testMethodName] = duration

    def save_debug_image(self, image, name: str, annotations=None, overlay_text=None):
        """Enhanced debug image saving with annotations and text overlay"""
        debug_path = self.debug_dir / f"{name}_{self.timestamp}.png"
        if isinstance(image, np.ndarray):
            annotated_img = image.copy()
            
            # Add annotations
            if annotations:
                for ann in annotations:
                    cv2.rectangle(annotated_img, 
                                (ann['x'], ann['y']), 
                                (ann['x'] + ann['w'], ann['y'] + ann['h']), 
                                (0, 255, 0), 2)
                    
            # Add text overlay
            if overlay_text:
                cv2.putText(annotated_img, overlay_text,
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1,
                           (0, 0, 255), 2)
            
            cv2.imwrite(str(debug_path), annotated_img)
        elif isinstance(image, Image.Image):
            image.save(str(debug_path))
            
        self.logger.debug(f"Saved debug image: {debug_path}")
        return debug_path

    def extract_page(self, page_num: int) -> Path:
        """Extract page with enhanced error handling"""
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

    def validate_music_notation(self, regions, img_array):
        """Validate musical notation with detailed metrics"""
        validation_metrics = {
            "num_regions": len(regions),
            "avg_region_size": np.mean([r[2] * r[3] for r in regions]) if regions else 0,
            "total_area": sum(r[2] * r[3] for r in regions) if regions else 0,
            "region_distribution": []
        }
        
        # Analyze region distribution
        if regions:
            y_positions = [r[1] for r in regions]
            validation_metrics["region_distribution"] = {
                "min_y": min(y_positions),
                "max_y": max(y_positions),
                "avg_y": np.mean(y_positions)
            }
        
        return validation_metrics

    def test_page_extraction(self):
        self.logger.info("Testing page extraction")
        page_image = self.extract_page(42)
        self.assertTrue(page_image.exists())
        img_size = page_image.stat().st_size
        self.assertTrue(img_size > 0)
        self.logger.info(f"Extracted page size: {img_size} bytes")
        
        # Save extracted page for debugging
        img = cv2.imread(str(page_image))
        self.save_debug_image(img, "extracted_page")
    
    def test_musical_notation_detection(self):
        self.logger.info("Testing musical notation detection")
        page_image = self.extract_page(42)
        img_array = cv2.imread(str(page_image))
        self.assertIsNotNone(img_array, "Failed to load image")
        
        # Get staff positions and save debug visualization
        music_regions = self.omr_processor.detect_staves(img_array)
        self.assertIsNotNone(music_regions)
        self.assertTrue(len(music_regions) > 0)
        
        # Save detection results
        detection_results = {
            "num_regions": len(music_regions),
            "regions": [{"x": r[0], "y": r[1], "w": r[2], "h": r[3]} for r in music_regions]
        }
        with open(self.debug_dir / f"music_regions_{self.timestamp}.json", 'w') as f:
            json.dump(detection_results, f, indent=2)
        
        # Save annotated image
        self.save_debug_image(img_array, "music_detection", detection_results["regions"])
        
        self.logger.info(f"Detected {len(music_regions)} musical regions")
    
    def test_text_extraction(self):
        self.logger.info("Testing text extraction")
        page_image = self.extract_page(42)
        pil_image = Image.open(str(page_image))
        
        # Save original for comparison
        self.save_debug_image(pil_image, "original")
        
        # Enhanced preprocessing pipeline with debugging
        stages = {
            "rgb": pil_image.convert('RGB'),
            "contrast": ImageEnhance.Contrast(pil_image).enhance(1.5),
            "sharpness": ImageEnhance.Sharpness(pil_image).enhance(1.5),
            "grayscale": pil_image.convert('L')
        }
        
        # Save each preprocessing stage
        for stage_name, stage_img in stages.items():
            self.save_debug_image(stage_img, f"ocr_{stage_name}")
        
        # Process with OCR
        text_content = self.ocr_processor.process_image(stages["grayscale"])
        self.assertIsNotNone(text_content)
        
        # Save OCR results
        ocr_output = {
            "text_content": text_content,
            "text_length": len(text_content),
            "timestamp": self.timestamp
        }
        with open(self.debug_dir / f"ocr_results_{self.timestamp}.json", 'w') as f:
            json.dump(ocr_output, f, indent=2)
        
        if not text_content.strip():
            self.logger.error("No text content extracted")
            self.fail("OCR failed to extract any text content")
        
        self.assertTrue(len(text_content.strip()) > 0)
        self.logger.info(f"Extracted {len(text_content)} characters of text")
    
    def test_mixed_content_handling(self):
        self.logger.info("Testing mixed content handling")
        page_image = self.extract_page(42)
        img_array = cv2.imread(str(page_image))
        
        # Process and validate results
        results = self.omr_processor.process_page(str(page_image))
        self.assertIsNotNone(results)
        
        # Save detailed results
        with open(self.debug_dir / f"mixed_content_results_{self.timestamp}.json", 'w') as f:
            json.dump(results, f, indent=2)
        
        # Validate staff positions
        staff_positions = results.get('staff_positions', [])
        self.assertTrue(len(staff_positions) > 0)
        self.logger.info(f"Detected {len(staff_positions)} staff positions")
        
        # Validate symbol confidence
        symbol_conf = results.get('symbol_confidence', {})
        confidence_scores = list(symbol_conf.values())
        if confidence_scores:
            avg_confidence = sum(confidence_scores) / len(confidence_scores)
            self.logger.info(f"Average symbol confidence: {avg_confidence:.2f}")
            self.assertTrue(avg_confidence > 0.5)
    
    def test_output_validation(self):
        self.logger.info("Testing output validation")
        page_image = self.extract_page(42)
        
        # Process page and collect metrics
        omr_results = self.omr_processor.process_page(str(page_image))
        staff_positions = omr_results.get('staff_positions', [])
        symbol_conf = omr_results.get('symbol_confidence', {})
        
        # Validate and log metrics
        validation_results = {
            "num_staves": len(staff_positions),
            "num_symbols": len(symbol_conf),
            "avg_confidence": sum(symbol_conf.values()) / len(symbol_conf) if symbol_conf else 0,
            "min_confidence": min(symbol_conf.values()) if symbol_conf else 0,
            "max_confidence": max(symbol_conf.values()) if symbol_conf else 0
        }
        
        # Save validation results
        with open(self.debug_dir / f"validation_results_{self.timestamp}.json", 'w') as f:
            json.dump(validation_results, f, indent=2)
        
        self.logger.info(f"Validation metrics: {validation_results}")
        
        # Assert quality thresholds
        self.assertTrue(validation_results["num_staves"] > 0)
        self.assertTrue(validation_results["avg_confidence"] > 0.5)

def test_comprehensive_page_analysis(self):
    """New comprehensive test method"""
    self.logger.info("Starting comprehensive page analysis")
    start_time = time.time()
    
    # Extract and validate page
    page_image = self.extract_page(42)
    img_array = cv2.imread(str(page_image))
    
    # Process with both OMR and OCR
    omr_results = self.omr_processor.process_page(str(page_image))
    
    # Enhanced validation
    validation_metrics = self.validate_music_notation(
        omr_results.get('staff_positions', []),
        img_array
    )
    
    # Save comprehensive results
    analysis_results = {
        "timestamp": self.timestamp,
        "processing_time": time.time() - start_time,
        "validation_metrics": validation_metrics,
        "omr_results": omr_results,
        "performance_metrics": {
            "memory_usage": sys.getsizeof(omr_results),
            "processing_speed": validation_metrics["total_area"] / (time.time() - start_time)
        }
    }
    
    with open(self.debug_dir / f"comprehensive_analysis_{self.timestamp}.json", 'w') as f:
        json.dump(analysis_results, f, indent=2)
    
    self.logger.info(f"Comprehensive analysis completed in {time.time() - start_time:.2f} seconds")
    
    # Final assertions
    self.assertTrue(validation_metrics["num_regions"] > 0)
    self.assertTrue(analysis_results["processing_time"] < 60)  # Should process within 60 seconds

unittest.main(verbosity=2)
