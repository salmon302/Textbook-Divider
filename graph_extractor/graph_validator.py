from typing import List, Dict, Set, Tuple
from .graph_types import MusicTheoryGraph, Node, Edge, NodeType

class GraphValidationError(Exception):
	pass

class GraphValidator:
	def __init__(self):
		self.validation_rules = {
			'connectivity': self._check_connectivity,
			'node_types': self._check_node_types,
			'edge_validity': self._check_edge_validity,
			'transformation_consistency': self._check_transformation_consistency
		}
		
	def validate(self, graph: MusicTheoryGraph) -> List[str]:
		errors = []
		for rule_name, rule_func in self.validation_rules.items():
			try:
				rule_func(graph)
			except GraphValidationError as e:
				errors.append(f"{rule_name}: {str(e)}")
		return errors
		
	def _check_connectivity(self, graph: MusicTheoryGraph) -> None:
		if not graph.nodes:
			return
			
		visited = set()
		start_node = next(iter(graph.nodes.values()))
		self._dfs(graph, start_node.id, visited)
		
		if len(visited) != len(graph.nodes):
			unvisited = set(graph.nodes.keys()) - visited
			raise GraphValidationError(
				f"Graph is not connected. Unreachable nodes: {unvisited}")
				
	def _check_node_types(self, graph: MusicTheoryGraph) -> None:
		invalid_nodes = []
		for node in graph.nodes.values():
			if not isinstance(node.type, NodeType):
				invalid_nodes.append(node.id)
				
		if invalid_nodes:
			raise GraphValidationError(
				f"Invalid node types found in nodes: {invalid_nodes}")
				
	def _check_edge_validity(self, graph: MusicTheoryGraph) -> None:
		invalid_edges = []
		for edge in graph.edges:
			if edge.source not in graph.nodes or edge.target not in graph.nodes:
				invalid_edges.append((edge.source, edge.target))
				
		if invalid_edges:
			raise GraphValidationError(
				f"Invalid edges found: {invalid_edges}")
				
	def _check_transformation_consistency(self, graph: MusicTheoryGraph) -> None:
		transformation_nodes = [n for n in graph.nodes.values() 
							  if n.type == NodeType.TRANSFORMATION]
		
		for trans_node in transformation_nodes:
			connected_edges = [e for e in graph.edges 
							 if e.source == trans_node.id or e.target == trans_node.id]
			
			if len(connected_edges) < 2:
				raise GraphValidationError(
					f"Transformation node {trans_node.id} should have at least "
					"two connections")
					
	def _dfs(self, graph: MusicTheoryGraph, node_id: str, 
			 visited: Set[str]) -> None:
		visited.add(node_id)
		for edge in graph.edges:
			if edge.source == node_id and edge.target not in visited:
				self._dfs(graph, edge.target, visited)
			elif edge.target == node_id and edge.source not in visited:
				self._dfs(graph, edge.source, visited)