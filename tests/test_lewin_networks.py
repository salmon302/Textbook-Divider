import unittest
import numpy as np
import cv2
import time
from graph_extractor.pattern_detector import PatternDetector, LayoutType
from graph_extractor.graph_types import NodeType, Node, MusicTheoryGraph
from graph_extractor.graph_layout import GraphLayout
from graph_extractor.graph_analyzer import GraphAnalyzer

class TestLewinNetworks(unittest.TestCase):
	def setUp(self):
		self.pattern_detector = PatternDetector()
		self.graph_layout = GraphLayout()
		
	def test_gis_network_detection(self):
		# Create a sample GIS network image
		img = np.ones((400, 600, 3), dtype=np.uint8) * 255
		# Draw nodes and edges for testing
		cv2.circle(img, (100, 100), 20, (0, 0, 255), 2)  # GIS space node
		cv2.circle(img, (300, 200), 20, (0, 0, 255), 2)  # Network node
		cv2.circle(img, (500, 300), 20, (0, 0, 255), 2)  # Transformation node
		cv2.line(img, (100, 100), (300, 200), (0, 0, 255), 2)  # Edge
		cv2.line(img, (300, 200), (500, 300), (0, 0, 255), 2)  # Edge
		
		# Add labels for node types
		cv2.putText(img, "GIS", (80, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
		cv2.putText(img, "NET", (280, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
		cv2.putText(img, "TRAN", (480, 290), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
		
		network = self.pattern_detector.detect_network(img)
		self.assertEqual(len(network.nodes), 3)
		self.assertEqual(len(network.edges), 2)
		self.assertGreater(network.confidence, 0.7)
		
	def test_isomorphic_network_detection(self):
		# Create a sample isomorphic network image
		img = np.ones((400, 800, 3), dtype=np.uint8) * 255
		# Draw two parallel networks with isomorphism
		cv2.circle(img, (100, 100), 20, (0, 0, 255), 2)
		cv2.circle(img, (300, 100), 20, (0, 0, 255), 2)
		cv2.circle(img, (500, 100), 20, (0, 0, 255), 2)
		cv2.circle(img, (700, 100), 20, (0, 0, 255), 2)
		cv2.line(img, (100, 100), (300, 100), (0, 0, 255), 2)
		cv2.line(img, (500, 100), (700, 100), (0, 0, 255), 2)
		cv2.line(img, (300, 100), (500, 100), (0, 0, 255), 2)  # Isomorphism edge
		
		# Add labels and symbols
		cv2.putText(img, "A", (90, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
		cv2.putText(img, "B", (290, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
		cv2.putText(img, "A'", (490, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
		cv2.putText(img, "B'", (690, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
		cv2.putText(img, "≅", (390, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
		
		network = self.pattern_detector.detect_network(img)
		self.assertEqual(len(network.nodes), 4)
		self.assertEqual(len(network.edges), 3)
		
		# Test layout
		graph = MusicTheoryGraph()
		for node in network.nodes:
			graph.add_node(node)
		for edge in network.edges:
			graph.add_edge(edge)
			
		laid_out = self.graph_layout.apply_layout(graph, 'isomorphic_network')
		self.assertTrue(all(node.position is not None for node in laid_out.nodes.values()))
		
	def test_transformation_symbol_detection(self):
		# Create sample transformation symbols
		img = np.ones((200, 600, 3), dtype=np.uint8) * 255
		# Add test symbols
		cv2.putText(img, "∘", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
		cv2.putText(img, "⊗", (150, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
		cv2.putText(img, "RICH", (250, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
		cv2.putText(img, "TCH", (350, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
		
		transform_type, confidence = self.pattern_detector.detect_transformation_type(img)
		self.assertIsNotNone(transform_type)
		self.assertGreater(confidence, 0.7)
		
	def test_analyzer_caching(self):
		"""Test that caching improves performance"""
		# Create a large test graph
		img = np.ones((800, 1200, 3), dtype=np.uint8) * 255
		for i in range(10):
			for j in range(10):
				cv2.circle(img, (100 + i*100, 100 + j*50), 20, (0, 0, 255), 2)
				if j > 0:
					cv2.line(img, (100 + i*100, 100 + j*50), 
							(100 + i*100, 100 + (j-1)*50), (0, 0, 255), 2)
		
		network = self.pattern_detector.detect_network(img)
		analyzer = GraphAnalyzer(network)
		
		# First call - should take longer
		start = time.time()
		cycles1 = analyzer.find_transformation_cycles()
		time1 = time.time() - start
		
		# Second call - should be faster due to caching
		start = time.time()
		cycles2 = analyzer.find_transformation_cycles()
		time2 = time.time() - start
		
		self.assertLess(time2, time1)
		self.assertEqual(cycles1, cycles2)
		
	def test_transformation_subgraph(self):
		"""Test that transformation subgraph optimization works"""
		graph = MusicTheoryGraph()
		# Add mix of transformation and regular nodes
		for i in range(5):
			graph.add_node(Node(id=f"t{i}", type=NodeType.TRANSFORMATION))
			graph.add_node(Node(id=f"r{i}", type=NodeType.REGULAR))
		
		analyzer = GraphAnalyzer(graph)
		analysis = analyzer.analyze_transformation_network()
		
		self.assertEqual(analysis['num_transformations'], 5)
		self.assertIn('centrality', analysis)
		self.assertIn('betweenness', analysis)

if __name__ == '__main__':
	unittest.main()