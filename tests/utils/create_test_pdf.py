from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os

def create_test_pdf():
	output_path = os.path.join(os.path.dirname(__file__), 'sample_books', 'sample.pdf')
	c = canvas.Canvas(output_path, pagesize=letter)
	
	# First page
	c.setFont('Helvetica-Bold', 16)
	c.drawString(100, 750, "INTRODUCTION")
	c.setFont('Helvetica', 12)
	c.drawString(100, 700, "This is the introduction chapter of the test document.")
	c.showPage()
	
	# Second page
	c.setFont('Helvetica-Bold', 16)
	c.drawString(100, 750, "THE CONCEPT OF FORM")
	c.setFont('Helvetica', 12)
	c.drawString(100, 700, "This chapter discusses the concept of form in detail.")
	c.save()

if __name__ == '__main__':
	create_test_pdf()