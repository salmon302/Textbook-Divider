from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Tuple
from enum import Enum

class NodeType(Enum):
	PITCH_CLASS = "pitch_class"
	INTERVAL = "interval"
	TRANSFORMATION = "transformation"
	SET_CLASS = "set_class"
	GEOMETRIC_POINT = "geometric_point"
	FUNCTION_SPACE = "function_space"
	GROUP = "group"
	INTERVAL_SYSTEM = "interval_system"
	INTERVAL_SET = "interval_set"
	VARIABLE = "variable"
	CIRCULAR_GRAPH = "circular_graph"
	# New Lewin-specific types
	TRANSFORMATION_NETWORK = "transformation_network"
	GIS_SPACE = "gis_space"
	TRANSFORMATION_GROUP = "transformation_group"
	INTERVAL_FUNCTION = "interval_function"
	NETWORK_NODE = "network_node"

@dataclass
class Node:
	id: str
	type: NodeType
	label: str
	properties: Dict[str, any]
	position: Optional[Tuple[float, float]] = None

@dataclass
class Edge:
	source: str
	target: str
	label: str
	weight: float = 1.0
	properties: Dict[str, any] = None
	# New properties for Lewin's transformations
	transformation_type: Optional[str] = None
	composition: Optional[List[str]] = None
	is_isomorphism: bool = False

	def __post_init__(self):
		if self.properties is None:
			self.properties = {}

class MusicTheoryGraph:
	def __init__(self):
		self.nodes: Dict[str, Node] = {}
		self.edges: List[Edge] = []
		
	def add_node(self, node: Node) -> None:
		self.nodes[node.id] = node
		
	def add_edge(self, edge: Edge) -> None:
		if edge.source in self.nodes and edge.target in self.nodes:
			self.edges.append(edge)
			
	def get_node(self, node_id: str) -> Optional[Node]:
		return self.nodes.get(node_id)