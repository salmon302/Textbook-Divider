#!/usr/bin/env python3

import PyPDF2
from pathlib import Path
import re

def clean_text(text):
	"""Clean extracted text for better analysis"""
	# Replace multiple spaces with single space
	text = re.sub(r'\s+', ' ', text)
	# Remove form feeds
	text = text.replace('\f', '\n')
	return text

def analyze_single_pdf(pdf_path):
	print(f"\nAnalyzing: {pdf_path.name}")
	print("="*80)
	
	with open(pdf_path, 'rb') as file:
		pdf = PyPDF2.PdfReader(file)
		total_pages = len(pdf.pages)
		print(f"Total pages: {total_pages}")
		
		# Look for table of contents first (first 10 pages)
		for page_num in range(min(10, total_pages)):
			text = clean_text(pdf.pages[page_num].extract_text())
			if any(marker in text.lower() for marker in ['contents', 'table of contents', 'index']):
				print(f"\nFound potential contents on page {page_num + 1}:")
				print("-"*50)
				# Print each line that might be a chapter entry
				for line in text.split('\n'):
					if re.search(r'^\s*(\d+|[IVX]+)[\.\s]', line):
						print(f"TOC Entry: {line.strip()}")
		
		# Analyze each page
		print("\nAnalyzing pages:")
		for page_num in range(min(20, total_pages)):
			text = clean_text(pdf.pages[page_num].extract_text())
			print(f"\nPage {page_num + 1}:")
			print("-"*50)
			
			# Look for chapter markers
			chapter_patterns = [
				r'^\s*chapter\s+(\d+|[ivxlc]+)',
				r'^\s*(\d+)\.\s+[A-Z]',
				r'^\s*[IVX]+\.\s+[A-Z]',
				r'^\s*part\s+(\d+|[ivxlc]+)',
				r'^\s*section\s+(\d+|[ivxlc]+)'
			]
			
			lines = text.split('\n')
			for i, line in enumerate(lines):
				# Print first few lines of each page
				if i < 3:
					print(f"Line {i+1}: {line[:100]}")
				
				# Check for chapter patterns
				for pattern in chapter_patterns:
					if re.search(pattern, line, re.IGNORECASE):
						print(f"Potential chapter marker: {line.strip()}")
			
			# Look for musical terms
			musical_terms = [
				r'\b(tempo|allegro|andante|forte|piano)\b',
				r'\b(chord|scale|note|rhythm|melody)\b',
				r'\b(major|minor|diminished|augmented)\b'
			]
			
			for pattern in musical_terms:
				if re.search(pattern, text, re.IGNORECASE):
					print(f"Found musical term matching: {pattern}")

if __name__ == "__main__":
	input_dir = Path(__file__).parent.parent / "input"
	target_file = input_dir / "Arnold Schoenberg, Gerald Strang, Leonard Stein - Fundamentals of Musical Composition (1982, Faber & Faber) - libgen.li.pdf"
	
	if target_file.exists():
		analyze_single_pdf(target_file)
	else:
		print(f"File not found: {target_file}")