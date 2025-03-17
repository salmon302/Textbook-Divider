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

    def detect_layout(self, image: np.ndarray) -> LayoutType:
        """Detect the layout type of the network in the image"""
        # Basic layout detection based on node distribution
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) > 2 else image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return LayoutType.COMPLEX
        
        # Analyze contour distribution
        centers = []
        for cnt in contours:
            M = cv2.moments(cnt)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                centers.append((cx, cy))
        
        if len(centers) < 2:
            return LayoutType.COMPLEX
        
        # Check if centers form a circular pattern
        center_x = sum(x for x, _ in centers) / len(centers)
        center_y = sum(y for _, y in centers) / len(centers)
        distances = [np.sqrt((x - center_x)**2 + (y - center_y)**2) for x, y in centers]
        std_dev = np.std(distances)
        
        if std_dev < 20:  # Threshold for circular layout
            return LayoutType.CIRCULAR
        
        # Check if centers form a linear pattern
        x_coords = [x for x, _ in centers]
        y_coords = [y for _, y in centers]
        x_std = np.std(x_coords)
        y_std = np.std(y_coords)
        
        if min(x_std, y_std) < 20:  # Threshold for linear layout
            return LayoutType.LINEAR
        
        return LayoutType.COMPLEX

    def detect_nodes(self, image: np.ndarray) -> List[Node]:
        """Detect nodes in the image"""
        nodes = []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) > 2 else image
        
        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY_INV, 11, 2)
        
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for i, cnt in enumerate(contours):
            area = cv2.contourArea(cnt)
            if area > 100:  # Filter small noise
                x, y, w, h = cv2.boundingRect(cnt)
                confidence = min(area / 1000, 1.0)  # Scale confidence based on area
                
                position = (x + w//2, y + h//2)
                
                node = Node(
                    id=f"node_{i}",
                    label=f"N{i}",
                    type=NodeType.FUNCTION_SPACE,  # Default type
                    properties={
                        "confidence": confidence,
                        "size": (w, h)
                    },
                    position=position
                )
                nodes.append(node)
        
        return nodes

    def detect_edges(self, image: np.ndarray, nodes: List[Node]) -> List[Edge]:
        """Detect edges between nodes"""
        edges = []
        if len(nodes) < 2:
            return edges
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) > 2 else image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        lines = cv2.HoughLinesP(binary, 1, np.pi/180, 50, minLineLength=30, maxLineGap=10)
        
        if lines is None:
            return edges
        
        for i, line in enumerate(lines):
            x1, y1, x2, y2 = line[0]
            source_node = None
            target_node = None
            min_dist_start = float('inf')
            min_dist_end = float('inf')
            
            for node in nodes:
                pos = node.position if node.position else (0, 0)
                dist_start = np.sqrt((pos[0] - x1)**2 + (pos[1] - y1)**2)
                dist_end = np.sqrt((pos[0] - x2)**2 + (pos[1] - y2)**2)
                
                if dist_start < min_dist_start:
                    min_dist_start = dist_start
                    source_node = node
                if dist_end < min_dist_end:
                    min_dist_end = dist_end
                    target_node = node
            
            if source_node and target_node and source_node != target_node:
                edge = Edge(
                    source=source_node.id,
                    target=target_node.id,
                    label="transform",
                    weight=1.0,
                    properties={
                        "confidence": max(0.0, min(1.0 - (min_dist_start + min_dist_end) / 200, 1.0)),
                        "is_isomorphism": False
                    }
                )
                edges.append(edge)
        
        return edges


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
