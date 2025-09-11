#!/usr/bin/env python3

import os
from PIL import Image, ImageDraw, ImageFont
import img2pdf
import numpy as np
import cv2

def create_staff_lines(draw, x, y, width=600, spacing=20):
	"""Draw a staff with 5 lines"""
	for i in range(5):
		y_pos = y + i * spacing
		draw.line([(x, y_pos), (x + width, y_pos)], fill='black', width=2)

def create_musical_symbols(draw, x, y):
	"""Draw basic musical symbols"""
	# Quarter notes
	draw.ellipse([(x, y), (x + 12, y + 12)], fill='black')
	draw.line([(x + 12, y + 6), (x + 12, y - 30)], fill='black', width=2)
	
	# Treble clef (simplified)
	draw.arc([(x + 50, y - 10), (x + 70, y + 30)], 0, 270, fill='black', width=2)
	
	# Time signature
	draw.text((x + 100, y - 10), "4", fill='black', font=ImageFont.load_default())
	draw.text((x + 100, y + 10), "4", fill='black', font=ImageFont.load_default())

def create_test_samples():
	current_dir = os.path.dirname(os.path.abspath(__file__))
	
	# Create various test samples
	samples = {
		'basic_score': (800, 1000, lambda img: create_basic_score(img)),
		'complex_score': (1000, 1200, lambda img: create_complex_score(img)),
		'multi_column': (1000, 1400, lambda img: create_multi_column(img)),
		'corrupted_score': (800, 1000, lambda img: create_corrupted_score(img)),
		'mixed_layout': (1000, 1400, lambda img: create_mixed_layout(img)),
		'contemporary': (800, 1200, lambda img: create_contemporary_score(img)),
		'low_res_score': (800, 1000, lambda img: create_low_res_score(img))
	}
	
	for name, (width, height, generator) in samples.items():
		# Create image
		img = Image.new('RGB', (width, height), 'white')
		draw = ImageDraw.Draw(img)
		generator(draw)
		
		# Save as PNG first
		png_path = os.path.join(current_dir, f'{name}.png')
		img.save(png_path)
		
		# Convert PNG to PDF
		pdf_path = os.path.join(current_dir, f'{name}.pdf')
		with open(pdf_path, 'wb') as pdf_file:
			pdf_file.write(img2pdf.convert(png_path))
		
		# Clean up PNG
		os.remove(png_path)
		print(f"Created {name} at: {pdf_path}")

def create_basic_score(draw):
	"""Create a basic musical score"""
	create_staff_lines(draw, 100, 100)
	create_musical_symbols(draw, 150, 120)
	draw.text((50, 50), "Basic Musical Score", fill='black')

def create_complex_score(draw):
	"""Create a complex musical score with multiple staves"""
	y_positions = [100, 300, 500]
	for y in y_positions:
		create_staff_lines(draw, 100, y)
		create_musical_symbols(draw, 150, y + 20)
	draw.text((50, 50), "Complex Musical Score", fill='black')

def create_multi_column(draw):
	"""Create a two-column layout with music"""
	# Left column
	create_staff_lines(draw, 50, 100)
	create_musical_symbols(draw, 100, 120)
	draw.text((50, 50), "Column 1", fill='black')
	
	# Right column
	create_staff_lines(draw, 550, 100)
	create_musical_symbols(draw, 600, 120)
	draw.text((550, 50), "Column 2", fill='black')

def create_corrupted_score(draw):
	"""Create a partially corrupted musical score"""
	create_staff_lines(draw, 100, 100)
	# Add some random noise
	for _ in range(50):
		x = np.random.randint(100, 700)
		y = np.random.randint(100, 200)
		draw.point((x, y), fill='black')

def create_mixed_layout(draw):
	"""Create a page with mixed text and musical notation"""
	draw.text((50, 50), "Chapter 1: Musical Theory", fill='black')
	draw.text((50, 100), "Lorem ipsum dolor sit amet...", fill='black')
	create_staff_lines(draw, 100, 200)
	create_musical_symbols(draw, 150, 220)

def create_contemporary_score(draw):
	"""Create a contemporary score with non-standard notation"""
	# Non-standard staff (6 lines)
	for i in range(6):
		y = 100 + i * 20
		draw.line([(100, y), (700, y)], fill='black', width=2)
	
	# Add some contemporary notation symbols
	draw.rectangle([(150, 90), (170, 170)], outline='black')
	draw.line([(200, 90), (200, 170)], fill='black', width=4)

def create_low_res_score(draw):
	"""Create a low resolution musical score"""
	# Draw at higher resolution first
	create_staff_lines(draw, 100, 100)
	create_musical_symbols(draw, 150, 120)
	draw.text((50, 50), "Low Resolution Score", fill='black')
	
	# Convert to low resolution
	img = draw._image
	width, height = img.size
	low_res = img.resize((width//4, height//4), Image.NEAREST)
	return low_res.resize((width, height), Image.NEAREST)

if __name__ == '__main__':
	create_test_samples()
