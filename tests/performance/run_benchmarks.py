#!/usr/bin/env python3
import time
import json
import os
import psutil
from pathlib import Path
from textbook_divider.processor import PDFProcessor

class PerformanceBenchmark:
	def __init__(self):
		self.metrics_dir = Path(__file__).parent.parent / 'metrics'
		self.metrics_dir.mkdir(exist_ok=True)
		self.input_dir = Path(__file__).parent.parent.parent / 'input'
		
	def measure_processing_time(self, file_path):
		"""Measure detailed processing time for each extraction method"""
		processor = PDFProcessor()
		metrics = {
			'total_time': 0,
			'per_page': [],
			'extraction_methods': {
				'pypdf2': {'time': 0, 'pages': 0},
				'pdfminer': {'time': 0, 'pages': 0},
				'ocr': {'time': 0, 'pages': 0}
			},
			'feature_detection': {
				'math': 0,
				'music': 0,
				'figures': 0,
				'tables': 0
			}
		}
		
		start_time = time.time()
		try:
			result = processor.process_file(file_path)
			metrics['total_time'] = time.time() - start_time
			
			# Collect per-page metrics
			for page in result.get('pages', []):
				metrics['per_page'].append({
					'page_num': page['number'],
					'processing_time': page.get('processing_time', 0),
					'extraction_method': page.get('extraction_method', 'unknown'),
					'features_detected': page.get('features', {})
				})
				
				# Track extraction method usage
				method = page.get('extraction_method', 'unknown')
				if method in metrics['extraction_methods']:
					metrics['extraction_methods'][method]['pages'] += 1
					metrics['extraction_methods'][method]['time'] += page.get('processing_time', 0)
			
			return metrics
		except Exception as e:
			print(f"Error processing {file_path}: {str(e)}")
			return None
		
	def monitor_memory_usage(self):
		"""Enhanced memory usage monitoring"""
		process = psutil.Process()
		return {
			'peak_memory_mb': process.memory_info().peak_wset / (1024 * 1024),
			'current_memory_mb': process.memory_info().rss / (1024 * 1024),
			'memory_percent': process.memory_percent(),
			'cpu_percent': process.cpu_percent(),
			'num_threads': process.num_threads()
		}
		
	def run_benchmarks(self):
		"""Run performance benchmarks on test files"""
		results = {
			'processing_times': {},
			'memory_usage': {},
			'timestamp': time.strftime('%Y%m%d_%H%M%S'),
			'system_info': {
				'cpu_count': psutil.cpu_count(),
				'total_memory_gb': psutil.virtual_memory().total / (1024**3)
			}
		}
		
		test_files = [
			'Schoenberg_Fundamentals.pdf',
			'Lewin_GMIT.pdf',
			'Tymoczko_Geometry.pdf'
		]
		
		for test_file in test_files:
			file_path = self.input_dir / test_file
			if not file_path.exists():
				print(f"File not found: {test_file}")
				continue
				
			print(f"Benchmarking {test_file}...")
			proc_time = self.measure_processing_time(file_path)
			mem_usage = self.monitor_memory_usage()
			
			if proc_time is not None:
				results['processing_times'][test_file] = {
					'seconds': proc_time,
					'minutes': proc_time / 60
				}
				results['memory_usage'][test_file] = mem_usage
			
		self.save_results(results)
		
	def analyze_performance(self, results):
		"""Analyze performance metrics against requirements"""
		analysis = {
			'meets_requirements': True,
			'issues': []
		}
		
		for file, metrics in results['processing_times'].items():
			# Check processing speed requirements
			base_speed = metrics.get('per_page_avg', 0)
			if base_speed > 2:  # Base text requirement: < 2s/page
				analysis['issues'].append(f"{file}: Base text processing too slow ({base_speed:.2f}s/page)")
				analysis['meets_requirements'] = False
				
			# Check memory requirements
			peak_memory = results['memory_usage'][file]['peak_memory_mb']
			if peak_memory > 2048:  # Peak memory requirement: < 2GB
				analysis['issues'].append(f"{file}: Peak memory usage too high ({peak_memory:.2f}MB)")
				analysis['meets_requirements'] = False
		
		return analysis

	def save_results(self, results):
		"""Save benchmark results to JSON file"""
		output_file = self.metrics_dir / f'benchmark_{results["timestamp"]}.json'
		
		# Add performance analysis
		results['performance_analysis'] = self.analyze_performance(results)
		
		with open(output_file, 'w') as f:
			json.dump(results, f, indent=2)
		print(f"Benchmark results saved to {output_file}")

def main():
	benchmark = PerformanceBenchmark()
	benchmark.run_benchmarks()

if __name__ == '__main__':
	main()