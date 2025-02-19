import os
import time
import psutil
import numpy as np
from PIL import Image
from pathlib import Path
import pytest
from textbook_divider.ocr_processor import OCRProcessor

def get_process_memory():
	process = psutil.Process(os.getpid())
	return process.memory_info().rss / 1024 / 1024  # Convert to MB

def create_large_test_image(size=(3000, 3000)):
	"""Create a large test image with text"""
	image = Image.new('RGB', size, 'white')
	return np.array(image)

@pytest.fixture
def processor():
	return OCRProcessor(enable_gpu=False, cache_size=100)

@pytest.fixture
def test_images_dir():
	test_dir = Path(__file__).parent.parent / 'data' / 'test_images'
	if not test_dir.exists():
		test_dir.mkdir(parents=True)
	return test_dir

def test_parallel_ocr_performance(processor, test_images_dir):
	# Get test images
	image_paths = sorted(list(test_images_dir.glob('page_*.png')))
	assert len(image_paths) > 0, f"No test images found in {test_images_dir}"
	
	# Test batch processing performance
	start_time = time.time()
	results = processor.process_images([str(p) for p in image_paths])
	total_time = time.time() - start_time
	
	# Get statistics
	stats = processor.get_stats()
	memory_stats = processor._memory_monitor
	
	print(f"\nPerformance Results:")
	print(f"Total processing time: {total_time:.2f}s")
	print(f"Images per second: {len(image_paths)/total_time:.2f}")
	print(f"Peak memory: {memory_stats['peak']:.2f}MB")
	print(f"Memory warnings: {memory_stats['warnings']}")
	
	# Verify results and performance
	assert len(results.strip()) > 0, "Processing produced no output"
	assert memory_stats['peak'] < 2048, f"Peak memory too high: {memory_stats['peak']:.2f}MB"
	assert total_time/len(image_paths) < 30, f"Processing too slow: {total_time/len(image_paths):.2f}s per image"

def test_chunk_processing(processor):
	# Create large test image
	large_image = create_large_test_image()
	
	# Test chunk processing
	start_mem = get_process_memory()
	text = processor.process_image_in_chunks(large_image)
	peak_mem = processor._memory_monitor['peak']
	
	print(f"\nChunk Processing Results:")
	print(f"Initial memory: {start_mem:.2f}MB")
	print(f"Peak memory: {peak_mem:.2f}MB")
	
	# Verify memory usage
	assert peak_mem - start_mem < 500, f"Memory increase too high: {peak_mem - start_mem:.2f}MB"
	assert processor._memory_monitor['warnings'] == 0, "Unexpected memory warnings"

def test_memory_efficient_batch_processing(processor, test_images_dir):
	image_paths = sorted(list(test_images_dir.glob('page_*.png')))
	
	# Process with memory monitoring
	start_mem = get_process_memory()
	results = processor.process_images([str(p) for p in image_paths])
	peak_mem = processor._memory_monitor['peak']
	
	print(f"\nBatch Processing Memory Usage:")
	print(f"Initial: {start_mem:.2f}MB")
	print(f"Peak: {peak_mem:.2f}MB")
	print(f"Memory warnings: {processor._memory_monitor['warnings']}")
	
	# Verify memory efficiency
	assert peak_mem - start_mem < 1024, f"Memory usage too high: {peak_mem - start_mem:.2f}MB"
	assert len(results.strip()) > 0, "No output produced"

if __name__ == '__main__':
	pytest.main([__file__, '-v'])
