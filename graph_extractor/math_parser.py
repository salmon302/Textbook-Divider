from typing import List, Dict, Optional, Tuple
import re
from .graph_types import Node, Edge, NodeType, MusicTheoryGraph

class MathNotationParser:
	def __init__(self):
		self.math_patterns = {
			'interval': r'int\(([\w\d\s,]+)\)',
			'function': r'f\s*:\s*([\w\d]+)\s*→\s*([\w\d]+)',
			'set': r'\{([^}]+)\}',
			'matrix': r'\[\[([\d\s,]+)\]\]'
		}
		
	def parse_mathematical_notation(self, text: str) -> MusicTheoryGraph:
		graph = MusicTheoryGraph()
		
		# Parse intervals
		intervals = re.finditer(self.math_patterns['interval'], text)
		for match in intervals:
			content = match.group(1)
			node = Node(
				id=f"interval_{hash(content)}",
				type=NodeType.INTERVAL,
				label=f"Interval({content})",
				properties={
					'content': content,
					'position': match.span()
				}
			)
			graph.add_node(node)
			
		# Parse functions and their mappings
		functions = re.finditer(self.math_patterns['function'], text)
		for match in functions:
			domain, codomain = match.group(1), match.group(2)
			node = Node(
				id=f"trans_f_{hash(domain + codomain)}",
				type=NodeType.TRANSFORMATION,
				label=f"f: {domain} → {codomain}",
				properties={
					'domain': domain,
					'codomain': codomain,
					'position': match.span()
				}
			)
			graph.add_node(node)
			
		# Connect related mathematical elements
		self._connect_mathematical_elements(graph)
		
		return graph
		
	def _connect_mathematical_elements(self, graph: MusicTheoryGraph) -> None:
		nodes = list(graph.nodes.values())
		for i, node1 in enumerate(nodes):
			for node2 in nodes[i+1:]:
				if self._are_mathematically_related(node1, node2):
					edge = Edge(
						source=node1.id,
						target=node2.id,
						label="mathematical_relation",
						properties={'type': 'math_dependency'}
					)
					graph.add_edge(edge)
					
	def _are_mathematically_related(self, node1: Node, node2: Node) -> bool:
		# Check if nodes share mathematical relationships
		if node1.type == NodeType.TRANSFORMATION and node2.type == NodeType.INTERVAL:
			return node1.properties.get('domain') in node2.properties.get('content', '')
		return False