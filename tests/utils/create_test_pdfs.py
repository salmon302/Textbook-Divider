import os
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import shutil

def create_test_pdfs():
	output_dir = Path(__file__).parent.parent / "sample_books"
	output_dir.mkdir(parents=True, exist_ok=True)
	
	# Ensure OMR input directory exists
	omr_dir = Path(__file__).parent.parent.parent / "data/input/OMR"
	if not omr_dir.exists():
		omr_dir.mkdir(parents=True, exist_ok=True)
	
	# Define test files
	test_files = {
		'basic_score.pdf': create_basic_score,
		'complex_notation.pdf': create_complex_score,
		'modern_score.pdf': create_contemporary_score,
		'mixed_layout.pdf': create_mixed_content,
		'corrupted_score.pdf': create_malformed_score,
		'low_res_score.pdf': create_poor_quality_score
	}
	
	# Generate test files
	for filename, generator in test_files.items():
		output_path = output_dir / filename
		generator(output_path)
		print(f"Created {filename}")

def create_basic_score(output_path):
	"""Create a simple single staff score"""
	c = canvas.Canvas(str(output_path), pagesize=letter)
	c.drawString(100, 750, "Basic Musical Score")
	# Draw staff lines
	y_start = 600
	for i in range(5):
		c.line(100, y_start - i*10, 500, y_start - i*10)
	c.save()

def create_complex_score(output_path):
	"""Create a complex score with multiple staves"""
	c = canvas.Canvas(str(output_path), pagesize=letter)
	c.drawString(100, 750, "Complex Musical Score")
	# Draw multiple staff systems
	for system in range(3):
		y_start = 600 - system*100
		for i in range(5):
			c.line(100, y_start - i*10, 500, y_start - i*10)
	c.save()

def create_contemporary_score(output_path):
	"""Create a contemporary notation score"""
	c = canvas.Canvas(str(output_path), pagesize=letter)
	c.drawString(100, 750, "Contemporary Musical Score")
	# Draw non-standard notation elements
	y_start = 600
	for i in range(5):
		c.line(100, y_start - i*15, 500, y_start - i*15)
	c.save()

def create_mixed_content(output_path):
	"""Create a score with mixed text and music"""
	c = canvas.Canvas(str(output_path), pagesize=letter)
	c.drawString(100, 750, "Mixed Content Score")
	# Add text
	c.drawString(100, 700, "Chapter 1: Musical Examples")
	# Draw staff
	y_start = 600
	for i in range(5):
		c.line(100, y_start - i*10, 500, y_start - i*10)
	c.save()

def create_malformed_score(output_path):
	"""Create an intentionally malformed score"""
	c = canvas.Canvas(str(output_path), pagesize=letter)
	c.drawString(100, 750, "Malformed Score")
	# Draw incomplete/broken staff lines
	y_start = 600
	for i in range(5):
		c.line(100, y_start - i*10, 300, y_start - i*10)
	c.save()

def create_poor_quality_score(output_path):
	"""Create a low resolution/quality score"""
	c = canvas.Canvas(str(output_path), pagesize=(300, 400))
	c.drawString(50, 350, "Low Quality Score")
	# Draw low quality staff lines
	y_start = 300
	for i in range(5):
		c.line(50, y_start - i*5, 250, y_start - i*5)
	c.save()

if __name__ == '__main__':
	create_test_pdfs()

