import pytest
from graph_extractor.pattern_detector import PatternDetector
from graph_extractor.graph_types import NodeType, MusicTheoryGraph

def test_basic_transformation_detection():
	detector = PatternDetector()
	text = "The transformation T1 maps C to C#"
	graph = detector.detect_patterns(text)
	
	assert len(graph.nodes) == 3
	assert any(n.type == NodeType.TRANSFORMATION for n in graph.nodes.values())
	assert any(n.type == NodeType.PITCH_CLASS for n in graph.nodes.values())

def test_interval_system():
	detector = PatternDetector()
	text = "The interval system IVLS contains P5 and M3"
	graph = detector.detect_patterns(text)
	
	assert len(graph.nodes) == 2
	assert all(n.type == NodeType.INTERVAL for n in graph.nodes.values())

def test_complex_transformation():
	detector = PatternDetector()
	text = "The composition T4∘T7 transforms Eb to G"
	graph = detector.detect_patterns(text)
	
	trans_nodes = [n for n in graph.nodes.values() if n.type == NodeType.TRANSFORMATION]
	assert len(trans_nodes) == 1
	assert trans_nodes[0].label == "T4∘T7"

def test_graph_connectivity():
	detector = PatternDetector()
	text = "T1 maps C to D, while T2 maps D to E"
	graph = detector.detect_patterns(text)
	
	assert len(graph.edges) >= 4  # Should have edges between transformations and pitch classes
	assert any(e.label == "transforms" for e in graph.edges)

def test_mathematical_notation():
	detector = PatternDetector()
	text = "s ∈ IVLS, where s: p → q"
	graph = detector.detect_patterns(text)
	
	assert len(graph.nodes) >= 3
	assert any(n.label == "s" for n in graph.nodes.values())

def test_homomorphism_detection():
	detector = PatternDetector()
	text = "NODEMAP is a homomorphism of the node/arrow system (NODES, ARROW) into/onto the system (NODES', ARROW)"
	graph = detector.detect_patterns(text)
	
	assert any(n.label == "NODEMAP" for n in graph.nodes.values())
	assert any(n.type == NodeType.FUNCTION_SPACE for n in graph.nodes.values())

def test_semigroup_mapping():
	detector = PatternDetector()
	text = "SGMAP is a homomorphism of the semigroup SGP into/onto the semigroup SGP'"
	graph = detector.detect_patterns(text)
	
	assert any(n.label == "SGMAP" for n in graph.nodes.values())
	assert any(n.label == "SGP" for n in graph.nodes.values())

def test_transit_relation():
	detector = PatternDetector()
	text = "TRANSIT'(NODEMAP(N1), NODEMAP(N2)) = SGMAP(TRANSIT(N1, N2))"
	graph = detector.detect_patterns(text)
	
	transit_nodes = [n for n in graph.nodes.values() if "TRANSIT" in n.label]
	assert len(transit_nodes) >= 2  # Should detect both TRANSIT and TRANSIT'

def test_brahms_example():
	detector = PatternDetector()
	text = "The intervallic augmentation that transforms graph (a) into graph (b) is in fact a formal homomorphism"
	graph = detector.detect_patterns(text)
	
	assert any(n.type == NodeType.TRANSFORMATION for n in graph.nodes.values())
	assert len(graph.edges) >= 1  # Should have transformation edge

def test_interval_mapping():
	detector = PatternDetector()
	text = "Take SGMAP to be the mapping of the interval i into the interval 2i"
	graph = detector.detect_patterns(text)
	
	assert any(n.label == "SGMAP" for n in graph.nodes.values())
	assert any(n.type == NodeType.INTERVAL for n in graph.nodes.values())
