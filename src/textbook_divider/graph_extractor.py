import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import networkx as nx
import logging
from PIL import Image
import pytesseract
import re

@dataclass
class GraphNode:
	"""Represents a node in a mathematical graph"""
	id: int
	position: Tuple[int, int]
	label: str
	type: str  # 'pitch_class', 'interval', 'transformation'
	properties: Dict[str, any]

@dataclass
class GraphEdge:
	"""Represents an edge in a mathematical graph"""
	source: int
	target: int
	label: str
	type: str  # 'arrow', 'line', 'double_arrow'
	properties: Dict[str, any]

class GraphExtractor:
	"""Extract mathematical graphs from images with specialized handling for music theory notation"""
	
	def __init__(self):
		self.logger = logging.getLogger(__name__)
		self._init_detectors()

	def _init_detectors(self):
		"""Initialize specialized detectors for mathematical notation"""
		self.arrow_templates = self._load_arrow_templates()
		self.node_templates = self._load_node_templates()
	
	def extract_graph(self, image: np.ndarray) -> Tuple[List[GraphNode], List[GraphEdge]]:
		"""Extract graph structure from image"""
		processed = self._preprocess_image(image)
		nodes = self._detect_nodes(processed)
		edges = self._detect_edges(processed, nodes)
		self._extract_mathematical_labels(processed, nodes, edges)
		return nodes, edges

	def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
		"""Preprocess image for better graph detection"""
		gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
		_, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
		return thresh

	def _detect_nodes(self, image: np.ndarray) -> List[GraphNode]:
		"""Detect nodes and their types"""
		nodes = []
		circles = cv2.HoughCircles(image, cv2.HOUGH_GRADIENT, 1, 20,
								 param1=50, param2=30, minRadius=10, maxRadius=30)
		
		if circles is not None:
			circles = np.uint16(np.around(circles))
			for i, circle in enumerate(circles[0, :]):
				x, y, r = circle
				label = self._extract_node_label(image, (x, y, r))
				nodes.append(GraphNode(
					id=i,
					position=(int(x), int(y)),
					label=label,
					type=self._determine_node_type(image, (x, y, r)),
					properties={'radius': int(r)}
				))
		return nodes

	def _detect_edges(self, image: np.ndarray, nodes: List[GraphNode]) -> List[GraphEdge]:
		"""Detect edges and their types"""
		edges = []
		lines = cv2.HoughLinesP(image, 1, np.pi/180, 50, minLineLength=30, maxLineGap=10)
		
		if lines is not None:
			for i, line in enumerate(lines):
				x1, y1, x2, y2 = line[0]
				source_node = self._find_closest_node((x1, y1), nodes)
				target_node = self._find_closest_node((x2, y2), nodes)
				
				if source_node and target_node:
					edge_type = self._determine_edge_type(image, (x1, y1, x2, y2))
					label = self._extract_edge_label(image, (x1, y1, x2, y2))
					edges.append(GraphEdge(
						source=source_node.id,
						target=target_node.id,
						label=label,
						type=edge_type,
						properties={'coords': (x1, y1, x2, y2)}
					))
		return edges

	def _extract_mathematical_labels(self, image: np.ndarray, nodes: List[GraphNode], edges: List[GraphEdge]):
		"""Extract and interpret mathematical notation from labels"""
		for node in nodes:
			x, y = node.position
			roi = self._get_label_roi(image, x, y)
			if roi is not None:
				label = pytesseract.image_to_string(roi, config='--psm 6')
				node.label = self._interpret_mathematical_notation(label)
		
		for edge in edges:
			x1, y1, x2, y2 = edge.properties['coords']
			roi = self._get_edge_label_roi(image, x1, y1, x2, y2)
			if roi is not None:
				label = pytesseract.image_to_string(roi, config='--psm 6')
				edge.label = self._interpret_mathematical_notation(label)

	def _interpret_mathematical_notation(self, text: str) -> str:
		"""Interpret mathematical notation in extracted text"""
		try:
			# Common music theory transformations
			transformations = {
				'T(\d+)': lambda m: f'T{m.group(1)}',  # Transposition
				'I(\d*)': lambda m: f'I{m.group(1)}',   # Inversion
				'R(\d*)': lambda m: f'R{m.group(1)}',   # Retrograde
				'M(\d+)': lambda m: f'M{m.group(1)}',   # Multiplication
				'P(\d*)': lambda m: f'P{m.group(1)}'    # Pitch class
			}
			
			# Clean and normalize text
			text = text.strip().replace(' ', '')
			
			# Apply transformation patterns
			for pattern, handler in transformations.items():
				match = re.search(pattern, text)
				if match:
					return handler(match)
			
			return text
		except Exception as e:
			self.logger.error(f"Error interpreting mathematical notation: {e}")
			return text

	def _find_closest_node(self, point: Tuple[int, int], nodes: List[GraphNode]) -> Optional[GraphNode]:
		"""Find the closest node to a given point"""
		if not nodes:
			return None
		closest = min(nodes, key=lambda n: 
			((n.position[0] - point[0]) ** 2 + (n.position[1] - point[1]) ** 2) ** 0.5)
		return closest

	def _determine_node_type(self, image: np.ndarray, circle: Tuple[int, int, int]) -> str:
		"""Determine the type of node based on its visual characteristics"""
		return 'pitch_class'  # Default type

	def _determine_edge_type(self, image: np.ndarray, line: Tuple[int, int, int, int]) -> str:
		"""Determine the type of edge based on its visual characteristics"""
		return 'arrow'  # Default type

	def _load_arrow_templates(self) -> List[np.ndarray]:
		"""Load arrow templates for matching"""
		return []

	def _load_node_templates(self) -> List[np.ndarray]:
		"""Load node templates for matching"""
		return []

	def _extract_node_label(self, image: np.ndarray, circle: Tuple[int, int, int]) -> str:
		"""Extract label from node region"""
		x, y, r = circle
		padding = int(r * 0.5)
		roi = image[y-r-padding:y+r+padding, x-r-padding:x+r+padding]
		if roi.size == 0:
			return ""
		return pytesseract.image_to_string(roi, config='--psm 6')

	def _extract_edge_label(self, image: np.ndarray, line: Tuple[int, int, int, int]) -> str:
		"""Extract label from edge region"""
		x1, y1, x2, y2 = line
		mid_x = (x1 + x2) // 2
		mid_y = (y1 + y2) // 2
		padding = 20
		roi = image[mid_y-padding:mid_y+padding, mid_x-padding:mid_x+padding]
		if roi.size == 0:
			return ""
		return pytesseract.image_to_string(roi, config='--psm 6')

	def _get_label_roi(self, image: np.ndarray, x: int, y: int) -> Optional[np.ndarray]:
		"""Get region of interest for label extraction"""
		padding = 20
		h, w = image.shape[:2]
		x1, y1 = max(0, x-padding), max(0, y-padding)
		x2, y2 = min(w, x+padding), min(h, y+padding)
		roi = image[y1:y2, x1:x2]
		return roi if roi.size > 0 else None

	def _get_edge_label_roi(self, image: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> Optional[np.ndarray]:
		"""Get region of interest for edge label extraction"""
		mid_x = (x1 + x2) // 2
		mid_y = (y1 + y2) // 2
		padding = 20
		h, w = image.shape[:2]
		roi_x1, roi_y1 = max(0, mid_x-padding), max(0, mid_y-padding)
		roi_x2, roi_y2 = min(w, mid_x+padding), min(h, mid_y+padding)
		roi = image[roi_y1:roi_y2, roi_x1:roi_x2]
		return roi if roi.size > 0 else None
