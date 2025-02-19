from typing import Dict, List, Set, Optional, Tuple
import networkx as nx
from functools import lru_cache
from .graph_types import MusicTheoryGraph, Node, Edge, NodeType
from .graph_exporter import GraphExporter

class GraphAnalyzer:
	def __init__(self, graph: MusicTheoryGraph):
		self.graph = graph
		self.nx_graph = GraphExporter.to_networkx(graph)
		self._transform_nodes = None
		self._components = None
		
	@property
	def transform_nodes(self) -> List[Node]:
		if self._transform_nodes is None:
			self._transform_nodes = [n for n in self.graph.nodes.values() 
								   if n.type == NodeType.TRANSFORMATION]
		return self._transform_nodes
	
	@lru_cache(maxsize=1024)
	def find_transformation_cycles(self) -> List[List[str]]:
		"""Find cycles in transformation relationships with optimized caching"""
		transform_subgraph = self.nx_graph.subgraph(
			[n.id for n in self.transform_nodes]
		)
		return [cycle for cycle in nx.simple_cycles(transform_subgraph)]
	
	def get_connected_components(self) -> List[Set[str]]:
		"""Get connected components with caching"""
		if self._components is None:
			self._components = list(nx.connected_components(self.nx_graph))
		return self._components
	
	@lru_cache(maxsize=1024)
	def find_shortest_transformation_path(self, 
									   start_node: str, 
									   end_node: str) -> Optional[List[str]]:
		"""Find shortest path between nodes with caching"""
		try:
			return nx.shortest_path(self.nx_graph, start_node, end_node)
		except nx.NetworkXNoPath:
			return None
	
	def analyze_transformation_network(self) -> Dict[str, any]:
		"""Analyze transformation network with optimized metrics calculation"""
		transform_subgraph = self.nx_graph.subgraph(
			[n.id for n in self.transform_nodes]
		)
		
		# Calculate metrics only for the transformation subgraph
		analysis = {
			'num_transformations': len(self.transform_nodes),
			'centrality': nx.degree_centrality(transform_subgraph),
			'betweenness': nx.betweenness_centrality(transform_subgraph),
			'clustering': nx.clustering(transform_subgraph)
		}
		
		# Only calculate path length if graph is connected
		if nx.is_connected(transform_subgraph):
			analysis['average_path_length'] = nx.average_shortest_path_length(
				transform_subgraph
			)
		else:
			analysis['average_path_length'] = float('inf')
			
		return analysis
	
	def find_invariant_structures(self) -> List[Set[str]]:
		"""Find invariant structures with optimized edge filtering"""
		invariant_sets = []
		edge_map: Dict[str, List[Edge]] = {}
		
		# Pre-process edges by transformation
		for edge in self.graph.edges:
			transform_id = edge.properties.get('transformation_id')
			if transform_id:
				if transform_id not in edge_map:
					edge_map[transform_id] = []
				edge_map[transform_id].append(edge)
		
		# Find invariant nodes for each transformation
		for transform in self.transform_nodes:
			if transform.id in edge_map:
				invariant_nodes = {e.source for e in edge_map[transform.id] 
								 if e.source == e.target}
				if invariant_nodes:
					invariant_sets.append(invariant_nodes)
		
		return invariant_sets