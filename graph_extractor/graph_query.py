from typing import List, Dict, Set, Optional, Callable
from .graph_types import MusicTheoryGraph, Node, Edge, NodeType

class GraphQuery:
	def __init__(self, graph: MusicTheoryGraph):
		self.graph = graph
		
	def find_nodes_by_type(self, node_type: NodeType) -> List[Node]:
		return [node for node in self.graph.nodes.values() 
				if node.type == node_type]
				
	def find_nodes_by_label_pattern(self, pattern: str) -> List[Node]:
		import re
		regex = re.compile(pattern)
		return [node for node in self.graph.nodes.values() 
				if regex.search(node.label)]
				
	def find_transformation_path(self, start_label: str, 
							   end_label: str) -> Optional[List[str]]:
		start_nodes = [n for n in self.graph.nodes.values() 
					  if n.label == start_label]
		end_nodes = [n for n in self.graph.nodes.values() 
					if n.label == end_label]
					
		if not start_nodes or not end_nodes:
			return None
			
		return self._find_path(start_nodes[0].id, end_nodes[0].id)
		
	def find_connected_components(self, 
								node_type: Optional[NodeType] = None) -> List[Set[str]]:
		components = []
		visited = set()
		
		for node in self.graph.nodes.values():
			if node.id not in visited and (
				node_type is None or node.type == node_type):
				component = self._explore_component(node.id, node_type)
				components.append(component)
				visited.update(component)
				
		return components
		
	def find_cycles(self, node_type: Optional[NodeType] = None) -> List[List[str]]:
		cycles = []
		visited = set()
		
		for node in self.graph.nodes.values():
			if node.id not in visited and (
				node_type is None or node.type == node_type):
				self._find_cycles_dfs(node.id, [], set(), cycles, node_type)
				visited.add(node.id)
				
		return cycles
		
	def find_nodes_by_property(self, property_name: str, 
							 value: any) -> List[Node]:
		return [node for node in self.graph.nodes.values() 
				if property_name in node.properties 
				and node.properties[property_name] == value]
				
	def _find_path(self, start_id: str, end_id: str) -> Optional[List[str]]:
		visited = set()
		path = []
		
		def dfs(current_id: str) -> bool:
			visited.add(current_id)
			path.append(current_id)
			
			if current_id == end_id:
				return True
				
			for edge in self.graph.edges:
				next_id = None
				if edge.source == current_id and edge.target not in visited:
					next_id = edge.target
				elif edge.target == current_id and edge.source not in visited:
					next_id = edge.source
					
				if next_id and dfs(next_id):
					return True
					
			path.pop()
			return False
			
		return path if dfs(start_id) else None
		
	def _explore_component(self, start_id: str, 
						 node_type: Optional[NodeType]) -> Set[str]:
		component = set()
		stack = [start_id]
		
		while stack:
			current = stack.pop()
			if current not in component:
				node = self.graph.nodes[current]
				if node_type is None or node.type == node_type:
					component.add(current)
					
					for edge in self.graph.edges:
						if edge.source == current and edge.target not in component:
							stack.append(edge.target)
						elif edge.target == current and edge.source not in component:
							stack.append(edge.source)
							
		return component
		
	def _find_cycles_dfs(self, current: str, path: List[str], 
						visited: Set[str], cycles: List[List[str]], 
						node_type: Optional[NodeType]) -> None:
		path.append(current)
		visited.add(current)
		
		for edge in self.graph.edges:
			if edge.source == current:
				next_id = edge.target
			elif edge.target == current:
				next_id = edge.source
			else:
				continue
				
			if next_id in path:
				cycle = path[path.index(next_id):]
				if all(self.graph.nodes[n].type == node_type 
					  for n in cycle if node_type):
					cycles.append(cycle)
			elif next_id not in visited:
				self._find_cycles_dfs(next_id, path, visited, cycles, node_type)
				
		path.pop()
		visited.remove(current)