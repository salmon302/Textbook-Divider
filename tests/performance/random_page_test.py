import random
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

data_dir = project_root / 'data' / 'input'

from src.textbook_divider.file_handler import FileHandler
from src.textbook_divider.text_processor import TextProcessor
from src.textbook_divider.chapter_detector import ChapterDetector
from src.textbook_divider.ocr_processor import OCRProcessor
from src.textbook_divider.omr_processor import OMRProcessor

class RandomPageTester:
	def __init__(self):
		self.test_books = {
			'schoenberg': {
				'name': "Fundamentals of Musical Composition",
				'path': str(data_dir / 'Arnold Schoenberg, Gerald Strang, Leonard Stein - Fundamentals of Musical Composition (1982, Faber & Faber) - libgen.li.pdf'),
				'total_pages': None  # Will be populated when file is loaded
			},
			'lewin': {
				'name': "Generalized Musical Intervals",
				'path': str(data_dir / 'David Lewin - Generalized Musical Intervals and Transformations (2007).pdf'),
				'total_pages': None
			},
			'tymoczko': {
				'name': "Geometry of Music",
				'path': str(data_dir / '(Oxford Studies in Music Theory) Dmitri Tymoczko - A Geometry of Music_ Harmony and Counterpoint in the Extended Common Practice-Oxford University Press (2011).pdf'),
				'total_pages': None
			},
			'lerdahl': {
				'name': "Tonal Pitch Space",
				'path': str(data_dir / 'Fred LErdahl - Tonal Pitch Space-Oxford University Press (2001).pdf'),
				'total_pages': None
			}
		}
		
		self.file_handler = FileHandler()
		self.text_processor = TextProcessor()
		self.chapter_detector = ChapterDetector()
		self.ocr_processor = OCRProcessor()
		self.omr_processor = OMRProcessor()
		
	def load_book_metadata(self):
		"""Load page counts for each book"""
		for book_id, book_info in self.test_books.items():
			try:
				page_count = self.file_handler.get_page_count(book_info['path'])
				self.test_books[book_id]['total_pages'] = page_count
			except FileNotFoundError:
				print(f"Warning: {book_info['name']} not found at {book_info['path']}")
				self.test_books[book_id]['total_pages'] = 0

	def select_random_pages(self, book_id, num_pages=5):
		"""Select random pages from a book"""
		total_pages = self.test_books[book_id]['total_pages']
		if not total_pages:
			return []
		return random.sample(range(1, total_pages + 1), min(num_pages, total_pages))

	def process_page(self, book_id, page_num):
		"""Process a single page and return metrics"""
		start_time = datetime.now()
		book_info = self.test_books[book_id]
		
		try:
			# Process the page through the pipeline
			page_content = self.file_handler.extract_page(book_info['path'], page_num)
			ocr_result = self.ocr_processor.process(page_content)
			processed_text = self.text_processor.process(ocr_result)
			
			# Check for musical notation
			has_notation = self.omr_processor.detect_notation(page_content)
			if has_notation:
				notation_result = self.omr_processor.process(page_content)
			
			end_time = datetime.now()
			processing_time = (end_time - start_time).total_seconds()
			
			return {
				'success': True,
				'processing_time': processing_time,
				'has_notation': has_notation,
				'page_number': page_num,
				'error': None
			}
			
		except Exception as e:
			return {
				'success': False,
				'processing_time': None,
				'has_notation': None,
				'page_number': page_num,
				'error': str(e)
			}

	def run_tests(self):
		"""Run tests on 5 random pages from each book"""
		self.load_book_metadata()
		results = {}
		
		for book_id, book_info in self.test_books.items():
			if book_info['total_pages']:
				print(f"\nTesting {book_info['name']}...")
				pages = self.select_random_pages(book_id)
				book_results = []
				
				for page in pages:
					print(f"Processing page {page}...")
					result = self.process_page(book_id, page)
					book_results.append(result)
				
				results[book_id] = book_results
		
		return results

	def save_results(self, results):
		"""Save test results to a JSON file"""
		timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
		output_dir = project_root / 'tests' / 'output' / 'random_page_tests'
		output_dir.mkdir(parents=True, exist_ok=True)
		
		output_file = output_dir / f'test_results_{timestamp}.json'
		
		with open(output_file, 'w') as f:
			json.dump(results, f, indent=2)
		
		return output_file

def main():
	tester = RandomPageTester()
	results = tester.run_tests()
	output_file = tester.save_results(results)
	
	print(f"\nTest results saved to: {output_file}")
	
	# Print summary
	print("\nTest Summary:")
	for book_id, book_results in results.items():
		successful = len([r for r in book_results if r['success']])
		total = len(book_results)
		avg_time = sum(r['processing_time'] for r in book_results if r['success'] and r['processing_time']) / successful if successful else 0
		
		print(f"\n{tester.test_books[book_id]['name']}:")
		print(f"- Pages tested: {total}")
		print(f"- Successful: {successful}")
		print(f"- Average processing time: {avg_time:.2f}s")

if __name__ == "__main__":
	main()