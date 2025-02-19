from typing import Dict, List, Set, Tuple
import networkx as nx
from .graph_types import MusicTheoryGraph, Node, Edge, NodeType

class GraphComparator:
	def compare_graphs(self, graph1: MusicTheoryGraph, 
					  graph2: MusicTheoryGraph) -> Dict[str, any]:
		comparison = {
			'node_differences': self._compare_nodes(graph1, graph2),
			'edge_differences': self._compare_edges(graph1, graph2),
			'structural_differences': self._compare_structure(graph1, graph2),
			'transformation_differences': self._compare_transformations(graph1, graph2),
			'similarity_metrics': self._compute_similarity_metrics(graph1, graph2)
		}
		return comparison
		
	def _compare_nodes(self, graph1: MusicTheoryGraph, 
					  graph2: MusicTheoryGraph) -> Dict[str, Set[str]]:
		nodes1 = set(graph1.nodes.keys())
		nodes2 = set(graph2.nodes.keys())
		
		return {
			'unique_to_graph1': nodes1 - nodes2,
			'unique_to_graph2': nodes2 - nodes1,
			'common': nodes1 & nodes2,
			'type_differences': self._compare_node_types(graph1, graph2)
		}
		
	def _compare_edges(self, graph1: MusicTheoryGraph, 
					  graph2: MusicTheoryGraph) -> Dict[str, Set[Tuple[str, str]]]:
		edges1 = {(e.source, e.target) for e in graph1.edges}
		edges2 = {(e.source, e.target) for e in graph2.edges}
		
		return {
			'unique_to_graph1': edges1 - edges2,
			'unique_to_graph2': edges2 - edges1,
			'common': edges1 & edges2
		}
		
	def _compare_structure(self, graph1: MusicTheoryGraph, 
						 graph2: MusicTheoryGraph) -> Dict[str, any]:
		nx1 = self._to_networkx(graph1)
		nx2 = self._to_networkx(graph2)
		
		return {
			'component_count_diff': (
				nx.number_connected_components(nx1) - 
				nx.number_connected_components(nx2)
			),
			'density_diff': nx.density(nx1) - nx.density(nx2),
			'avg_degree_diff': (
				sum(dict(nx1.degree()).values()) / nx1.number_of_nodes() -
				sum(dict(nx2.degree()).values()) / nx2.number_of_nodes()
			)
		}
		
	def _compare_transformations(self, graph1: MusicTheoryGraph, 
							   graph2: MusicTheoryGraph) -> Dict[str, any]:
		trans1 = self._get_transformation_patterns(graph1)
		trans2 = self._get_transformation_patterns(graph2)
		
		return {
			'unique_patterns_graph1': trans1 - trans2,
			'unique_patterns_graph2': trans2 - trans1,
			'common_patterns': trans1 & trans2
		}
		
	def _compute_similarity_metrics(self, graph1: MusicTheoryGraph, 
								  graph2: MusicTheoryGraph) -> Dict[str, float]:
		nx1 = self._to_networkx(graph1)
		nx2 = self._to_networkx(graph2)
		
		return {
			'node_similarity': self._compute_node_similarity(graph1, graph2),
			'edge_similarity': self._compute_edge_similarity(graph1, graph2),
			'structural_similarity': self._compute_structural_similarity(nx1, nx2)
		}
		
	def _compare_node_types(self, graph1: MusicTheoryGraph, 
						  graph2: MusicTheoryGraph) -> Dict[str, Set[str]]:
		differences = {}
		common_nodes = set(graph1.nodes.keys()) & set(graph2.nodes.keys())
		
		for node_id in common_nodes:
			if graph1.nodes[node_id].type != graph2.nodes[node_id].type:
				differences[node_id] = {
					'graph1_type': graph1.nodes[node_id].type.value,
					'graph2_type': graph2.nodes[node_id].type.value
				}
				
		return differences
		
	def _get_transformation_patterns(self, graph: MusicTheoryGraph) -> Set[Tuple[str, ...]]:
		patterns = set()
		transformation_nodes = [n for n in graph.nodes.values() 
							  if n.type == NodeType.TRANSFORMATION]
		
		for node in transformation_nodes:
			connected = self._get_connected_transformations(graph, node.id)
			if len(connected) > 1:
				patterns.add(tuple(sorted(n.label for n in connected)))
				
		return patterns
		
	def _get_connected_transformations(self, graph: MusicTheoryGraph, 
									 start_id: str) -> List[Node]:
		connected = []
		visited = set()
		stack = [start_id]
		
		while stack:
			current = stack.pop()
			if current not in visited:
				visited.add(current)
				node = graph.nodes[current]
				if node.type == NodeType.TRANSFORMATION:
					connected.append(node)
				
				for edge in graph.edges:
					if edge.source == current and edge.target not in visited:
						stack.append(edge.target)
					elif edge.target == current and edge.source not in visited:
						stack.append(edge.source)
						
		return connected
		
	def _to_networkx(self, graph: MusicTheoryGraph) -> nx.Graph:
		G = nx.Graph()
		for node in graph.nodes.values():
			G.add_node(node.id)
		for edge in graph.edges:
			G.add_edge(edge.source, edge.target)
		return G
		
	def _compute_node_similarity(self, graph1: MusicTheoryGraph, 
							   graph2: MusicTheoryGraph) -> float:
		nodes1 = set(graph1.nodes.keys())
		nodes2 = set(graph2.nodes.keys())
		intersection = len(nodes1 & nodes2)
		union = len(nodes1 | nodes2)
		return intersection / union if union > 0 else 0.0
		
	def _compute_edge_similarity(self, graph1: MusicTheoryGraph, 
							   graph2: MusicTheoryGraph) -> float:
		edges1 = {(e.source, e.target) for e in graph1.edges}
		edges2 = {(e.source, e.target) for e in graph2.edges}
		intersection = len(edges1 & edges2)
		union = len(edges1 | edges2)
		return intersection / union if union > 0 else 0.0
		
	def _compute_structural_similarity(self, nx1: nx.Graph, nx2: nx.Graph) -> float:
		# Use graph edit distance as a measure of structural similarity
		try:
			distance = nx.graph_edit_distance(nx1, nx2)
			max_size = max(nx1.number_of_nodes() + nx1.number_of_edges(),
						 nx2.number_of_nodes() + nx2.number_of_edges())
			return 1.0 - (distance / max_size) if max_size > 0 else 1.0
		except:
			return 0.0