import pytest
from ..pattern_detector import PatternDetector
from ..graph_types import NodeType

def test_directed_edge_with_math_operator():
	detector = PatternDetector()
	text = "T1 ∘ T2 maps C to D"
	graph = detector.detect_patterns(text)
	
	edges = list(graph.edges)
	assert any(e.label == "∘" for e in edges)
	assert any(e.source == "transformation_T1_0" for e in edges)

def test_circular_graph_detection():
	detector = PatternDetector()
	text = "circular graph {A, B, C, D}"
	graph = detector.detect_patterns(text)
	
	circular_nodes = [n for n in graph.nodes.values() if n.type == NodeType.CIRCULAR_GRAPH]
	assert len(circular_nodes) == 1
	assert len(circular_nodes[0].properties["nodes"]) == 4

def test_complex_transformation_network():
	detector = PatternDetector()
	text = "T1 ⊗ T2 → T3 ⊕ T4"
	graph = detector.detect_patterns(text)
	
	edges = list(graph.edges)
	assert any(e.label == "⊗" for e in edges)
	assert any(e.label == "⊕" for e in edges)
	assert any(e.label == "→" for e in edges)

def test_homomorphism_with_directed_edges():
	detector = PatternDetector()
	text = "f: A → B is a homomorphism where T1 ∘ T2 maps to S1"
	graph = detector.detect_patterns(text)
	
	edges = list(graph.edges)
	assert any(e.label == "→" for e in edges)
	assert any(e.label == "∘" for e in edges)
	assert any(n.type == NodeType.FUNCTION_SPACE for n in graph.nodes.values())
