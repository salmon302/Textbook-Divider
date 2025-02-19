from typing import List, Dict, Optional, Tuple
import numpy as np
from .graph_types import Node, Edge, NodeType, MusicTheoryGraph

class GeometricParser:
	def __init__(self):
		self.geometric_types = {
			'point': {'pattern': r'\((-?\d+\.?\d*),\s*(-?\d+\.?\d*)\)'},
			'vector': {'pattern': r'<(-?\d+\.?\d*),\s*(-?\d+\.?\d*)>'},
			'transformation': {'pattern': r'T\[([^\]]+)\]'}
		}
		
	def parse_geometric_elements(self, text: str) -> MusicTheoryGraph:
		graph = MusicTheoryGraph()
		
		# Parse geometric points
		points = self._extract_points(text)
		for i, (x, y) in enumerate(points):
			node = Node(
				id=f"point_{i}",
				type=NodeType.GEOMETRIC_POINT,
				label=f"({x}, {y})",
				properties={
					'coordinates': (x, y),
					'type': 'point'
				},
				position=(float(x), float(y))
			)
			graph.add_node(node)
			
		# Parse transformations
		transformations = self._extract_transformations(text)
		for i, transform_matrix in enumerate(transformations):
			node = Node(
				id=f"transform_{i}",
				type=NodeType.TRANSFORMATION,
				label=f"T{i}",
				properties={
					'matrix': transform_matrix,
					'type': 'geometric_transformation'
				}
			)
			graph.add_node(node)
			
		# Connect related geometric elements
		self._connect_geometric_elements(graph)
		
		return graph
		
	def _extract_points(self, text: str) -> List[Tuple[float, float]]:
		import re
		points = []
		pattern = self.geometric_types['point']['pattern']
		matches = re.finditer(pattern, text)
		for match in matches:
			x, y = float(match.group(1)), float(match.group(2))
			points.append((x, y))
		return points
		
	def _extract_transformations(self, text: str) -> List[np.ndarray]:
		import re
		transformations = []
		pattern = self.geometric_types['transformation']['pattern']
		matches = re.finditer(pattern, text)
		for match in matches:
			matrix_str = match.group(1)
			# Parse matrix string to numpy array
			matrix = np.array([
				[float(x) for x in row.split()]
				for row in matrix_str.split(';')
			])
			transformations.append(matrix)
		return transformations
		
	def _connect_geometric_elements(self, graph: MusicTheoryGraph) -> None:
		points = [n for n in graph.nodes.values() if n.type == NodeType.GEOMETRIC_POINT]
		transforms = [n for n in graph.nodes.values() if n.type == NodeType.TRANSFORMATION]
		
		# Connect points that are related through transformations
		for transform in transforms:
			matrix = transform.properties['matrix']
			for point in points:
				coords = point.properties['coordinates']
				transformed = np.dot(matrix, np.array([coords[0], coords[1], 1]))
				
				# Find if there's a point that matches the transformation
				for target in points:
					target_coords = target.properties['coordinates']
					if np.allclose(transformed[:2], target_coords):
						edge = Edge(
							source=point.id,
							target=target.id,
							label=transform.label,
							properties={'transformation_id': transform.id}
						)
						graph.add_edge(edge)