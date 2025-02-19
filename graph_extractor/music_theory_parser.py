from typing import List, Dict, Optional, Set
import re
from .graph_types import MusicTheoryGraph, Node, Edge, NodeType

class MusicTheoryParser:
	def __init__(self):
		self.pitch_class_pattern = r'(?:[A-G][#b]?)'
		self.interval_pattern = r'(?:P|M|m|A|d)\d+'
		self.set_class_pattern = r'\[(?:\d+(?:,\s*\d+)*)\]'
		self.transformation_pattern = r'T\d+|P|L|R|I\d*'
		
	def parse_text(self, text: str) -> MusicTheoryGraph:
		graph = MusicTheoryGraph()
		
		# Extract and create nodes for each type
		pitch_classes = self._extract_pitch_classes(text)
		intervals = self._extract_intervals(text)
		set_classes = self._extract_set_classes(text)
		transformations = self._extract_transformations(text)
		
		# Add nodes to graph
		self._add_pitch_class_nodes(graph, pitch_classes)
		self._add_interval_nodes(graph, intervals)
		self._add_set_class_nodes(graph, set_classes)
		self._add_transformation_nodes(graph, transformations)
		
		# Create edges based on relationships
		self._create_relationships(graph, text)
		
		return graph
		
	def _extract_pitch_classes(self, text: str) -> Set[str]:
		return set(re.findall(self.pitch_class_pattern, text))
		
	def _extract_intervals(self, text: str) -> Set[str]:
		return set(re.findall(self.interval_pattern, text))
		
	def _extract_set_classes(self, text: str) -> Set[str]:
		return set(re.findall(self.set_class_pattern, text))
		
	def _extract_transformations(self, text: str) -> Set[str]:
		return set(re.findall(self.transformation_pattern, text))
		
	def _add_pitch_class_nodes(self, graph: MusicTheoryGraph, 
							  pitch_classes: Set[str]) -> None:
		for pc in pitch_classes:
			node = Node(
				id=f"pc_{pc}",
				type=NodeType.PITCH_CLASS,
				label=pc,
				properties={'type': 'pitch_class'}
			)
			graph.add_node(node)
			
	def _add_interval_nodes(self, graph: MusicTheoryGraph, 
						   intervals: Set[str]) -> None:
		for interval in intervals:
			node = Node(
				id=f"int_{interval}",
				type=NodeType.INTERVAL,
				label=interval,
				properties={'type': 'interval'}
			)
			graph.add_node(node)
			
	def _add_set_class_nodes(self, graph: MusicTheoryGraph, 
							set_classes: Set[str]) -> None:
		for sc in set_classes:
			node = Node(
				id=f"sc_{sc}",
				type=NodeType.SET_CLASS,
				label=sc,
				properties={'type': 'set_class'}
			)
			graph.add_node(node)
			
	def _add_transformation_nodes(self, graph: MusicTheoryGraph,
								transformations: Set[str]) -> None:
		for trans in transformations:
			node = Node(
				id=f"trans_{trans}",
				type=NodeType.TRANSFORMATION,
				label=trans,
				properties={'type': 'transformation'}
			)
			graph.add_node(node)
			
	def _create_relationships(self, graph: MusicTheoryGraph, text: str) -> None:
		# Find relationships between pitch classes and intervals
		pc_pairs = re.finditer(
			f"({self.pitch_class_pattern})\\s*({self.interval_pattern})",
			text
		)
		for match in pc_pairs:
			pc, interval = match.groups()
			edge = Edge(
				source=f"pc_{pc}",
				target=f"int_{interval}",
				label="has_interval"
			)
			graph.add_edge(edge)
			
		# Find relationships between set classes and transformations
		set_trans = re.finditer(
			f"({self.set_class_pattern})\\s*({self.transformation_pattern})",
			text
		)
		for match in set_trans:
			sc, trans = match.groups()
			edge = Edge(
				source=f"sc_{sc}",
				target=f"trans_{trans}",
				label="transformed_by"
			)
			graph.add_edge(edge)