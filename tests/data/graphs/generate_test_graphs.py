import cv2
import numpy as np
import os

def generate_simple_graph():
	"""Generate a simple graph with two nodes and an arrow"""
	img = np.zeros((200, 200), dtype=np.uint8)
	# Draw nodes
	cv2.circle(img, (50, 100), 20, 255, 2)
	cv2.circle(img, (150, 100), 20, 255, 2)
	# Draw arrow
	cv2.arrowedLine(img, (70, 100), (130, 100), 255, 2, tipLength=0.3)
	# Add labels
	cv2.putText(img, "C", (45, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 255, 2)
	cv2.putText(img, "G", (145, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 255, 2)
	cv2.putText(img, "T7", (90, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 255, 2)
	return img

def generate_triangle_graph():
	"""Generate a triangular graph with transformational labels"""
	img = np.zeros((300, 300), dtype=np.uint8)
	# Draw nodes in triangle formation
	points = [(50, 50), (250, 50), (150, 250)]
	labels = ["E", "G#", "B"]
	for (x, y), label in zip(points, labels):
		cv2.circle(img, (x, y), 20, 255, 2)
		cv2.putText(img, label, (x-5, y+5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 255, 2)
	
	# Draw arrows forming triangle
	cv2.arrowedLine(img, points[0], points[1], 255, 2, tipLength=0.2)
	cv2.arrowedLine(img, points[1], points[2], 255, 2, tipLength=0.2)
	cv2.arrowedLine(img, points[2], points[0], 255, 2, tipLength=0.2)
	
	# Add transformation labels
	midpoints = [
		((points[0][0] + points[1][0])//2, (points[0][1] + points[1][1])//2 - 15),
		((points[1][0] + points[2][0])//2, (points[1][1] + points[2][1])//2),
		((points[2][0] + points[0][0])//2, (points[2][1] + points[0][1])//2)
	]
	for pos, label in zip(midpoints, ["T4", "T3", "T5"]):
		cv2.putText(img, label, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 255, 2)
	return img

def generate_test_images():
	"""Generate all test images and save them"""
	output_dir = os.path.dirname(os.path.abspath(__file__))
	
	# Generate and save simple graph
	simple = generate_simple_graph()
	cv2.imwrite(os.path.join(output_dir, 'simple_graph.png'), simple)
	
	# Generate and save triangle graph
	triangle = generate_triangle_graph()
	cv2.imwrite(os.path.join(output_dir, 'triangle_graph.png'), triangle)

if __name__ == '__main__':
	generate_test_images()