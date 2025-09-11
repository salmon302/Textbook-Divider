import unittest
import cv2
import numpy as np
from pathlib import Path
from graph_extractor.pattern_detector import PatternDetector
from graph_extractor.graph_layout import GraphLayout
from graph_extractor.graph_types import NodeType, MusicTheoryGraph

class TestLewinTransformations(unittest.TestCase):
	def setUp(self):
		self.pattern_detector = PatternDetector()
		self.graph_layout = GraphLayout()
		self.data_dir = Path('/home/seth-n/CLionProjects/Textbook Divider/data')
		self.lewin_pdf = self.data_dir / 'input' / 'David Lewin - Generalized Musical Intervals and Transformations (2007).pdf'
		
	def test_transformation_detection(self):
		# Create test image with transformation symbols
		img = np.ones((200, 400, 3), dtype=np.uint8) * 255
		symbols = ["∘", "⊗", "RICH", "TCH"]
		for i, symbol in enumerate(symbols):
			cv2.putText(img, symbol, (50 + i*100, 100), 
					   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
		
		# Test each symbol
		for i, symbol in enumerate(symbols):
			roi = img[:, i*100:(i+1)*100]
			detected, conf = self.pattern_detector.detect_transformation_type(roi)
			self.assertIsNotNone(detected)
			self.assertGreater(conf, 0.7)
	
	def test_isomorphic_network(self):
		# Create test image with parallel networks
		img = np.ones((300, 600, 3), dtype=np.uint8) * 255
		
		# Draw first network
		cv2.circle(img, (100, 100), 20, (0, 0, 0), 2)
		cv2.circle(img, (200, 100), 20, (0, 0, 0), 2)
		cv2.line(img, (120, 100), (180, 100), (0, 0, 0), 2)
		cv2.putText(img, "A", (90, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
		cv2.putText(img, "B", (190, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
		
		# Draw second network
		cv2.circle(img, (400, 100), 20, (0, 0, 0), 2)
		cv2.circle(img, (500, 100), 20, (0, 0, 0), 2)
		cv2.line(img, (420, 100), (480, 100), (0, 0, 0), 2)
		cv2.putText(img, "A'", (390, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
		cv2.putText(img, "B'", (490, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
		
		# Draw isomorphism
		cv2.putText(img, "≅", (290, 105), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
		cv2.line(img, (220, 100), (380, 100), (0, 0, 0), 1)
		
		# Test network detection
		network = self.pattern_detector.detect_network(img)
		self.assertEqual(len(network.nodes), 4)
		self.assertEqual(len(network.edges), 3)
		
		# Test layout
		layout_params = {'spacing': 2.0, 'vertical_spacing': 1.5}
		laid_out = self.graph_layout.apply_layout(network, 'isomorphic_network', layout_params)
		
		# Verify layout properties
		self.assertTrue(all(node.position is not None for node in laid_out.nodes.values()))
		self.assertTrue(any(edge.properties.get('style') == 'dashed' 
						  for edge in laid_out.edges))

if __name__ == '__main__':
	unittest.main()