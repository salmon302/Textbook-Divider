import numpy as np
from typing import List, Dict, Tuple, Optional
import cv2
from .graph_types import Node, Edge, NodeType, MusicTheoryGraph

class DiagramParser:
	def __init__(self):
		self.shape_templates = {
			'circle': np.array([[0, 1, 0],
							  [1, 1, 1],
							  [0, 1, 0]], dtype=np.uint8),
			'square': np.array([[1, 1, 1],
							  [1, 1, 1],
							  [1, 1, 1]], dtype=np.uint8)
		}
		
	def parse_geometric_diagram(self, image: np.ndarray) -> MusicTheoryGraph:
		graph = MusicTheoryGraph()
		
		# Preprocess image
		processed = self._preprocess_image(image)
		
		# Detect shapes and points
		shapes = self._detect_shapes(processed)
		points = self._detect_points(processed)
		lines = self._detect_lines(processed)
		
		# Convert detected elements to graph
		self._shapes_to_nodes(shapes, graph)
		self._points_to_nodes(points, graph)
		self._lines_to_edges(lines, graph)
		
		return graph
		
	def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
		# Convert to grayscale
		gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
		# Apply threshold
		_, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
		# Remove noise
		kernel = np.ones((3,3), np.uint8)
		cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
		return cleaned
		
	def _detect_shapes(self, image: np.ndarray) -> List[Dict]:
		shapes = []
		contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, 
									 cv2.CHAIN_APPROX_SIMPLE)
		
		for contour in contours:
			# Get shape properties
			area = cv2.contourArea(contour)
			if area < 100:  # Filter out noise
				continue
				
			center = cv2.moments(contour)
			if center['m00'] != 0:
				cx = int(center['m10']/center['m00'])
				cy = int(center['m01']/center['m00'])
				
				shape = {
					'type': self._classify_shape(contour),
					'center': (cx, cy),
					'area': area,
					'contour': contour
				}
				shapes.append(shape)
				
		return shapes
		
	def _detect_points(self, image: np.ndarray) -> List[Tuple[int, int]]:
		points = []
		# Use template matching for small circular points
		result = cv2.matchTemplate(image, self.shape_templates['circle'], 
								 cv2.TM_CCOEFF_NORMED)
		locations = np.where(result >= 0.8)
		for pt in zip(*locations[::-1]):
			points.append(pt)
		return points
		
	def _detect_lines(self, image: np.ndarray) -> List[Dict]:
		lines = []
		detected_lines = cv2.HoughLinesP(image, 1, np.pi/180, 50, 
									   minLineLength=100, maxLineGap=10)
		
		if detected_lines is not None:
			for line in detected_lines:
				x1, y1, x2, y2 = line[0]
				lines.append({
					'start': (x1, y1),
					'end': (x2, y2),
					'length': np.sqrt((x2-x1)**2 + (y2-y1)**2)
				})
		return lines
		
	def _classify_shape(self, contour) -> str:
		# Approximate the contour to a polygon
		epsilon = 0.04 * cv2.arcLength(contour, True)
		approx = cv2.approxPolyDP(contour, epsilon, True)
		
		# Classify based on number of vertices
		num_vertices = len(approx)
		if num_vertices == 3:
			return 'triangle'
		elif num_vertices == 4:
			return 'square'
		else:
			return 'circle'
			
	def _shapes_to_nodes(self, shapes: List[Dict], 
						graph: MusicTheoryGraph) -> None:
		for i, shape in enumerate(shapes):
			node = Node(
				id=f"shape_{i}",
				type=NodeType.GEOMETRIC_POINT,
				label=f"{shape['type']}_{i}",
				properties={
					'shape_type': shape['type'],
					'area': shape['area'],
					'center': shape['center']
				},
				position=shape['center']
			)
			graph.add_node(node)
			
	def _points_to_nodes(self, points: List[Tuple[int, int]], 
						graph: MusicTheoryGraph) -> None:
		for i, point in enumerate(points):
			node = Node(
				id=f"point_{i}",
				type=NodeType.GEOMETRIC_POINT,
				label=f"P_{i}",
				properties={'type': 'point'},
				position=point
			)
			graph.add_node(node)
			
	def _lines_to_edges(self, lines: List[Dict], 
					   graph: MusicTheoryGraph) -> None:
		for i, line in enumerate(lines):
			# Find nodes close to line endpoints
			start_node = self._find_closest_node(line['start'], graph)
			end_node = self._find_closest_node(line['end'], graph)
			
			if start_node and end_node:
				edge = Edge(
					source=start_node.id,
					target=end_node.id,
					label=f"line_{i}",
					properties={
						'length': line['length'],
						'type': 'geometric_connection'
					}
				)
				graph.add_edge(edge)
				
	def _find_closest_node(self, point: Tuple[int, int], 
						  graph: MusicTheoryGraph, 
						  threshold: int = 10) -> Optional[Node]:
		closest_node = None
		min_dist = float('inf')
		
		for node in graph.nodes.values():
			if node.position:
				dist = np.sqrt((point[0] - node.position[0])**2 + 
							 (point[1] - node.position[1])**2)
				if dist < min_dist and dist < threshold:
					min_dist = dist
					closest_node = node
					
		return closest_node