from typing import Dict, List, Set, Tuple
import networkx as nx
from collections import Counter
from .graph_types import MusicTheoryGraph, Node, Edge, NodeType

class GraphMetricsCollector:
	def collect_metrics(self, graph: MusicTheoryGraph) -> Dict[str, any]:
		nx_graph = self._to_networkx(graph)
		
		metrics = {
			'basic_stats': self._collect_basic_stats(graph),
			'node_type_distribution': self._get_node_type_distribution(graph),
			'centrality_metrics': self._compute_centrality_metrics(nx_graph),
			'structural_metrics': self._compute_structural_metrics(nx_graph),
			'transformation_patterns': self._analyze_transformation_patterns(graph)
		}
		
		return metrics
		
	def _to_networkx(self, graph: MusicTheoryGraph) -> nx.Graph:
		G = nx.Graph()
		
		for node in graph.nodes.values():
			G.add_node(node.id, **{'type': node.type.value, 'label': node.label})
			
		for edge in graph.edges:
			G.add_edge(edge.source, edge.target, 
					  weight=edge.weight, label=edge.label)
			
		return G
		
	def _collect_basic_stats(self, graph: MusicTheoryGraph) -> Dict[str, int]:
		return {
			'total_nodes': len(graph.nodes),
			'total_edges': len(graph.edges),
			'pitch_classes': len([n for n in graph.nodes.values() 
								if n.type == NodeType.PITCH_CLASS]),
			'intervals': len([n for n in graph.nodes.values() 
							if n.type == NodeType.INTERVAL]),
			'transformations': len([n for n in graph.nodes.values() 
								  if n.type == NodeType.TRANSFORMATION])
		}
		
	def _get_node_type_distribution(self, graph: MusicTheoryGraph) -> Dict[str, int]:
		type_counts = Counter(node.type.value for node in graph.nodes.values())
		return dict(type_counts)
		
	def _compute_centrality_metrics(self, G: nx.Graph) -> Dict[str, Dict[str, float]]:
		return {
			'degree_centrality': nx.degree_centrality(G),
			'betweenness_centrality': nx.betweenness_centrality(G),
			'closeness_centrality': nx.closeness_centrality(G),
			'eigenvector_centrality': nx.eigenvector_centrality(G, max_iter=1000)
		}
		
	def _compute_structural_metrics(self, G: nx.Graph) -> Dict[str, any]:
		metrics = {
			'average_clustering': nx.average_clustering(G),
			'density': nx.density(G),
			'diameter': nx.diameter(G) if nx.is_connected(G) else float('inf'),
			'average_shortest_path': (
				nx.average_shortest_path_length(G)
				if nx.is_connected(G) else float('inf')
			)
		}
		
		# Compute connected components
		components = list(nx.connected_components(G))
		metrics['num_components'] = len(components)
		metrics['largest_component_size'] = len(max(components, key=len))
		
		return metrics
		
	def _analyze_transformation_patterns(self, 
									   graph: MusicTheoryGraph) -> Dict[str, any]:
		transformation_nodes = [n for n in graph.nodes.values() 
							  if n.type == NodeType.TRANSFORMATION]
		
		patterns = {
			'transformation_types': Counter(n.label for n in transformation_nodes),
			'common_sequences': self._find_transformation_sequences(graph),
			'cyclic_patterns': self._find_cyclic_patterns(graph)
		}
		
		return patterns
		
	def _find_transformation_sequences(self, 
									 graph: MusicTheoryGraph) -> List[List[str]]:
		sequences = []
		transformation_edges = [e for e in graph.edges 
							  if any(n.type == NodeType.TRANSFORMATION 
									for n in [graph.nodes[e.source], 
											graph.nodes[e.target]])]
		
		# Find sequences of connected transformations
		visited = set()
		for edge in transformation_edges:
			if edge.source not in visited:
				sequence = self._follow_transformation_chain(graph, edge.source)
				if len(sequence) > 1:
					sequences.append(sequence)
				visited.update(sequence)
				
		return sequences
		
	def _find_cyclic_patterns(self, graph: MusicTheoryGraph) -> List[List[str]]:
		cycles = []
		nx_graph = self._to_networkx(graph)
		
		# Find simple cycles in the graph
		for cycle in nx.simple_cycles(nx_graph):
			if all(graph.nodes[node_id].type == NodeType.TRANSFORMATION 
				   for node_id in cycle):
				cycles.append([graph.nodes[node_id].label for node_id in cycle])
				
		return cycles
		
	def _follow_transformation_chain(self, graph: MusicTheoryGraph, 
								   start_node: str) -> List[str]:
		chain = [start_node]
		current = start_node
		
		while True:
			next_edges = [e for e in graph.edges 
						 if e.source == current and e.target not in chain]
			if not next_edges:
				break
				
			current = next_edges[0].target
			chain.append(current)
			
		return chain