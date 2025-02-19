#!/usr/bin/env python3

import fitz  # PyMuPDF
from pathlib import Path
import re

def analyze_pdf_content(pdf_path):
	print(f"\nAnalyzing: {pdf_path.name}")
	print("="*80)
	
	doc = fitz.open(pdf_path)
	total_pages = len(doc)
	print(f"Total pages: {total_pages}")
	
	# Analyze first few pages
	for page_num in range(min(20, total_pages)):
		page = doc[page_num]
		text = page.get_text()
		
		print(f"\nPage {page_num + 1}:")
		print("-"*50)
		
		# Print first few lines
		lines = text.split('\n')
		for i, line in enumerate(lines[:10]):
			if line.strip():
				print(f"Line {i+1}: {line[:100]}")
		
		# Look for musical terms
		musical_terms = re.finditer(
			r'\b(tempo|allegro|andante|forte|piano|chord|scale|note|rhythm|melody|harmony|counterpoint)\b',
			text,
			re.IGNORECASE
		)
		for match in musical_terms:
			print(f"Musical term found: {match.group(0)}")
		
		# Look for mathematical notation
		math_terms = re.finditer(
			r'\b(theorem|lemma|proof|equation|formula|function|interval|set|group)\b',
			text,
			re.IGNORECASE
		)
		for match in math_terms:
			print(f"Math term found: {match.group(0)}")
		
		# Look for chapter markers
		chapter_markers = re.finditer(
			r'(?im)^(?:chapter|part|section)\s+(?:\d+|[ivxlc]+)|^\d+\.\s+[A-Z]',
			text
		)
		for match in chapter_markers:
			print(f"Chapter marker found: {match.group(0)}")
			
	doc.close()

if __name__ == "__main__":
	input_dir = Path(__file__).parent.parent / "input"
	target_file = input_dir / "Arnold Schoenberg, Gerald Strang, Leonard Stein - Fundamentals of Musical Composition (1982, Faber & Faber) - libgen.li.pdf"
	
	if target_file.exists():
		analyze_pdf_content(target_file)
	else:
		print(f"File not found: {target_file}")