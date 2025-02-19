from typing import Dict, List, Optional, Callable
import numpy as np
from .graph_types import MusicTheoryGraph, Node, Edge, NodeType

class GraphTransformer:
	def __init__(self):
		self.transformation_functions = {
			'T': self._transpose,
			'I': self._invert,
			'P': self._parallel,
			'L': self._leading_tone,
			'R': self._relative
		}
		
	def apply_transformation(self, graph: MusicTheoryGraph, 
						   transform_type: str, 
						   params: Optional[Dict] = None) -> MusicTheoryGraph:
		if transform_type[0] not in self.transformation_functions:
			raise ValueError(f"Unknown transformation type: {transform_type}")
			
		transform_func = self.transformation_functions[transform_type[0]]
		return transform_func(graph, transform_type, params or {})
		
	def _transpose(self, graph: MusicTheoryGraph, 
				  transform: str, params: Dict) -> MusicTheoryGraph:
		new_graph = MusicTheoryGraph()
		n = int(transform[1:]) if len(transform) > 1 else 0
		
		for node in graph.nodes.values():
			if node.type == NodeType.PITCH_CLASS:
				new_pitch = self._transpose_pitch(node.label, n)
				new_node = Node(
					id=f"pc_{new_pitch}",
					type=NodeType.PITCH_CLASS,
					label=new_pitch,
					properties=node.properties.copy()
				)
				new_graph.add_node(new_node)
			else:
				new_graph.add_node(node)
				
		# Copy edges with updated references
		for edge in graph.edges:
			new_graph.add_edge(edge)
			
		return new_graph
		
	def _invert(self, graph: MusicTheoryGraph, 
				transform: str, params: Dict) -> MusicTheoryGraph:
		new_graph = MusicTheoryGraph()
		n = int(transform[1:]) if len(transform) > 1 else 0
		
		for node in graph.nodes.values():
			if node.type == NodeType.PITCH_CLASS:
				new_pitch = self._invert_pitch(node.label, n)
				new_node = Node(
					id=f"pc_{new_pitch}",
					type=NodeType.PITCH_CLASS,
					label=new_pitch,
					properties=node.properties.copy()
				)
				new_graph.add_node(new_node)
			else:
				new_graph.add_node(node)
				
		for edge in graph.edges:
			new_graph.add_edge(edge)
			
		return new_graph
		
	def _parallel(self, graph: MusicTheoryGraph, 
				 transform: str, params: Dict) -> MusicTheoryGraph:
		new_graph = MusicTheoryGraph()
		
		for node in graph.nodes.values():
			if node.type == NodeType.SET_CLASS:
				new_set = self._parallel_transform(node.label)
				new_node = Node(
					id=f"sc_{new_set}",
					type=NodeType.SET_CLASS,
					label=new_set,
					properties=node.properties.copy()
				)
				new_graph.add_node(new_node)
			else:
				new_graph.add_node(node)
				
		for edge in graph.edges:
			new_graph.add_edge(edge)
			
		return new_graph
		
	def _leading_tone(self, graph: MusicTheoryGraph, 
					 transform: str, params: Dict) -> MusicTheoryGraph:
		new_graph = MusicTheoryGraph()
		
		for node in graph.nodes.values():
			if node.type == NodeType.SET_CLASS:
				new_set = self._leading_tone_transform(node.label)
				new_node = Node(
					id=f"sc_{new_set}",
					type=NodeType.SET_CLASS,
					label=new_set,
					properties=node.properties.copy()
				)
				new_graph.add_node(new_node)
			else:
				new_graph.add_node(node)
				
		for edge in graph.edges:
			new_graph.add_edge(edge)
			
		return new_graph
		
	def _relative(self, graph: MusicTheoryGraph, 
				 transform: str, params: Dict) -> MusicTheoryGraph:
		new_graph = MusicTheoryGraph()
		
		for node in graph.nodes.values():
			if node.type == NodeType.SET_CLASS:
				new_set = self._relative_transform(node.label)
				new_node = Node(
					id=f"sc_{new_set}",
					type=NodeType.SET_CLASS,
					label=new_set,
					properties=node.properties.copy()
				)
				new_graph.add_node(new_node)
			else:
				new_graph.add_node(node)
				
		for edge in graph.edges:
			new_graph.add_edge(edge)
			
		return new_graph
		
	def _transpose_pitch(self, pitch: str, n: int) -> str:
		pitch_classes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
		idx = pitch_classes.index(pitch)
		return pitch_classes[(idx + n) % 12]
		
	def _invert_pitch(self, pitch: str, n: int) -> str:
		pitch_classes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
		idx = pitch_classes.index(pitch)
		return pitch_classes[(12 - idx + n) % 12]
		
	def _parallel_transform(self, set_class: str) -> str:
		# Implement parallel transformation logic for set classes
		# This is a placeholder implementation
		return f"P({set_class})"
		
	def _leading_tone_transform(self, set_class: str) -> str:
		# Implement leading tone transformation logic for set classes
		# This is a placeholder implementation
		return f"L({set_class})"
		
	def _relative_transform(self, set_class: str) -> str:
		# Implement relative transformation logic for set classes
		# This is a placeholder implementation
		return f"R({set_class})"