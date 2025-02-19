from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import re
from .graph_types import Node, Edge, NodeType, MusicTheoryGraph

@dataclass
class TreeNode:
	content: str
	level: int
	children: List['TreeNode']
	properties: Dict[str, any]

class TreeStructureParser:
	def __init__(self):
		self.indent_patterns = {
			'bullet': r'^\s*[•\-\*]\s+',
			'numbered': r'^\s*\d+[\.)\]]\s+',
			'hierarchical': r'^\s*(?:\d+\.)*\d+\s+'
		}
		
	def parse_hierarchical_structure(self, text: str) -> MusicTheoryGraph:
		graph = MusicTheoryGraph()
		lines = text.split('\n')
		root_node = self._build_tree_structure(lines)
		
		# Convert tree structure to graph
		self._convert_tree_to_graph(root_node, graph)
		
		return graph
		
	def _build_tree_structure(self, lines: List[str]) -> TreeNode:
		root = TreeNode("root", -1, [], {})
		stack = [(root, -1)]
		
		for line in lines:
			level = self._get_indentation_level(line)
			content = self._clean_line(line)
			
			if not content:
				continue
				
			node = TreeNode(content, level, [], {
				'type': self._determine_node_type(content)
			})
			
			# Find appropriate parent
			while stack and stack[-1][1] >= level:
				stack.pop()
				
			parent, _ = stack[-1]
			parent.children.append(node)
			stack.append((node, level))
			
		return root
		
	def _get_indentation_level(self, line: str) -> int:
		return len(line) - len(line.lstrip())
		
	def _clean_line(self, line: str) -> str:
		# Remove bullets and numbering
		for pattern in self.indent_patterns.values():
			line = re.sub(pattern, '', line)
		return line.strip()
		
	def _determine_node_type(self, content: str) -> str:
		if re.search(r'[A-G][#b]?(?:\s*(?:major|minor|dim|aug))?', content):
			return 'chord'
		elif re.search(r'T\d+|P\d+|L\d+', content):
			return 'transformation'
		else:
			return 'concept'
			
	def _convert_tree_to_graph(self, tree_node: TreeNode, 
							 graph: MusicTheoryGraph, 
							 parent_id: Optional[str] = None) -> str:
		if tree_node.content == "root":
			node_id = "root"
		else:
			node_id = f"node_{hash(tree_node.content)}"
			node = Node(
				id=node_id,
				type=NodeType.SET_CLASS if tree_node.properties['type'] == 'chord'
					  else NodeType.TRANSFORMATION if tree_node.properties['type'] == 'transformation'
					  else NodeType.INTERVAL,
				label=tree_node.content,
				properties=tree_node.properties
			)
			graph.add_node(node)
			
			if parent_id:
				edge = Edge(
					source=parent_id,
					target=node_id,
					label="contains",
					properties={'hierarchical': True}
				)
				graph.add_edge(edge)
				
		# Process children
		for child in tree_node.children:
			self._convert_tree_to_graph(child, graph, node_id)
			
		return node_id