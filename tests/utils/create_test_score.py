#!/usr/bin/env python3
import cv2
import numpy as np
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_score_image():
	"""Create a basic score image"""
	img = np.full((800, 600), 255, dtype=np.uint8)
	
	# Draw staff lines
	for staff_num in range(3):  # 3 staff systems
		y_offset = 150 + staff_num * 200
		for i in range(5):  # 5 lines per staff
			y = y_offset + i * 20
			cv2.line(img, (50, y), (550, y), 0, 2)
	
		# Draw treble clef (simplified)
		cv2.ellipse(img, (80, y_offset + 50), (15, 20), 0, 0, 360, 0, 2)
		cv2.ellipse(img, (80, y_offset + 25), (10, 15), 0, 0, 360, 0, 2)
		
		# Draw time signature
		cv2.putText(img, "4", (120, y_offset + 35), cv2.FONT_HERSHEY_SIMPLEX, 1, 0, 2)
		cv2.putText(img, "4", (120, y_offset + 75), cv2.FONT_HERSHEY_SIMPLEX, 1, 0, 2)
		
		# Draw notes
		x_positions = [200, 300, 400, 500]
		for x in x_positions:
			cv2.circle(img, (x, y_offset + 50), 6, 0, -1)  # note head
			cv2.line(img, (x + 6, y_offset + 50), (x + 6, y_offset + 20), 0, 2)  # stem
	
	return img

def create_test_pdf():
	"""Create a PDF with musical score"""
	output_dir = Path(__file__).parent.parent / "sample_books"
	output_dir.mkdir(parents=True, exist_ok=True)
	
	# Create score image
	score_img = create_score_image()
	temp_img_path = output_dir / "temp_score.png"
	cv2.imwrite(str(temp_img_path), score_img)
	
	# Create PDF
	pdf_path = output_dir / "basic_score.pdf"
	c = canvas.Canvas(str(pdf_path), pagesize=letter)
	
	# Add title
	c.setFont("Helvetica", 16)
	c.drawString(72, 750, "Basic Musical Score")
	
	# Add score image
	c.drawImage(str(temp_img_path), 72, 72, width=450, height=600)
	c.save()
	
	# Cleanup
	temp_img_path.unlink()
	
	return pdf_path

if __name__ == '__main__':
	pdf_path = create_test_pdf()
	print(f"Created test score PDF: {pdf_path}")