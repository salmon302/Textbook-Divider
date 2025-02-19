#!/usr/bin/env python3

import fitz  # PyMuPDF
from pathlib import Path
import re
import urllib.parse

def debug_pdf(pdf_path):
	try:
		print(f"\nAnalyzing: {pdf_path.name}")
		print("="*80)
		
		# Handle paths with spaces
		doc = fitz.open(str(pdf_path))
		total_pages = len(doc)
		print(f"Total pages: {total_pages}")
		
		# Analyze first few pages
		for page_num in range(min(5, total_pages)):
			try:
				page = doc[page_num]
				text = page.get_text()
				
				print(f"\nPage {page_num + 1} Content:")
				print("-"*50)
				print(text[:500])  # Print first 500 characters
				
				# Look for specific terms
				terms = {
					'musical': re.findall(r'\b(music|chord|note|rhythm|harmony|melody)\b', text, re.I),
					'mathematical': re.findall(r'\b(theorem|function|interval|set|group)\b', text, re.I),
					'structural': re.findall(r'\b(chapter|section|part|exercise)\b', text, re.I)
				}
				
				for category, found_terms in terms.items():
					if found_terms:
						print(f"\n{category.title()} terms found: {', '.join(set(found_terms))}")
			except Exception as e:
				print(f"Error processing page {page_num + 1}: {str(e)}")
		
		doc.close()
	except Exception as e:
		print(f"Error opening PDF: {str(e)}")

if __name__ == "__main__":
	input_dir = Path(__file__).parent.parent / "input"
	
	# Test files
	test_files = [
		"Arnold Schoenberg, Gerald Strang, Leonard Stein - Fundamentals of Musical Composition (1982, Faber & Faber) - libgen.li.pdf",
		"David Lewin - Generalized Musical Intervals and Transformations (2007).pdf"
	]
	
	for filename in test_files:
		pdf_path = input_dir / filename
		if pdf_path.exists():
			debug_pdf(pdf_path)
		else:
			print(f"File not found: {filename}")