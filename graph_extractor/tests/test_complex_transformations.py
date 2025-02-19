import pytest
import numpy as np
from pathlib import Path
from ..graph_types import MusicTheoryGraph, Node, Edge, NodeType
from ..graph_layout import GraphLayout
from ..graph_visualizer import GraphVisualizer

def test_complex_transformation_network():
	"""Test visualization of complex transformation network from Lewin p.235"""
	graph = MusicTheoryGraph()
	
	# Add nodes for the node/arrow system
	nodes = ['N1', 'N2']
	for n in nodes:
		node = Node(
			id=f"node_{n}",
			type=NodeType.SET_CLASS,
			label=n,
			properties={}
		)
		graph.add_node(node)
	
	# Add transformation nodes
	transforms = {
		'NODEMAP': NodeType.FUNCTION_SPACE,
		'SGMAP': NodeType.FUNCTION_SPACE,
		'TRANSIT': NodeType.FUNCTION_SPACE,
		"TRANSIT'": NodeType.FUNCTION_SPACE
	}
	for name, node_type in transforms.items():
		node = Node(
			id=f"func_{name}",
			type=node_type,
			label=name,
			properties={}
		)
		graph.add_node(node)
	
	# Add edges for homomorphism relationships
	edges = [
		('func_NODEMAP', 'node_N1', 'maps'),
		('func_NODEMAP', 'node_N2', 'maps'),
		('func_SGMAP', 'func_TRANSIT', 'transforms'),
		('func_TRANSIT', 'node_N1', 'applies_to'),
		('func_TRANSIT', 'node_N2', 'applies_to'),
		("func_TRANSIT'", 'func_NODEMAP', 'composed_with')
	]
	for src, tgt, label in edges:
		edge = Edge(source=src, target=tgt, label=label)
		graph.add_edge(edge)
	
	# Create visualizer and save test output
	visualizer = GraphVisualizer()
	visualizer.visualize_transformation_network(
		graph,
		filename="/tmp/test_complex_network.png"
	)
	
	# Verify file was created and basic properties
	assert Path("/tmp/test_complex_network.png").exists()
	assert len(graph.nodes) == 6  # 2 set nodes + 4 function nodes
	assert len(graph.edges) == 6  # All relationships defined