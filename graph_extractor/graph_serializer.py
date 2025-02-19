import json
import pickle
from typing import Dict, Any, Optional
from pathlib import Path
import networkx as nx
from .graph_types import MusicTheoryGraph, Node, Edge, NodeType

class GraphSerializer:
	def __init__(self):
		self.supported_formats = {
			'json': self._save_json,
			'pickle': self._save_pickle,
			'graphml': self._save_graphml
		}
		
	def save(self, graph: MusicTheoryGraph, 
			 filepath: str, 
			 format: str = 'json') -> None:
		if format not in self.supported_formats:
			raise ValueError(f"Unsupported format: {format}")
			
		save_func = self.supported_formats[format]
		save_func(graph, filepath)
		
	def load(self, filepath: str, format: Optional[str] = None) -> MusicTheoryGraph:
		if format is None:
			format = Path(filepath).suffix[1:]
			
		if format not in self.supported_formats:
			raise ValueError(f"Unsupported format: {format}")
			
		if format == 'json':
			return self._load_json(filepath)
		elif format == 'pickle':
			return self._load_pickle(filepath)
		else:
			return self._load_graphml(filepath)
			
	def _save_json(self, graph: MusicTheoryGraph, filepath: str) -> None:
		data = {
			'nodes': [
				{
					'id': node.id,
					'type': node.type.value,
					'label': node.label,
					'properties': node.properties,
					'position': node.position
				}
				for node in graph.nodes.values()
			],
			'edges': [
				{
					'source': edge.source,
					'target': edge.target,
					'label': edge.label,
					'weight': edge.weight,
					'properties': edge.properties
				}
				for edge in graph.edges
			]
		}
		
		with open(filepath, 'w') as f:
			json.dump(data, f, indent=2)
			
	def _save_pickle(self, graph: MusicTheoryGraph, filepath: str) -> None:
		with open(filepath, 'wb') as f:
			pickle.dump(graph, f)
			
	def _save_graphml(self, graph: MusicTheoryGraph, filepath: str) -> None:
		G = nx.Graph()
		
		# Add nodes with attributes
		for node in graph.nodes.values():
			G.add_node(
				node.id,
				type=node.type.value,
				label=node.label,
				**node.properties
			)
			
		# Add edges with attributes
		for edge in graph.edges:
			G.add_edge(
				edge.source,
				edge.target,
				label=edge.label,
				weight=edge.weight,
				**edge.properties
			)
			
		nx.write_graphml(G, filepath)
		
	def _load_json(self, filepath: str) -> MusicTheoryGraph:
		with open(filepath, 'r') as f:
			data = json.load(f)
			
		graph = MusicTheoryGraph()
		
		# Load nodes
		for node_data in data['nodes']:
			node = Node(
				id=node_data['id'],
				type=NodeType(node_data['type']),
				label=node_data['label'],
				properties=node_data['properties'],
				position=tuple(node_data['position']) if node_data.get('position') else None
			)
			graph.add_node(node)
			
		# Load edges
		for edge_data in data['edges']:
			edge = Edge(
				source=edge_data['source'],
				target=edge_data['target'],
				label=edge_data['label'],
				weight=edge_data['weight'],
				properties=edge_data['properties']
			)
			graph.add_edge(edge)
			
		return graph
		
	def _load_pickle(self, filepath: str) -> MusicTheoryGraph:
		with open(filepath, 'rb') as f:
			return pickle.load(f)
			
	def _load_graphml(self, filepath: str) -> MusicTheoryGraph:
		G = nx.read_graphml(filepath)
		graph = MusicTheoryGraph()
		
		# Convert nodes
		for node_id, data in G.nodes(data=True):
			node = Node(
				id=node_id,
				type=NodeType(data['type']),
				label=data['label'],
				properties={k: v for k, v in data.items() 
						  if k not in ['type', 'label']}
			)
			graph.add_node(node)
			
		# Convert edges
		for u, v, data in G.edges(data=True):
			edge = Edge(
				source=u,
				target=v,
				label=data.get('label', ''),
				weight=float(data.get('weight', 1.0)),
				properties={k: v for k, v in data.items() 
						  if k not in ['label', 'weight']}
			)
			graph.add_edge(edge)
			
		return graph