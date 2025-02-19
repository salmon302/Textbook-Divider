import os
from pathlib import Path
from pdf2image import convert_from_path

def generate_test_images():
	# Setup paths
	script_dir = Path(__file__).parent
	project_root = script_dir.parent.parent
	input_pdf = project_root / 'data' / 'input' / 'Arnold Schoenberg, Gerald Strang, Leonard Stein - Fundamentals of Musical Composition (1982, Faber & Faber) - libgen.li.pdf'
	output_dir = project_root / 'tests' / 'data' / 'test_images'
	
	# Create output directory if it doesn't exist
	output_dir.mkdir(parents=True, exist_ok=True)
	
	# Select pages to extract (mix of text, musical notation, etc.)
	test_pages = [10, 20, 30, 40, 50]  # Adjust page numbers as needed
	
	# Convert and save pages one at a time to avoid memory issues
	for page_num in test_pages:
		images = convert_from_path(
			str(input_pdf),
			first_page=page_num,
			last_page=page_num
		)
		
		if images:
			output_path = output_dir / f'page_{page_num:03d}.png'
			images[0].save(str(output_path), 'PNG')
			print(f'Saved {output_path}')


if __name__ == '__main__':
	generate_test_images()