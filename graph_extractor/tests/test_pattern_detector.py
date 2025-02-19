import unittest
from graph_extractor.pattern_detector import PatternDetector
from graph_extractor.graph_types import NodeType

class TestPatternDetector(unittest.TestCase):
	def setUp(self):
		self.detector = PatternDetector()
		
	def test_pitch_class_detection(self):
		"""Test detection of pitch classes from text"""
		test_text = """
		The pitch classes C and G form a perfect fifth interval,
		while D♭ and A♭ form another fifth relationship.
		"""
		print(f"Test text (repr): {repr(test_text)}")
		print(f"Test text (bytes): {test_text.encode('utf-8')}")
		
		graph = self.detector.detect_patterns(test_text)
		
		pitch_classes = [n for n in graph.nodes.values() 
						if n.type == NodeType.PITCH_CLASS]
		print(f"Found pitch classes: {[n.label for n in pitch_classes]}")
		
		self.assertEqual(len(pitch_classes), 4)
		
		labels = {n.label for n in pitch_classes}
		self.assertEqual(labels, {'C', 'G', 'D♭', 'A♭'})
		
	def test_interval_detection(self):
		"""Test detection of intervals from text"""
		test_text = """
		The interval of a perfect fifth (P5) between C and G,
		and a major third (M3) between C and E.
		"""
		graph = self.detector.detect_patterns(test_text)
		
		intervals = [n for n in graph.nodes.values() 
					if n.type == NodeType.INTERVAL]
		self.assertEqual(len(intervals), 2)
		
		labels = {n.label for n in intervals}
		self.assertEqual(labels, {'P5', 'M3'})
		
	def test_transformation_detection(self):
		"""Test detection of transformations from text"""
		test_text = """
		The transformation T1 maps C to D♭, while T2 maps D♭ to E.
		The composite transformation T2∘T1 maps C directly to E.
		"""
		graph = self.detector.detect_patterns(test_text)
		
		transformations = [n for n in graph.nodes.values() 
						 if n.type == NodeType.TRANSFORMATION]
		self.assertEqual(len(transformations), 3)
		
		labels = {n.label for n in transformations}
		self.assertEqual(labels, {'T1', 'T2', 'T2∘T1'})

if __name__ == '__main__':
	unittest.main(verbosity=2)