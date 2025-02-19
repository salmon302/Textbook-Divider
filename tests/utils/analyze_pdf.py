#!/usr/bin/env python3

import PyPDF2
from pathlib import Path
import re

def analyze_pdf(pdf_path):
	print(f"\nAnalyzing: {pdf_path.name}")
	print("="*80)
	
	with open(pdf_path, 'rb') as file:
		pdf = PyPDF2.PdfReader(file)
		total_pages = len(pdf.pages)
		print(f"Total pages: {total_pages}")
		
		# Analyze first few pages
		for page_num in range(min(20, total_pages)):
			print(f"\nPage {page_num + 1}:")
			print("-"*50)
			
			text = pdf.pages[page_num].extract_text()
			
			# Look for potential chapter headings
			chapter_patterns = [
				r'(?im)^.*?(chapter|part|section)\s+(\d+|[ivxlc]+).*$',
				r'(?im)^\s*(\d+|[ivxlc]+)\.\s+[A-Z].*$',
				r'(?im)^.*?contents.*$',
				r'(?im)^.*?table\s+of\s+contents.*$'
			]
			
			for pattern in chapter_patterns:
				matches = re.finditer(pattern, text, re.MULTILINE)
				for match in matches:
					print(f"Potential heading: {match.group(0)}")
			
			# Print first few non-empty lines
			lines = [line.strip() for line in text.split('\n') if line.strip()]
			for line in lines[:5]:
				print(f"Line: {line[:100]}")

if __name__ == "__main__":
	input_dir = Path(__file__).parent.parent / "input"
	
	# Analyze each PDF
	for pdf_file in input_dir.glob("*.pdf"):
		analyze_pdf(pdf_file)