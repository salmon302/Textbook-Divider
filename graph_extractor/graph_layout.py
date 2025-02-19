from typing import Dict, List, Tuple, Optional
import numpy as np
from .graph_types import MusicTheoryGraph, Node, Edge, NodeType

class GraphLayout:
	def __init__(self):
		self.layout_types = {
			'circle_of_fifths': self._circle_of_fifths_layout,
			'tonnetz': self._tonnetz_layout,
			'transformation_network': self._transformation_network_layout,
			'hierarchical': self._hierarchical_layout,
			'gis_network': self._gis_network_layout,
			'isomorphic_network': self._isomorphic_network_layout
		}
		
	def apply_layout(self, graph: MusicTheoryGraph, 
					layout_type: str,
					params: Optional[Dict] = None) -> MusicTheoryGraph:
		if layout_type not in self.layout_types:
			raise ValueError(f"Unsupported layout type: {layout_type}")
			
		layout_func = self.layout_types[layout_type]
		return layout_func(graph, params or {})
		
	def _circle_of_fifths_layout(self, graph: MusicTheoryGraph, 
							   params: Dict) -> MusicTheoryGraph:
		pitch_classes = ['C', 'G', 'D', 'A', 'E', 'B', 'F#', 
						'C#', 'G#', 'D#', 'A#', 'F']
		radius = params.get('radius', 1.0)
		
		# Create a new graph with positions
		new_graph = MusicTheoryGraph()
		
		for node in graph.nodes.values():
			if node.type == NodeType.PITCH_CLASS:
				try:
					idx = pitch_classes.index(node.label)
					angle = 2 * np.pi * idx / 12
					position = (radius * np.cos(angle), radius * np.sin(angle))
				except ValueError:
					position = (0, 0)
					
				new_node = Node(
					id=node.id,
					type=node.type,
					label=node.label,
					properties=node.properties,
					position=position
				)
				new_graph.add_node(new_node)
			else:
				new_graph.add_node(node)
				
		# Copy edges
		for edge in graph.edges:
			new_graph.add_edge(edge)
			
		return new_graph
		
	def _tonnetz_layout(self, graph: MusicTheoryGraph, 
					   params: Dict) -> MusicTheoryGraph:
		scale = params.get('scale', 1.0)
		new_graph = MusicTheoryGraph()
		
		# Tonnetz coordinates for pitch classes
		tonnetz_coords = {
			'C':  (0, 0),    'G': (1, 0),    'D': (2, 0),
			'E':  (0, 1),    'B': (1, 1),    'F#': (2, 1),
			'G#': (0, 2),    'D#': (1, 2),   'A#': (2, 2),
			'F':  (-0.5, -0.5), 'A': (0.5, -0.5)
		}
		
		for node in graph.nodes.values():
			if node.type == NodeType.PITCH_CLASS and node.label in tonnetz_coords:
				x, y = tonnetz_coords[node.label]
				position = (scale * x, scale * y)
				
				new_node = Node(
					id=node.id,
					type=node.type,
					label=node.label,
					properties=node.properties,
					position=position
				)
				new_graph.add_node(new_node)
			else:
				new_graph.add_node(node)
				
		# Copy edges
		for edge in graph.edges:
			new_graph.add_edge(edge)
			
		return new_graph
		
	def _transformation_network_layout(self, graph: MusicTheoryGraph, 
								   params: Dict) -> MusicTheoryGraph:
		layout_style = params.get('layout_style', 'hierarchical')
		if layout_style == 'circular':
			return self._circular_transformation_layout(graph, params)
		return self._hierarchical_transformation_layout(graph, params)

	def _circular_transformation_layout(self, graph: MusicTheoryGraph, 
									params: Dict) -> MusicTheoryGraph:
		new_graph = MusicTheoryGraph()
		radius = params.get('radius', 1.0)
		center_transformations = params.get('center_transformations', True)
		
		# Separate nodes by type
		pitch_nodes = [n for n in graph.nodes.values() if n.type == NodeType.PITCH_CLASS]
		transform_nodes = [n for n in graph.nodes.values() if n.type == NodeType.TRANSFORMATION]
		other_nodes = [n for n in graph.nodes.values() 
					  if n.type not in (NodeType.PITCH_CLASS, NodeType.TRANSFORMATION)]
		
		# Position pitch class nodes in outer circle
		for i, node in enumerate(pitch_nodes):
			angle = 2 * np.pi * i / len(pitch_nodes)
			position = (radius * np.cos(angle), radius * np.sin(angle))
			new_node = Node(
				id=node.id,
				type=node.type,
				label=node.label,
				properties=node.properties,
				position=position
			)
			new_graph.add_node(new_node)
		
		# Position transformation nodes
		if center_transformations and transform_nodes:
			inner_radius = radius * 0.5
			for i, node in enumerate(transform_nodes):
				angle = 2 * np.pi * i / len(transform_nodes)
				position = (inner_radius * np.cos(angle), inner_radius * np.sin(angle))
				new_node = Node(
					id=node.id,
					type=node.type,
					label=node.label,
					properties=node.properties,
					position=position
				)
				new_graph.add_node(new_node)
		
		# Position other nodes in grid layout
		grid_spacing = radius * 0.3
		for i, node in enumerate(other_nodes):
			row = i // 3
			col = i % 3
			position = (-radius + col * grid_spacing, -radius - row * grid_spacing)
			new_node = Node(
				id=node.id,
				type=node.type,
				label=node.label,
				properties=node.properties,
				position=position
			)
			new_graph.add_node(new_node)
		
		# Copy and route edges
		for edge in graph.edges:
			new_graph.add_edge(edge)
		
		return new_graph

	def _hierarchical_transformation_layout(self, graph: MusicTheoryGraph, 
									   params: Dict) -> MusicTheoryGraph:
		new_graph = MusicTheoryGraph()
		level_spacing = params.get('level_spacing', 1.0)
		node_spacing = params.get('node_spacing', 1.0)
		
		# Group nodes by type
		nodes_by_type = {
			NodeType.PITCH_CLASS: [],
			NodeType.TRANSFORMATION: [],
			NodeType.SET_CLASS: []
		}
		
		for node in graph.nodes.values():
			if node.type in nodes_by_type:
				nodes_by_type[node.type].append(node)
				
		# Position nodes by type level
		for level, (node_type, nodes) in enumerate(nodes_by_type.items()):
			for i, node in enumerate(nodes):
				position = (
					node_spacing * i - (len(nodes) - 1) * node_spacing / 2,
					level_spacing * level
				)
				new_node = Node(
					id=node.id,
					type=node.type,
					label=node.label,
					properties=node.properties,
					position=position
				)
				new_graph.add_node(new_node)
				
		# Copy edges
		for edge in graph.edges:
			new_graph.add_edge(edge)
			
		return new_graph
		
	def _hierarchical_layout(self, graph: MusicTheoryGraph, 
						   params: Dict) -> MusicTheoryGraph:
		new_graph = MusicTheoryGraph()
		level_height = params.get('level_height', 1.0)
		node_width = params.get('node_width', 1.0)
		
		# Find root nodes (nodes with no incoming edges)
		incoming_edges = {edge.target for edge in graph.edges}
		root_nodes = [node for node in graph.nodes.values() 
					 if node.id not in incoming_edges]
		
		# Assign levels through BFS
		levels = self._assign_hierarchical_levels(graph, root_nodes)
		
		# Position nodes by level
		for level, nodes in levels.items():
			for i, node in enumerate(nodes):
				position = (
					node_width * i - (len(nodes) - 1) * node_width / 2,
					-level_height * level
				)
				new_node = Node(
					id=node.id,
					type=node.type,
					label=node.label,
					properties=node.properties,
					position=position
				)
				new_graph.add_node(new_node)
				
		# Copy edges
		for edge in graph.edges:
			new_graph.add_edge(edge)
			
		return new_graph
		
	def _assign_hierarchical_levels(self, graph: MusicTheoryGraph, 
								  root_nodes: List[Node]) -> Dict[int, List[Node]]:
		levels = {}
		visited = set()
		
		def assign_level(node: Node, level: int):
			if node.id in visited:
				return
				
			visited.add(node.id)
			if level not in levels:
				levels[level] = []
			levels[level].append(node)
			
			# Process children
			children = [graph.nodes[edge.target] for edge in graph.edges 
					   if edge.source == node.id]
			for child in children:
				assign_level(child, level + 1)
				
		# Start from root nodes
		for root in root_nodes:
			assign_level(root, 0)
			
		return levels

	def _gis_network_layout(self, graph: MusicTheoryGraph, params: Dict) -> MusicTheoryGraph:
		new_graph = MusicTheoryGraph()
		level_spacing = params.get('level_spacing', 1.5)
		node_spacing = params.get('node_spacing', 1.2)
		
		# Group nodes by GIS space
		gis_spaces = [n for n in graph.nodes.values() if n.type == NodeType.GIS_SPACE]
		network_nodes = [n for n in graph.nodes.values() if n.type == NodeType.NETWORK_NODE]
		transformations = [n for n in graph.nodes.values() if n.type == NodeType.TRANSFORMATION]
		
		# Position GIS spaces at top level
		for i, node in enumerate(gis_spaces):
			position = (node_spacing * i, 0)
			new_graph.add_node(Node(
				id=node.id, type=node.type, label=node.label,
				properties=node.properties, position=position
			))
		
		# Position network nodes in middle level
		for i, node in enumerate(network_nodes):
			position = (node_spacing * i, -level_spacing)
			new_graph.add_node(Node(
				id=node.id, type=node.type, label=node.label,
				properties=node.properties, position=position
			))
		
		# Position transformations at bottom
		for i, node in enumerate(transformations):
			position = (node_spacing * i, -2 * level_spacing)
			new_graph.add_node(Node(
				id=node.id, type=node.type, label=node.label,
				properties=node.properties, position=position
			))
		
		# Copy edges
		for edge in graph.edges:
			new_graph.add_edge(edge)
		
		return new_graph

	def _isomorphic_network_layout(self, graph: MusicTheoryGraph, params: Dict) -> MusicTheoryGraph:
		new_graph = MusicTheoryGraph()
		spacing = params.get('spacing', 2.0)
		vertical_spacing = params.get('vertical_spacing', 1.5)
		
		# Split into parallel networks
		networks = self._split_isomorphic_networks(graph)
		
		# Find isomorphism pairs
		iso_pairs = []
		for edge in graph.edges:
			if edge.is_isomorphism:
				iso_pairs.append((edge.source, edge.target))
		
		# Layout each network with vertical alignment for isomorphic nodes
		for i, network in enumerate(networks):
			# Use transformation network layout as base
			network_params = params.copy()
			network_params['layout_style'] = 'hierarchical'
			network_graph = self._transformation_network_layout(network, network_params)
			
			# Calculate vertical offset based on isomorphism relationships
			vertical_offset = 0
			if i > 0:
				# Check if this network has isomorphic relationships with previous ones
				for src, tgt in iso_pairs:
					if src in network.nodes or tgt in network.nodes:
						vertical_offset = vertical_spacing
						break
			
			# Add nodes with offset
			offset = (i * spacing * 3, vertical_offset)
			for node in network_graph.nodes.values():
				if node.position:
					new_position = (
						node.position[0] + offset[0],
						node.position[1] + offset[1]
					)
					new_graph.add_node(Node(
						id=node.id,
						type=node.type,
						label=node.label,
						properties=node.properties,
						position=new_position
					))
		
		# Add all edges including isomorphisms
		for edge in graph.edges:
			if edge.is_isomorphism:
				# Adjust isomorphism edges to be more visible
				edge.properties['style'] = 'dashed'
				edge.properties['weight'] = 2.0
			new_graph.add_edge(edge)
		
		return new_graph

	def _split_isomorphic_networks(self, graph: MusicTheoryGraph) -> List[MusicTheoryGraph]:
		networks = []
		visited = set()
		
		# Find connected components excluding isomorphism edges
		def dfs(node_id: str, current_network: MusicTheoryGraph):
			if node_id in visited:
				return
			visited.add(node_id)
			node = graph.nodes[node_id]
			current_network.add_node(node)
			
			# Add connected nodes through non-isomorphism edges
			for edge in graph.edges:
				if edge.source == node_id and not edge.is_isomorphism:
					current_network.add_edge(edge)
					dfs(edge.target, current_network)
				elif edge.target == node_id and not edge.is_isomorphism:
					current_network.add_edge(edge)
					dfs(edge.source, current_network)
		
		# Process nodes in order of their type to maintain hierarchy
		node_order = [NodeType.GIS_SPACE, NodeType.NETWORK_NODE, NodeType.TRANSFORMATION]
		for node_type in node_order:
			for node_id, node in graph.nodes.items():
				if node.type == node_type and node_id not in visited:
					new_network = MusicTheoryGraph()
					dfs(node_id, new_network)
					if new_network.nodes:
						networks.append(new_network)
		
		# Process any remaining nodes
		for node_id in graph.nodes:
			if node_id not in visited:
				new_network = MusicTheoryGraph()
				dfs(node_id, new_network)
				if new_network.nodes:
					networks.append(new_network)
		
		return networks