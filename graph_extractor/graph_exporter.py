import json
import networkx as nx
from typing import Dict, Any
from .graph_types import MusicTheoryGraph

class GraphExporter:
	@staticmethod
	def to_json(graph: MusicTheoryGraph) -> str:
		"""Export graph to JSON format"""
		data = {
			"nodes": [
				{
					"id": node.id,
					"type": node.type.value,
					"label": node.label,
					"properties": node.properties
				}
				for node in graph.nodes.values()
			],
			"edges": [
				{
					"source": edge.source,
					"target": edge.target,
					"label": edge.label,
					"weight": edge.weight,
					"properties": edge.properties
				}
				for edge in graph.edges
			]
		}
		return json.dumps(data, indent=2)
	
	@staticmethod
	def to_networkx(graph: MusicTheoryGraph) -> nx.Graph:
		"""Convert to NetworkX graph for analysis"""
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
				**(edge.properties or {})
			)
			
		return G
		
	@staticmethod
	def to_graphviz(graph: MusicTheoryGraph) -> str:
		"""Export graph to GraphViz DOT format"""
		dot_str = ["digraph G {"]
		
		# Add nodes
		for node in graph.nodes.values():
			label = f"{node.label} ({node.type.value})"
			dot_str.append(f'    "{node.id}" [label="{label}"];')
			
		# Add edges
		for edge in graph.edges:
			dot_str.append(
				f'    "{edge.source}" -> "{edge.target}" '
				f'[label="{edge.label}",weight="{edge.weight}"];'
			)
			
		dot_str.append("}")
		return "\n".join(dot_str)