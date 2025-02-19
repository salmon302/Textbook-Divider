import cv2
import numpy as np
import pytest
from ..pattern_detector import PatternDetector, LayoutType, Node, Edge, TransformationNetwork

def create_test_image(layout_type: LayoutType) -> np.ndarray:
	# Create a blank image
	image = np.zeros((400, 400), dtype=np.uint8)
	
	if layout_type == LayoutType.CIRCULAR:
		# Draw circular pattern
		center = (200, 200)
		radius = 100
		for i in range(4):
			angle = i * np.pi / 2
			x = int(center[0] + radius * np.cos(angle))
			y = int(center[1] + radius * np.sin(angle))
			cv2.circle(image, (x, y), 20, 255, -1)
			# Draw lines between nodes
			next_i = (i + 1) % 4
			next_x = int(center[0] + radius * np.cos(next_i * np.pi / 2))
			next_y = int(center[1] + radius * np.sin(next_i * np.pi / 2))
			cv2.line(image, (x, y), (next_x, next_y), 255, 2)
	
	elif layout_type == LayoutType.LINEAR:
		# Draw linear pattern
		for i in range(3):
			x = 100 + i * 100
			y = 200
			cv2.circle(image, (x, y), 20, 255, -1)
			if i < 2:
				cv2.line(image, (x+20, y), (x+80, y), 255, 2)
	
	return image

def test_layout_detection():
	detector = PatternDetector()
	
	# Test circular layout
	circular_image = create_test_image(LayoutType.CIRCULAR)
	assert detector.detect_layout(circular_image) == LayoutType.CIRCULAR
	
	# Test linear layout
	linear_image = create_test_image(LayoutType.LINEAR)
	assert detector.detect_layout(linear_image) == LayoutType.LINEAR

def test_node_detection():
	detector = PatternDetector()
	linear_image = create_test_image(LayoutType.LINEAR)
	nodes = detector.detect_nodes(linear_image)
	
	assert len(nodes) == 3
	for node in nodes:
		assert isinstance(node, Node)
		assert node.confidence > 0

def test_edge_detection():
	detector = PatternDetector()
	linear_image = create_test_image(LayoutType.LINEAR)
	nodes = detector.detect_nodes(linear_image)
	edges = detector.detect_edges(linear_image, nodes)
	
	assert len(edges) == 2
	for edge in edges:
		assert isinstance(edge, Edge)
		assert edge.confidence > 0

def test_network_detection():
	detector = PatternDetector()
	
	# Test with circular layout
	circular_image = create_test_image(LayoutType.CIRCULAR)
	network = detector.detect_network(circular_image)
	
	assert isinstance(network, TransformationNetwork)
	assert network.layout_type == LayoutType.CIRCULAR
	assert len(network.nodes) == 4
	assert len(network.edges) == 4
	assert network.confidence > 0