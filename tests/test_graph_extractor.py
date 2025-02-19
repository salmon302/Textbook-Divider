import unittest
import cv2
import numpy as np
import os
from src.textbook_divider.graph_extractor import GraphExtractor, GraphNode, GraphEdge

class TestGraphExtractor(unittest.TestCase):
	def setUp(self):
		self.extractor = GraphExtractor()
		self.test_data_dir = os.path.join(os.path.dirname(__file__), 'data', 'graphs')
		os.makedirs(self.test_data_dir, exist_ok=True)

	def test_node_detection(self):
		"""Test detection of nodes in a simple graph"""
		img = np.zeros((200, 200), dtype=np.uint8)
		cv2.circle(img, (50, 50), 20, 255, 2)
		cv2.circle(img, (150, 150), 20, 255, 2)
		
		nodes, _ = self.extractor.extract_graph(cv2.cvtColor(img, cv2.COLOR_GRAY2BGR))
		
		self.assertEqual(len(nodes), 2)
		self.assertEqual(nodes[0].type, 'pitch_class')

	def test_edge_detection(self):
		"""Test detection of edges between nodes"""
		img = np.zeros((200, 200), dtype=np.uint8)
		cv2.circle(img, (50, 50), 20, 255, 2)
		cv2.circle(img, (150, 150), 20, 255, 2)
		cv2.line(img, (50, 50), (150, 150), 255, 2)
		
		nodes, edges = self.extractor.extract_graph(cv2.cvtColor(img, cv2.COLOR_GRAY2BGR))
		
		self.assertEqual(len(edges), 1)
		self.assertEqual(edges[0].type, 'arrow')

	def test_mathematical_notation(self):
		"""Test extraction of mathematical notation"""
		img = np.zeros((200, 200), dtype=np.uint8)
		cv2.circle(img, (100, 100), 20, 255, 2)
		cv2.putText(img, "T5", (80, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, 255, 2)
		
		nodes, _ = self.extractor.extract_graph(cv2.cvtColor(img, cv2.COLOR_GRAY2BGR))
		
		self.assertEqual(len(nodes), 1)
		self.assertIn("T5", nodes[0].label)

if __name__ == '__main__':
	unittest.main()
