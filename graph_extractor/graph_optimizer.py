from typing import Dict, List, Set, Optional
from collections import defaultdict
from .graph_types import MusicTheoryGraph, Node, Edge, NodeType

class GraphOptimizer:
	def __init__(self):
		self.optimization_strategies = {
			'merge_similar_nodes': self._merge_similar_nodes,
			'remove_redundant_edges': self._remove_redundant_edges,
			'simplify_transformations': self._simplify_transformations,
			'compress_paths': self._compress_paths
		}
		
	def optimize(self, graph: MusicTheoryGraph, 
				strategies: Optional[List[str]] = None) -> MusicTheoryGraph:
		if strategies is None:
			strategies = list(self.optimization_strategies.keys())
			
		optimized_graph = graph
		for strategy in strategies:
			if strategy in self.optimization_strategies:
				optimized_graph = self.optimization_strategies[strategy](optimized_graph)
				
		return optimized_graph
		
	def _merge_similar_nodes(self, graph: MusicTheoryGraph) -> MusicTheoryGraph:
		new_graph = MusicTheoryGraph()
		merged_nodes = {}
		
		# Group similar nodes
		node_groups = defaultdict(list)
		for node in graph.nodes.values():
			key = self._get_node_similarity_key(node)
			node_groups[key].append(node)
			
		# Create merged nodes
		for group in node_groups.values():
			if len(group) > 1:
				merged_node = self._create_merged_node(group)
				for node in group:
					merged_nodes[node.id] = merged_node.id
				new_graph.add_node(merged_node)
			else:
				new_graph.add_node(group[0])
				merged_nodes[group[0].id] = group[0].id
				
		# Update edges
		for edge in graph.edges:
			new_source = merged_nodes[edge.source]
			new_target = merged_nodes[edge.target]
			if new_source != new_target:  # Avoid self-loops
				new_edge = Edge(
					source=new_source,
					target=new_target,
					label=edge.label,
					weight=edge.weight,
					properties=edge.properties
				)
				new_graph.add_edge(new_edge)
				
		return new_graph
		
	def _remove_redundant_edges(self, graph: MusicTheoryGraph) -> MusicTheoryGraph:
		new_graph = MusicTheoryGraph()
		
		# Copy nodes
		for node in graph.nodes.values():
			new_graph.add_node(node)
			
		# Find and remove redundant edges
		edge_dict = defaultdict(list)
		for edge in graph.edges:
			key = (edge.source, edge.target)
			edge_dict[key].append(edge)
			
		for edges in edge_dict.values():
			if len(edges) > 1:
				# Keep the most significant edge
				significant_edge = self._select_significant_edge(edges)
				new_graph.add_edge(significant_edge)
			else:
				new_graph.add_edge(edges[0])
				
		return new_graph
		
	def _simplify_transformations(self, graph: MusicTheoryGraph) -> MusicTheoryGraph:
		new_graph = MusicTheoryGraph()
		
		# Copy non-transformation nodes
		for node in graph.nodes.values():
			if node.type != NodeType.TRANSFORMATION:
				new_graph.add_node(node)
				
		# Simplify transformation chains
		transformation_chains = self._find_transformation_chains(graph)
		for chain in transformation_chains:
			simplified = self._simplify_transformation_chain(chain, graph)
			for node in simplified['nodes']:
				new_graph.add_node(node)
			for edge in simplified['edges']:
				new_graph.add_edge(edge)
				
		return new_graph
		
	def _compress_paths(self, graph: MusicTheoryGraph) -> MusicTheoryGraph:
		new_graph = MusicTheoryGraph()
		
		# Copy nodes
		for node in graph.nodes.values():
			new_graph.add_node(node)
			
		# Find and compress linear paths
		paths = self._find_linear_paths(graph)
		compressed_edges = self._compress_linear_paths(paths, graph)
		
		# Add compressed edges
		for edge in compressed_edges:
			new_graph.add_edge(edge)
			
		return new_graph
		
	def _get_node_similarity_key(self, node: Node) -> str:
		return f"{node.type}_{node.label}"
		
	def _create_merged_node(self, nodes: List[Node]) -> Node:
		# Merge properties and create a new node
		base_node = nodes[0]
		merged_properties = {}
		for node in nodes:
			merged_properties.update(node.properties)
			
		return Node(
			id=f"merged_{'_'.join(n.id for n in nodes)}",
			type=base_node.type,
			label=base_node.label,
			properties=merged_properties
		)
		
	def _select_significant_edge(self, edges: List[Edge]) -> Edge:
		# Select the edge with highest weight or most properties
		return max(edges, key=lambda e: (e.weight, len(e.properties or {})))
		
	def _find_transformation_chains(self, 
								  graph: MusicTheoryGraph) -> List[List[str]]:
		chains = []
		visited = set()
		
		for node in graph.nodes.values():
			if node.type == NodeType.TRANSFORMATION and node.id not in visited:
				chain = self._follow_transformation_chain(graph, node.id, visited)
				if len(chain) > 1:
					chains.append(chain)
					
		return chains
		
	def _simplify_transformation_chain(self, chain: List[str], 
									 graph: MusicTheoryGraph) -> Dict:
		# Create a single transformation node representing the chain
		nodes = [graph.nodes[node_id] for node_id in chain]
		simplified_node = Node(
			id=f"trans_{'_'.join(n.label for n in nodes)}",
			type=NodeType.TRANSFORMATION,
			label=f"{'→'.join(n.label for n in nodes)}",
			properties={'original_chain': [n.id for n in nodes]}
		)
		
		return {
			'nodes': [simplified_node],
			'edges': []
		}
		
	def _find_linear_paths(self, graph: MusicTheoryGraph) -> List[List[str]]:
		paths = []
		visited = set()
		
		for node_id in graph.nodes:
			if node_id not in visited:
				path = self._follow_linear_path(graph, node_id, visited)
				if len(path) > 2:
					paths.append(path)
					
		return paths
		
	def _compress_linear_paths(self, paths: List[List[str]], 
							 graph: MusicTheoryGraph) -> List[Edge]:
		compressed_edges = []
		
		for path in paths:
			start_node = path[0]
			end_node = path[-1]
			
			edge = Edge(
				source=start_node,
				target=end_node,
				label=f"compressed_path_{len(path)}",
				weight=1.0,
				properties={'original_path': path}
			)
			compressed_edges.append(edge)
			
		return compressed_edges
		
	def _follow_transformation_chain(self, graph: MusicTheoryGraph, 
								   start_id: str, 
								   visited: Set[str]) -> List[str]:
		chain = []
		current = start_id
		
		while True:
			if current in visited:
				break
				
			visited.add(current)
			chain.append(current)
			
			next_edges = [e for e in graph.edges 
						 if e.source == current and 
						 graph.nodes[e.target].type == NodeType.TRANSFORMATION]
			
			if not next_edges:
				break
				
			current = next_edges[0].target
			
		return chain
		
	def _follow_linear_path(self, graph: MusicTheoryGraph, 
						  start_id: str, 
						  visited: Set[str]) -> List[str]:
		path = []
		current = start_id
		
		while True:
			if current in visited:
				break
				
			visited.add(current)
			path.append(current)
			
			neighbors = [e.target for e in graph.edges if e.source == current] + \
					   [e.source for e in graph.edges if e.target == current]
			
			# Only continue if there's exactly one unvisited neighbor
			unvisited_neighbors = [n for n in neighbors if n not in visited]
			if len(unvisited_neighbors) != 1:
				break
				
			current = unvisited_neighbors[0]
			
		return path