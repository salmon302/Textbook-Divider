import unittest
from pathlib import Path
from graph_extractor.graph_types import MusicTheoryGraph, Node, Edge, NodeType

class TestBasicGraph(unittest.TestCase):
	def setUp(self):
		self.graph = MusicTheoryGraph()
		
	def test_node_creation(self):
		"""Test basic node creation and addition"""
		node = Node(
			id="pc_C",
			type=NodeType.PITCH_CLASS,
			label="C",
			properties={"octave": 4}
		)
		self.graph.add_node(node)
		self.assertEqual(len(self.graph.nodes), 1)
		self.assertEqual(self.graph.get_node("pc_C"), node)
		
	def test_edge_creation(self):
		"""Test basic edge creation and addition"""
		node1 = Node(
			id="pc_C",
			type=NodeType.PITCH_CLASS,
			label="C",
			properties={}
		)
		node2 = Node(
			id="pc_G",
			type=NodeType.PITCH_CLASS,
			label="G",
			properties={}
		)
		self.graph.add_node(node1)
		self.graph.add_node(node2)
		
		edge = Edge(
			source="pc_C",
			target="pc_G",
			label="fifth",
			weight=1.0
		)
		self.graph.add_edge(edge)
		self.assertEqual(len(self.graph.edges), 1)
		
	def test_invalid_edge(self):
		"""Test edge creation with invalid nodes"""
		edge = Edge(
			source="nonexistent1",
			target="nonexistent2",
			label="invalid"
		)
		self.graph.add_edge(edge)
		self.assertEqual(len(self.graph.edges), 0)

if __name__ == '__main__':
	unittest.main(verbosity=2)