import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from enum import Enum
from .graph_types import MusicTheoryGraph, Node, Edge, NodeType

class LayoutType(Enum):
    CIRCULAR = "circular"
    LINEAR = "linear"
    COMPLEX = "complex"

class TransformationNetwork:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self.layout_type: LayoutType = LayoutType.COMPLEX
        self.confidence: float = 0.0

    def add_node(self, node: Node) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)

    def __len__(self):
        return len(self.nodes)

class PatternDetector:
    def __init__(self):
        self.mathematical_symbols = {
            "∘", "⊗", "⊕", "→", "⟶", "↦", "⊆", "⊇", "≅", "≃", "∼",
            "∈", "∉", "⊂", "⊃", "∪", "∩", "×", "⋈", "≤", "≥"
        }
        self.transformation_labels = {
            "RICH", "TCH", "TRAN", "INT", "GIS", "STAB", "FLIP", "ROT"
        }
        self.gis_patterns = {
            "s", "t", "i", "int", "IVLS", "IVLS1", "IVLS2"
        }

    def detect_network(self, image: np.ndarray) -> TransformationNetwork:
        network = TransformationNetwork()
        network.layout_type = self.detect_layout(image)
        
        detected_nodes = self.detect_nodes(image)
        for node in detected_nodes:
            network.add_node(node)
        
        if detected_nodes:
            edges = self.detect_edges(image, detected_nodes)
            for edge in edges:
                network.add_edge(edge)
        
        node_confidences = [n.properties.get("confidence", 0.0) for n in network.nodes.values()]
        edge_confidences = [e.properties.get("confidence", 0.0) for e in network.edges]
        
        if node_confidences and edge_confidences:
            network.confidence = (sum(node_confidences) / len(node_confidences) + 
                                sum(edge_confidences) / len(edge_confidences)) / 2
        elif node_confidences:
            network.confidence = sum(node_confidences) / len(node_confidences)
        else:
            network.confidence = 0.0
        
        return network
