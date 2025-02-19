import gc
import cv2
import numpy as np
from pathlib import Path
import fitz  # PyMuPDF
import logging
from typing import Dict, List, Tuple, Optional, Any
import json
import subprocess
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
import time
import psutil
from pdf2image import convert_from_path

class OMRProcessor:
    def __init__(self, cache_dir: Optional[Path] = None):
        self.logger = logging.getLogger(__name__)
        self.cache_dir = cache_dir or Path.home() / '.cache/textbook-divider/omr'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Find Audiveris installation
        self.audiveris_path = self._find_audiveris()
        if not self.audiveris_path:
            self.logger.warning('Audiveris not found, falling back to template matching')
        
        # Load templates for fallback
        self.templates_dir = Path(__file__).parent / 'templates'
        self.templates = self._load_templates()
        
        # Initialize thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=4)

    def _find_audiveris(self) -> Optional[str]:
        """Find Audiveris installation with expanded search paths"""
        try:
            # Check project-specific installation first
            project_audiveris = Path(__file__).parent.parent.parent / 'external' / 'audiveris'
            for version_dir in project_audiveris.glob('**/bin/Audiveris'):
                if version_dir.is_file() and os.access(version_dir, os.X_OK):
                    return str(version_dir)

            # Check common system paths
            common_paths = [
                '/usr/bin/Audiveris',
                '/usr/local/bin/Audiveris',
                '/opt/Audiveris/bin/Audiveris',
                str(Path.home() / 'Audiveris/bin/Audiveris')
            ]
            for path in common_paths:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    return path
            
            # Try which command
            result = subprocess.run(['which', 'Audiveris'], 
                                 capture_output=True, text=True)
            if result.returncode == 0:
                path = result.stdout.strip()
                if os.access(path, os.X_OK):
                    return path
        except Exception as e:
            self.logger.warning(f'Error finding Audiveris: {e}')
        return None

    def _generate_templates(self, category: str, names: List[str]) -> List[np.ndarray]:
        """Generate templates programmatically using OpenCV"""
        templates = []
        for name in names:
            # Create a blank image
            img = np.zeros((50, 50), dtype=np.uint8)
            
            # Add text to the image
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(img, name, (10, 30), font, 0.7, 255, 2, cv2.LINE_AA)
            
            templates.append(img)
        return templates

    def _load_templates(self) -> Dict[str, List[np.ndarray]]:
        templates = {}
        for category in ['notes', 'clefs', 'time_signatures', 'accidentals']:
            templates[category] = []
            category_dir = self.templates_dir / category
            if category_dir.exists():
                for template_path in category_dir.glob('*.png'):
                    template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
                    if template is not None:
                        templates[category].append(template)
            else:
                # Generate templates if directory doesn't exist
                if category == 'notes':
                    template_names = ['quarter_note', 'eighth_note', 'whole_note']
                elif category == 'clefs':
                    template_names = ['treble_clef', 'bass_clef']
                elif category == 'time_signatures':
                    template_names = ['4_4', '3_4', '2_4']
                elif category == 'accidentals':
                    template_names = ['sharp', 'flat', 'natural']
                else:
                    template_names = []
                
                generated_templates = self._generate_templates(category, template_names)
                templates[category] = generated_templates

        return templates

    def detect_staves(self, image: np.ndarray) -> List[List[int]]:
        if len(image.shape) > 2:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        binary_small = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY_INV, 15, 2)
        binary_large = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY_INV, 25, 2)
        binary = cv2.bitwise_and(binary_small, binary_large)
        
        staff_positions = []
        for scale in [0.8, 1.0, 1.2]:
            scaled = cv2.resize(binary, None, fx=scale, fy=scale)
            horizontal = np.copy(scaled)
            cols = horizontal.shape[1]
            horizontal_size = cols // 30
            
            for kernel_size in [horizontal_size, horizontal_size//2]:
                horizontalStructure = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, 1))
                horizontal = cv2.erode(horizontal, horizontalStructure)
                horizontal = cv2.dilate(horizontal, horizontalStructure)
                
                positions = self._find_staff_positions(horizontal, scale)
                if positions:
                    staff_positions.extend(positions)
        
        return self._clean_staff_positions(staff_positions)

    def _find_staff_positions(self, horizontal: np.ndarray, scale: float) -> List[List[int]]:
        positions = []
        rows = horizontal.shape[0]
        row_sums = np.sum(horizontal, axis=1)
        
        # Use dynamic thresholding
        mean_sum = np.mean(row_sums)
        std_sum = np.std(row_sums)
        threshold = mean_sum + std_sum
        
        # Find peaks in row sums
        peaks = []
        for i in range(1, rows-1):
            if (row_sums[i] > threshold and 
                row_sums[i] >= row_sums[i-1] and 
                row_sums[i] >= row_sums[i+1]):
                peaks.append(i)
        
        # Group peaks into staves
        staff_spacing = 10  # Expected spacing between staff lines
        tolerance = 2       # Tolerance for spacing variation
        
        current_staff = []
        for peak in peaks:
            if not current_staff:
                current_staff.append(peak)
            else:
                spacing = peak - current_staff[-1]
                if staff_spacing - tolerance <= spacing <= staff_spacing + tolerance:
                    current_staff.append(peak)
                else:
                    if len(current_staff) == 5:
                        scaled_staff = [int(pos / scale) for pos in current_staff]
                        positions.append(scaled_staff)
                    current_staff = [peak]
        
        if len(current_staff) == 5:
            scaled_staff = [int(pos / scale) for pos in current_staff]
            positions.append(scaled_staff)
        
        return positions

    def _clean_staff_positions(self, positions: List[List[int]]) -> List[List[int]]:
        if not positions:
            return []
            
        unique_positions = {tuple(staff) for staff in positions}
        cleaned = [list(staff) for staff in unique_positions]
        cleaned.sort(key=lambda x: x[0])
        
        merged = []
        current = cleaned[0]
        
        for next_staff in cleaned[1:]:
            if abs(current[0] - next_staff[0]) < 5:
                current = [(a + b) // 2 for a, b in zip(current, next_staff)]
            else:
                merged.append(current)
                current = next_staff
        
        merged.append(current)
        return merged

    def detect_symbols(self, image: np.ndarray, staff_positions: List[List[int]]) -> Dict[str, float]:
        if len(image.shape) > 2:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        results = {
            'notes': 0.0,
            'clefs': 0.0,
            'time_signatures': 0.0,
            'accidentals': 0.0
        }
        
        if not staff_positions:
            return results
        
        staff_heights = [staff[-1] - staff[0] for staff in staff_positions]
        avg_staff_height = sum(staff_heights) / len(staff_heights)
        staff_spacing = avg_staff_height / 4
        
        # Enhance image contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        for staff in staff_positions:
            staff_height = staff[-1] - staff[0]
            padding = int(staff_height * 1.5)
            top = max(0, staff[0] - padding)
            bottom = min(enhanced.shape[0], staff[-1] + padding)
            staff_region = enhanced[top:bottom, :]
            
            # Apply adaptive thresholding
            binary = cv2.adaptiveThreshold(staff_region, 255,
                                         cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                         cv2.THRESH_BINARY_INV, 15, 2)
            
            region_height, region_width = binary.shape
            
            for category, templates in self.templates.items():
                max_confidence = 0.0
                
                for template in templates:
                    try:
                        template_binary = cv2.adaptiveThreshold(template, 255,
                                                              cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                              cv2.THRESH_BINARY_INV, 15, 2)
                        
                        # Calculate maximum allowed template size
                        max_template_height = region_height // 2
                        max_template_width = region_width // 2
                        
                        # Calculate template size relative to staff height
                        template_height = int(staff_height * 0.8)
                        aspect_ratio = template.shape[1] / template.shape[0]
                        template_width = int(template_height * aspect_ratio)
                        
                        # Ensure template is not too large
                        if template_height > max_template_height:
                            scale = max_template_height / template_height
                            template_height = max_template_height
                            template_width = int(template_width * scale)
                        
                        if template_width > max_template_width:
                            scale = max_template_width / template_width
                            template_width = max_template_width
                            template_height = int(template_height * scale)
                        
                        # Skip if template dimensions are invalid
                        if template_width <= 0 or template_height <= 0:
                            self.logger.warning(f"Invalid template dimensions for {category}: {template_width}x{template_height}")
                            continue
                            
                        # Resize template to calculated size
                        scaled_template = cv2.resize(template_binary, (template_width, template_height))
                        
                        # Only attempt rotation if template is smaller than region
                        if scaled_template.shape[0] < region_height and scaled_template.shape[1] < region_width:
                            for angle in [-5, -2, 0, 2, 5]:
                                try:
                                    if angle != 0:
                                        matrix = cv2.getRotationMatrix2D(
                                            (scaled_template.shape[1]/2, scaled_template.shape[0]/2),
                                            angle, 1.0)
                                        rotated = cv2.warpAffine(scaled_template, matrix, 
                                                               (template_width, template_height))
                                    else:
                                        rotated = scaled_template
                                    
                                    result = cv2.matchTemplate(binary, rotated, cv2.TM_CCOEFF_NORMED)
                                    confidence = np.max(result)
                                    max_confidence = max(max_confidence, confidence)
                                except Exception as e:
                                    self.logger.warning(f"Rotation failed for {category} at angle {angle}: {str(e)}")
                                    continue
                        else:
                            self.logger.warning(f"Template too large for region: {scaled_template.shape} vs {(region_height, region_width)}")
                    
                    except Exception as e:
                        self.logger.warning(f"Template matching failed for {category}: {str(e)}")
                        continue
                
                # Apply confidence boost for expected symbol locations
                if category == 'clefs' and max_confidence > 0.3:
                    max_confidence *= 1.5  # Boost clef detection at staff start
                
                results[category] = max(results[category], 
                                      max_confidence * (staff_height / avg_staff_height))
        
        return results

    def process_page(self, image_path: str) -> Dict[str, Any]:
        try:
            # Try Audiveris first if available
            if self.audiveris_path:
                result = self._process_with_audiveris(image_path)
                if result['success']:
                    return result
                self.logger.info('Falling back to template matching after Audiveris failure')
            
            # Try template matching
            result = self._process_with_template_matching(image_path)
            if not result['success'] or not result.get('has_music', False):
                self.logger.info('Attempting enhanced preprocessing')
                result = self._process_with_enhanced_preprocessing(image_path)
            
            # Lower confidence threshold for template matching
            if result['success']:
                symbol_conf = result.get('symbol_confidence', {})
                result['has_music'] = any(conf > 0.3 for conf in symbol_conf.values())
            
            return result
            
        except Exception as e:
            self.logger.error(f'Processing error: {str(e)}')
            return {
                'success': False,
                'has_music': False,
                'error': str(e),
                'recovery_attempted': True
            }


    def _process_with_enhanced_preprocessing(self, image_path: str) -> Dict[str, Any]:
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError('Failed to load image')
            
            # Enhanced preprocessing pipeline
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # Add bilateral filtering for better edge preservation
            bilateral = cv2.bilateralFilter(denoised, 9, 75, 75)
            
            # Multiple CLAHE passes with different parameters
            clahe1 = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced1 = clahe1.apply(bilateral)
            
            clahe2 = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(16,16))
            enhanced2 = clahe2.apply(bilateral)
            
            # Combine enhancements
            enhanced = cv2.addWeighted(enhanced1, 0.6, enhanced2, 0.4, 0)
            
            # Add adaptive thresholding
            binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                         cv2.THRESH_BINARY_INV, 15, 2)
            
            temp_path = f'{image_path}_enhanced.png'
            cv2.imwrite(temp_path, binary)
            
            result = self._process_with_template_matching(temp_path)
            
            os.remove(temp_path)
            
            return result
            
        except Exception as e:
            self.logger.error(f'Enhanced preprocessing failed: {str(e)}')
            return {
                'success': False,
                'has_music': False,
                'error': f'Enhanced preprocessing failed: {str(e)}',
                'recovery_attempted': True
            }

    def _process_with_audiveris(self, image_path: str) -> Dict[str, Any]:
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir)
                cmd = [
                    self.audiveris_path,
                    '-batch',
                    '-output', str(output_dir),
                    '-export', 'json',
                    '-option', 'org.audiveris.omr.score.ScoreParameters.minDurationDivisor=32',
                    '-option', 'org.audiveris.omr.sheet.SheetParameters.binarizationFilter=adaptive',
                    image_path
                ]
                process = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if process.returncode != 0:
                    self.logger.warning(f'Audiveris failed: {process.stderr}')
                    return {
                        'success': False,
                        'has_music': False,
                        'engine': 'audiveris',
                        'error': process.stderr
                    }
                    
                json_file = next(output_dir.glob('*.json'), None)
                if not json_file:
                    raise FileNotFoundError('No Audiveris output found')
                    
                with open(json_file) as f:
                    data = json.load(f)
                    
                return {
                    'success': True,
                    'has_music': True,
                    'engine': 'audiveris',
                    'data': data,
                    'error': None
                }
        except Exception as e:
            self.logger.error(f'Audiveris processing error: {str(e)}')
            return {
                'success': False,
                'has_music': False,
                'engine': 'audiveris',
                'error': str(e)
            }

    def _process_with_template_matching(self, image_path: str) -> Dict[str, Any]:
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError('Failed to load image')
            staff_positions = self.detect_staves(image)
            symbol_confidence = self.detect_symbols(image, staff_positions)
            has_music = any(conf > 0.5 for conf in symbol_confidence.values())  # Lower threshold for music detection
            return {
                'success': True,
                'has_music': has_music,
                'engine': 'template_matching',
                'staff_positions': staff_positions,
                'symbol_confidence': symbol_confidence,
                'error': None
            }
        except Exception as e:
            self.logger.error(f'Template matching error: {str(e)}')
            return {
                'success': False,
                'has_music': False,
                'engine': 'template_matching',
                'error': str(e),
                'staff_positions': [],
                'symbol_confidence': {}
            }

    def analyze_results(self, output_dir: Path) -> Dict[str, Any]:
        """Analyze OMR results from a processed directory"""
        results = {
            "staff_accuracy": 0.0,
            "note_accuracy": 0.0,
            "mixed_content_quality": 0.0,
            "engine": "unknown",
            "staff_positions": [],
            "raw_confidence": {},
            "recoveries": []
        }
        
        try:
            # Look for section metrics
            metrics_file = output_dir / "section_metrics.json"
            if metrics_file.exists():
                with open(metrics_file) as f:
                    metrics = json.load(f)
                    results["staff_accuracy"] = metrics.get("staff_accuracy", 0.0)
                    results["note_accuracy"] = metrics.get("note_accuracy", 0.0)
                    results["mixed_content_quality"] = metrics.get("mixed_content_quality", 0.0)
            
            # Analyze all PNG files in directory for music notation
            for img_file in output_dir.glob("*.png"):
                try:
                    page_result = self.process_page(str(img_file))
                    if page_result.get("has_music", False):
                        results["staff_positions"].extend(page_result.get("staff_positions", []))
                        
                        # Update confidence scores
                        symbol_conf = page_result.get("symbol_confidence", {})
                        for key, value in symbol_conf.items():
                            if key not in results["raw_confidence"]:
                                results["raw_confidence"][key] = []
                            results["raw_confidence"][key].append(value)
                        
                        if page_result.get("engine"):
                            results["engine"] = page_result["engine"]
                        
                        if page_result.get("recovery_attempted", False):
                            results["recoveries"].append({
                                "file": img_file.name,
                                "engine": page_result.get("engine")
                            })
                except Exception as e:
                    self.logger.warning(f"Error analyzing {img_file}: {str(e)}")
                    continue
            
            # Average confidence scores
            for key in results["raw_confidence"]:
                if results["raw_confidence"][key]:
                    results["raw_confidence"][key] = sum(results["raw_confidence"][key]) / len(results["raw_confidence"][key])
                else:
                    results["raw_confidence"][key] = 0.0
            
            # Calculate overall accuracies if not already set
            if results["staff_accuracy"] == 0.0 and results["raw_confidence"]:
                results["staff_accuracy"] = results["raw_confidence"].get("clefs", 0.0) * 0.7 + \
                                          results["raw_confidence"].get("notes", 0.0) * 0.3
            
            if results["note_accuracy"] == 0.0 and results["raw_confidence"]:
                results["note_accuracy"] = results["raw_confidence"].get("notes", 0.0)
            
            if results["mixed_content_quality"] == 0.0 and results["raw_confidence"]:
                results["mixed_content_quality"] = sum(results["raw_confidence"].values()) / len(results["raw_confidence"])
            
        except Exception as e:
            self.logger.error(f"Error analyzing results: {str(e)}")
        
        return results

    def process_book(self, book_path: str, output_path: str) -> Dict[str, Any]:
        """Process an entire book with OMR and save results"""
        try:
            start_time = time.time()
            results = {
                "success": True,
                "musical_notation": [],
                "chapters": [],
                "errors": [],
                "recoveries": [],
                "processing_time": 0,
                "memory_usage": 0
            }
            
            # Process book in batches
            batch_size = 10  # Process 10 pages at a time
            
            # Get total pages first
            doc = fitz.open(book_path)
            total_pages = doc.page_count
            doc.close()
            
            # Process in batches
            for start_page in range(0, total_pages, batch_size):
                end_page = min(start_page + batch_size, total_pages)
                
                # Convert batch of pages
                pages = convert_from_path(
                    book_path,
                    first_page=start_page + 1,
                    last_page=end_page
                )
                
                # Process each page in batch
                for i, page in enumerate(pages):
                    page_num = start_page + i
                    temp_path = f"{output_path}_temp_{page_num}.png"
                    
                    try:
                        # Save and process page
                        page.save(temp_path)
                        page_result = self.process_page(temp_path)
                        
                        # Track results
                        if page_result.get("has_music", False):
                            results["musical_notation"].append({
                                "page": page_num + 1,
                                "staff_positions": page_result.get("staff_positions", []),
                                "symbol_confidence": page_result.get("symbol_confidence", {})
                            })
                        
                        if not page_result["success"]:
                            results["errors"].append({
                                "page": page_num + 1,
                                "error": page_result.get("error")
                            })
                        
                        if page_result.get("recovery_attempted", False):
                            results["recoveries"].append({
                                "page": page_num + 1,
                                "engine": page_result.get("engine")
                            })
                    
                    finally:
                        # Cleanup temp file
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                
                # Force garbage collection between batches
                gc.collect()
            
            # Add performance metrics
            results["processing_time"] = time.time() - start_time
            results["memory_usage"] = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            return results
            
        except Exception as e:
            self.logger.error(f"Book processing error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "musical_notation": [],
                "chapters": [],
                "errors": [{"error": str(e)}],
                "recoveries": [],
                "processing_time": 0,
                "memory_usage": 0
            }
