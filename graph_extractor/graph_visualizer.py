import networkx as nx
import matplotlib.pyplot as plt
from typing import Optional, Dict, Any
from .graph_types import MusicTheoryGraph, NodeType

class GraphVisualizer:
	def __init__(self):
		self.node_colors = {
			NodeType.PITCH_CLASS: '#ff7f7f',
			NodeType.INTERVAL: '#7f7f7f',
			NodeType.TRANSFORMATION: '#7fff7f',
			NodeType.SET_CLASS: '#ff7fff',
			NodeType.GEOMETRIC_POINT: '#ffff7f',
			NodeType.FUNCTION_SPACE: '#7fffff',
			NodeType.GROUP: '#ffaf7f'
		}
		self.node_shapes = {
			NodeType.PITCH_CLASS: 'o',      # circle
			NodeType.TRANSFORMATION: 's',    # square
			NodeType.FUNCTION_SPACE: 'D',    # diamond
			NodeType.GROUP: '^'             # triangle
		}
		
	def visualize(self, graph: MusicTheoryGraph, 
				 layout: str = 'spring',
				 filename: Optional[str] = None) -> None:
		nx_graph = self._convert_to_networkx(graph)
		
		# Set up the plot
		plt.figure(figsize=(12, 8))
		
		# Get layout
		pos = self._get_layout(nx_graph, layout)
		
		# Draw nodes with shapes
		self._draw_nodes_with_shapes(nx_graph, pos)
		
		# Draw edges
		self._draw_edges(nx_graph, pos)
		
		# Add labels
		self._add_labels(nx_graph, pos)
		
		if filename:
			plt.savefig(filename)
		plt.show()
		
	def visualize_transformation_network(self, graph: MusicTheoryGraph,
									  filename: Optional[str] = None) -> None:
		nx_graph = self._convert_to_networkx(graph)
		plt.figure(figsize=(12, 8))
		
		# Use custom layout for transformation networks
		pos = self._get_transformation_layout(nx_graph)
		
		# Draw nodes with different shapes
		self._draw_nodes_with_shapes(nx_graph, pos)
		
		# Draw edges with mathematical labels
		self._draw_mathematical_edges(nx_graph, pos)
		
		if filename:
			plt.savefig(filename)
			plt.close()  # Close the figure to avoid the show() warning
		else:
			plt.show()
		
	def _convert_to_networkx(self, graph: MusicTheoryGraph) -> nx.Graph:
		G = nx.Graph()
		
		# Add nodes with attributes
		for node in graph.nodes.values():
			G.add_node(node.id, 
					  type=node.type,
					  label=node.label,
					  **node.properties)
		
		# Add edges with attributes
		for edge in graph.edges:
			G.add_edge(edge.source, 
					  edge.target,
					  label=edge.label,
					  **edge.properties)
		
		return G
		
	def _get_layout(self, G: nx.Graph, layout_type: str) -> Dict[str, Any]:
		layouts = {
			'spring': nx.spring_layout,
			'circular': nx.circular_layout,
			'spectral': nx.spectral_layout,
			'shell': nx.shell_layout
		}
		return layouts.get(layout_type, nx.spring_layout)(G)
		
	def _get_transformation_layout(self, G: nx.Graph) -> Dict[str, Any]:
		# Use positions from node attributes if available
		pos = {}
		for node, data in G.nodes(data=True):
			if 'position' in data:
				pos[node] = data['position']
		
		# Fall back to circular layout if no positions
		if not pos:
			pos = nx.circular_layout(G)
		return pos
		
	def _draw_nodes_with_shapes(self, G: nx.Graph, pos: Dict[str, Any]) -> None:
		for node_type in NodeType:
			node_list = [n for n, d in G.nodes(data=True) 
						if d.get('type') == node_type]
			if node_list:
				nx.draw_networkx_nodes(G, pos,
									 nodelist=node_list,
									 node_color=self.node_colors[node_type],
									 node_shape=self.node_shapes.get(node_type, 'o'),
									 node_size=1000)
									 
	def _draw_edges(self, G: nx.Graph, pos: Dict[str, Any]) -> None:
		nx.draw_networkx_edges(G, pos, width=2, alpha=0.5)
		
	def _draw_mathematical_edges(self, G: nx.Graph, pos: Dict[str, Any]) -> None:
		# Draw edges with arrows
		nx.draw_networkx_edges(G, pos, 
							 width=2, 
							 alpha=0.5,
							 arrows=True,  # Enable arrows
							 arrowsize=20,
							 edge_color='gray')
		
		# Add mathematical edge labels with LaTeX formatting
		edge_labels = {}
		for u, v, data in G.edges(data=True):
			if 'label' in data:
				# Convert common symbols to LaTeX
				label = data['label']
				label = label.replace('∘', r'$\circ$')
				label = label.replace('⊗', r'$\otimes$')
				label = label.replace('→', r'$\rightarrow$')
				edge_labels[(u, v)] = label
				
		nx.draw_networkx_edge_labels(G, pos, 
								   edge_labels, 
								   font_size=8,
								   bbox=dict(facecolor='white', 
										   edgecolor='none', 
										   alpha=0.7))
		
	def _add_labels(self, G: nx.Graph, pos: Dict[str, Any]) -> None:
		labels = {node: data.get('label', node) 
				 for node, data in G.nodes(data=True)}
		nx.draw_networkx_labels(G, pos, labels, font_size=8)
		
		edge_labels = nx.get_edge_attributes(G, 'label')
		nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=6)