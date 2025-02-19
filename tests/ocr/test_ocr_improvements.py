import os
import time
import json
from pathlib import Path
from textbook_divider.ocr_processor import OCRProcessor

def run_ocr_benchmark():
	# Initialize OCR processor
	ocr = OCRProcessor(enable_gpu=False)
	
	# Test data directory
	test_dir = Path(__file__).parent.parent / 'data' / 'test_images'
	results = {
		'performance': [],
		'cache_stats': {},
		'memory_usage': []
	}
	
	# Process test images
	for image_file in test_dir.glob('*.png'):
		start_time = time.time()
		text = ocr.process_image(str(image_file))
		processing_time = time.time() - start_time
		
		results['performance'].append({
			'file': image_file.name,
			'time': processing_time,
			'text_length': len(text)
		})
		
		# Get cache stats
		results['cache_stats'] = ocr.get_stats()
	
	# Save results
	output_dir = Path(__file__).parent / 'output'
	output_dir.mkdir(exist_ok=True)
	
	output_file = output_dir / f'ocr_benchmark_{int(time.time())}.json'
	with open(output_file, 'w') as f:
		json.dump(results, f, indent=2)
	
	return results

if __name__ == '__main__':
	results = run_ocr_benchmark()
	print("\nOCR Benchmark Results:")
	print(f"Average processing time: {sum(r['time'] for r in results['performance'])/len(results['performance']):.2f}s")
	print(f"Cache hit rate: {results['cache_stats']['cache_hit_rate']}")