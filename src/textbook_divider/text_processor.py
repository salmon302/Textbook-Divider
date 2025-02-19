import re
import logging
import cv2
import numpy as np
from PIL import Image
import pytesseract
from dataclasses import dataclass
from typing import List, Dict, Pattern, Tuple, Any
from .graph_extractor import GraphExtractor, GraphNode, GraphEdge

@dataclass
class TextBlock:
	"""Represents a block of text with its type"""
	content: str
	block_type: str  # 'paragraph', 'list', 'quote', 'code'

class TextProcessor:
	"""Process and clean text while preserving formatting"""
	
	def __init__(self):
		self.logger = logging.getLogger(__name__)
		self._compile_patterns()
		self.graph_extractor = GraphExtractor()

	
	def _compile_patterns(self):
		"""Compile regex patterns for text processing"""
		self.patterns = {
			'math': re.compile(r'\$[^$]+\$'),
			'list': re.compile(r'^[\s]*[•\-\*]\s+|^\s*\d+\.\s+', re.MULTILINE),
			'quote': re.compile(r'^\s*>\s+', re.MULTILINE),
			'code': re.compile(r'```[\w]*\n.*?```', re.MULTILINE | re.DOTALL),
			'table': re.compile(r'\|[^|]+\|')
		}

	
	def clean_text(self, text: str) -> str:
		"""Clean and format text while preserving structure"""
		# Remove page header/footer artifacts
		text = self._remove_header_footer(text)
		
		# Handle split words and lines
		text = self._handle_split_content(text)
		
		blocks = self._split_into_blocks(text)
		processed_blocks = [self._process_block(block) for block in blocks]
		return '\n\n'.join(block.content for block in processed_blocks)

	def _remove_header_footer(self, text: str) -> str:
		"""Remove common header/footer artifacts"""
		# Remove repeated chapter titles
		text = re.sub(r'(?:iil|III?|ll)\s+THE\s+MOTIVE\s*\d*\s*=?\.?', 'THE MOTIVE', text)
		
		# Remove page numbers and artifacts
		text = re.sub(r'\f|\v|\d+\s*$', '', text, flags=re.MULTILINE)
		return text

	def _handle_split_content(self, text: str) -> str:
		"""Handle split words and ensure proper content flow"""
		# Join hyphenated words split across lines
		text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
		
		# Fix common OCR artifacts in split content
		text = re.sub(r'(?<=\w)\s+(?=\w)', ' ', text)
		
		# Remove duplicate content from page splits
		lines = text.split('\n')
		cleaned_lines = []
		prev_line = ''
		
		for line in lines:
			# Skip if line is very similar to previous line (duplicate from page split)
			if self._similarity_ratio(line.strip(), prev_line.strip()) > 0.8:
				continue
			cleaned_lines.append(line)
			prev_line = line
		
		return '\n'.join(cleaned_lines)

	def _similarity_ratio(self, str1: str, str2: str) -> float:
		"""Calculate similarity ratio between two strings"""
		if not str1 or not str2:
			return 0.0
		
		# Simple length-based comparison for performance
		if abs(len(str1) - len(str2)) / max(len(str1), len(str2)) > 0.3:
			return 0.0
		
		# Character-based similarity
		matches = sum(a == b for a, b in zip(str1, str2))
		return matches / max(len(str1), len(str2))


	
	def _split_into_blocks(self, text: str) -> List[TextBlock]:
		"""Split text into blocks based on type"""
		blocks = []
		current_block = []
		current_type = 'paragraph'
		
		for line in text.split('\n'):
			line_type = self._determine_line_type(line)
			
			if line_type != current_type or not line.strip():
				if current_block:
					blocks.append(TextBlock(
						content='\n'.join(current_block),
						block_type=current_type
					))
					current_block = []
				current_type = line_type
			
			if line.strip():
				current_block.append(line)
		
		if current_block:
			blocks.append(TextBlock(
				content='\n'.join(current_block),
				block_type=current_type
			))
		
		return blocks

	def _determine_line_type(self, line: str) -> str:
		"""Determine the type of a line"""
		line = line.strip()
		if not line:
			return 'paragraph'
		if line.startswith('```'):
			return 'code'
		if line.startswith('|') and line.endswith('|'):
			return 'table'
		if self.patterns['list'].match(line):
			return 'list'
		if self.patterns['quote'].match(line):
			return 'quote'
		return 'paragraph'
	
	def _clean_list_item(self, content: str) -> str:
		"""Clean and format list items while preserving markers"""
		# Handle bullet points
		content = re.sub(r'^[•\-\*]\s+', '• ', content, flags=re.MULTILINE)
		
		# Handle numbered lists
		content = re.sub(r'^\d+\.\s+', lambda m: f"{m.group().strip()} ", content, flags=re.MULTILINE)
		
		# Clean extra whitespace while preserving list structure
		lines = [line.strip() for line in content.split('\n')]
		return '\n'.join(lines)

	def _process_block(self, block: TextBlock) -> TextBlock:
		"""Process individual text block based on its type"""
		if block.block_type in ['code', 'table']:
			# Don't modify code blocks or tables at all
			return block
		elif block.block_type == 'list':
			block.content = self._clean_list_item(block.content)
		elif block.block_type == 'quote':
			block.content = re.sub(r'^>\s*', '> ', block.content, flags=re.MULTILINE)
		else:  # paragraph
			block.content = ' '.join(line.strip() for line in block.content.splitlines())
		
		return block

	
	def _clean_paragraph(self, text: str) -> str:
		"""Clean and format paragraph text"""
		# Preserve line breaks for tables and special content
		if self.patterns['table'].search(text):
			return text.rstrip()
			
		# Convert newlines to spaces and remove excess whitespace
		text = ' '.join(line.strip() for line in text.splitlines())
		text = ' '.join(text.split())
		
		# Fix typographic characters
		text = self._fix_typography(text)
		
		# Wrap long lines
		if len(text) > self.max_line_length:
			text = self._wrap_text(text)
		
		return text
	
	def _fix_typography(self, text: str) -> str:
		"""Fix typographic characters and formatting"""
		replacements = {
			'...': '…',  # ellipsis
			'--': '—',   # em dash
			'<<': '«',   # guillemets
			'>>': '»',
			'(c)': '©',  # copyright
			'(r)': '®',  # registered
			'(tm)': '™'  # trademark
		}
		
		for old, new in replacements.items():
			text = text.replace(old, new)
		
		return text
	
	def _wrap_text(self, text: str, width: int = None) -> str:
		"""Wrap text to specified width while preserving structure"""
		if width is None:
			width = self.max_line_length
			
		words = text.split()
		lines = []
		current_line = []
		current_length = 0
		
		for word in words:
			word_length = len(word)
			if current_length + word_length + 1 <= width:
				current_line.append(word)
				current_length += word_length + 1
			else:
				lines.append(' '.join(current_line))
				current_line = [word]
				current_length = word_length
		
		if current_line:
			lines.append(' '.join(current_line))
		
		return '\n'.join(lines)
	
	def _clean_table(self, text: str) -> str:
		"""Clean and format table content"""
		lines = text.splitlines()
		return '\n'.join(line.rstrip() for line in lines)

	def _join_blocks(self, blocks: List[TextBlock]) -> str:
		"""Join processed blocks with appropriate spacing"""
		result = []
		for i, block in enumerate(blocks):
			# Add appropriate spacing between blocks
			if i > 0:
				prev_type = blocks[i-1].block_type
				curr_type = block.block_type
				
				# Handle special cases
				if curr_type == 'table' or prev_type == 'table':
					result.append('')
				elif curr_type == prev_type == 'paragraph':
					result.append('')
				elif curr_type in ['list', 'quote']:
					result.append('')
			
			# Add block content without trailing newline
			content = block.content.rstrip('\n')
			if block.block_type == 'table':
				# Preserve exact formatting for tables
				result.append(content)
			else:
				result.append(content)
		
		return '\n'.join(result)

	def extract_text_blocks(self, image_path: str) -> Tuple[List[Tuple[str, Tuple[int, int, int, int]]], List[Tuple[np.ndarray, Tuple[int, int, int, int]]]]:
		"""Extract text blocks and graph components from an image using OCR"""
		try:
			img = cv2.imread(image_path)
			gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
			_, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
			
			contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
			
			text_blocks = []
			graph_components = []
			for contour in contours:
				x, y, w, h = cv2.boundingRect(contour)
				if w > 10 and h > 10:
					roi = thresh[y:y+h, x:x+w]
					text = self.extract_text_from_roi(roi)
					if text:
						text_blocks.append((text, (x, y, w, h)))
					elif self.is_graph_component(img[y:y+h, x:x+w]):
						graph_components.append((img[y:y+h, x:x+w], (x, y, w, h)))
			return text_blocks, graph_components
		except Exception as e:
			self.logger.error(f"Error extracting text blocks: {e}")
			return [], []

	def extract_text_from_roi(self, roi: np.ndarray) -> str:
		"""Extract text from a region of interest using OCR"""
		try:
			pil_image = Image.fromarray(roi)
			text = pytesseract.image_to_string(pil_image, config='--psm 6')
			return text.strip()
		except Exception as e:
			self.logger.error(f"Error extracting text from ROI: {e}")
			return ""

	def is_graph_component(self, roi: np.ndarray) -> bool:
		"""Heuristic check to determine if a region of interest is a graph component"""
		gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
		edges = cv2.Canny(gray, 50, 150)
		lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, minLineLength=50, maxLineGap=10)
		if lines is not None and len(lines) > 2:
			return True
		return False

	def extract_graph_structure(self, graph_component: np.ndarray) -> Dict[str, Any]:
		"""Extract graph structure information (nodes, edges, relationships)"""
		try:
			# Convert to grayscale
			gray = cv2.cvtColor(graph_component, cv2.COLOR_BGR2GRAY)
			
			# Detect nodes (circles)
			circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, 20,
									 param1=50, param2=30, minRadius=10, maxRadius=30)
			
			# Detect edges (lines)
			edges = cv2.Canny(gray, 50, 150)
			lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, minLineLength=50, maxLineGap=10)
			
			# Build graph structure
			graph_data = {
				'nodes': [],
				'edges': [],
				'relationships': []
			}
			
			if circles is not None:
				circles = np.uint16(np.around(circles))
				for i in circles[0, :]:
					graph_data['nodes'].append({
						'x': int(i[0]),
						'y': int(i[1]),
						'radius': int(i[2])
					})
			
			if lines is not None:
				for line in lines:
					x1, y1, x2, y2 = line[0]
					graph_data['edges'].append({
						'start': (int(x1), int(y1)),
						'end': (int(x2), int(y2))
					})
			
			# Analyze relationships between nodes based on edge connections
			for edge in graph_data['edges']:
				start_node = self._find_closest_node(edge['start'], graph_data['nodes'])
				end_node = self._find_closest_node(edge['end'], graph_data['nodes'])
				if start_node is not None and end_node is not None:
					graph_data['relationships'].append({
						'from': start_node,
						'to': end_node
					})
			
			return graph_data
		except Exception as e:
			self.logger.error(f"Error extracting graph structure: {e}")
			return {}

	def _find_closest_node(self, point: Tuple[int, int], nodes: List[Dict[str, int]]) -> Dict[str, int]:
		"""Find the closest node to a given point"""
		if not nodes:
			return None
		
		closest = min(nodes, key=lambda n: 
			((n['x'] - point[0]) ** 2 + (n['y'] - point[1]) ** 2) ** 0.5)
		return closest

	def process_page(self, image: np.ndarray) -> Dict[str, Any]:
		"""Process a page and extract both text and graph content"""
		result = {
			'text_blocks': [],
			'graphs': []
		}
		
		# Extract text blocks and graph components
		text_blocks, graph_components = self.extract_text_blocks(image)
		result['text_blocks'] = text_blocks
		
		# Process each graph component
		for graph_img, bbox in graph_components:
			nodes, edges = self.graph_extractor.extract_graph(graph_img)
			result['graphs'].append({
				'bbox': bbox,
				'nodes': nodes,
				'edges': edges
			})
		
		return result