#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

def load_json_file(file_path: Path) -> dict:
	"""Load and parse JSON file"""
	with open(file_path) as f:
		return json.load(f)

def compare_features(ground_truth: dict, result: dict) -> List[str]:
	"""Compare feature detection between ground truth and result"""
	differences = []
	
	# Compare feature detection
	gt_features = ground_truth.get('features', {})
	res_features = result.get('features', {})
	
	for feature in ['math', 'music', 'figures', 'tables', 'technical_diagrams']:
		if gt_features.get(feature) != res_features.get(feature):
			differences.append(
				f"Feature detection mismatch for {feature}:\n"
				f"Expected: {gt_features.get(feature)}\n"
				f"Got: {res_features.get(feature)}"
			)
	
	return differences

def compare_extraction_methods(result: dict) -> List[str]:
	"""Analyze text extraction method usage"""
	analysis = []
	
	methods = result.get('extraction_methods', {})
	total_pages = sum(m.get('pages', 0) for m in methods.values())
	
	if total_pages > 0:
		for method, stats in methods.items():
			percentage = (stats.get('pages', 0) / total_pages) * 100
			analysis.append(
				f"{method}: {percentage:.1f}% of pages "
				f"(avg {stats.get('time', 0)/max(1, stats.get('pages', 1)):.2f}s per page)"
			)
	
	return analysis

def compare_chapters(ground_truth: dict, result: dict) -> List[str]:
	"""Compare chapters between ground truth and processing result"""
	differences = []
	
	gt_chapters = {str(ch["number"]): ch for ch in ground_truth["chapters"]}
	res_chapters = {str(ch["number"]): ch for ch in result["chapters"]}
	
	# Check for missing/extra chapters
	missing = set(gt_chapters.keys()) - set(res_chapters.keys())
	extra = set(res_chapters.keys()) - set(gt_chapters.keys())
	
	if missing:
		differences.append(f"Missing chapters: {', '.join(missing)}")
	if extra:
		differences.append(f"Extra chapters detected: {', '.join(extra)}")
	
	# Compare content of matching chapters
	for num in set(gt_chapters.keys()) & set(res_chapters.keys()):
		gt_ch = gt_chapters[num]
		res_ch = res_chapters[num]
		
		if gt_ch["title"] != res_ch["title"]:
			differences.append(
				f"Chapter {num} title mismatch:\n"
				f"Expected: {gt_ch['title']}\n"
				f"Got: {res_ch['title']}"
			)
	
	# Add feature comparison
	differences.extend(compare_features(ground_truth, result))
	
	# Add extraction method analysis
	differences.extend(["\nText Extraction Analysis:"] + 
					  compare_extraction_methods(result))
	
	# Compare accuracy metrics
	gt_accuracy = ground_truth.get('accuracy_metrics', {})
	res_accuracy = result.get('accuracy_metrics', {})
	
	for metric in ['text', 'mathematical_notation', 'musical_notation', 'figures']:
		gt_val = gt_accuracy.get(f'{metric}_accuracy', 0)
		res_val = res_accuracy.get(f'{metric}_accuracy', 0)
		if abs(gt_val - res_val) > 0.05:  # 5% threshold
			differences.append(
				f"{metric} accuracy mismatch:\n"
				f"Expected: {gt_val:.2f}\n"
				f"Got: {res_val:.2f}"
			)
	
	return differences

def main():
	tests_dir = Path(__file__).parent.parent
	books = [
		"Schoenberg_Fundamentals",
		"Lewin_GMIT",
		"Tymoczko_Geometry",
		"Erdahl_PitchSpace"
	]
	
	# Initialize summary statistics
	summary = {
		'total_books': len(books),
		'successful_comparisons': 0,
		'feature_detection_accuracy': {},
		'extraction_method_stats': {}
	}
	
	for book in books:
		ground_truth = tests_dir / "ground_truth" / f"{book}.json"
		result = tests_dir / "output" / f"{book}_output.json"
		
		if not ground_truth.exists():
			print(f"Warning: No ground truth file for {book}")
			continue
		if not result.exists():
			print(f"Warning: No result file for {book}")
			continue
			
		gt_data = load_json_file(ground_truth)
		res_data = load_json_file(result)
		
		differences = compare_chapters(gt_data, res_data)
		
		# Update summary statistics
		if not differences:
			summary['successful_comparisons'] += 1
			
		# Save comparison results
		comparison_file = tests_dir / "metrics" / f"{book}_comparison.txt"
		with open(comparison_file, 'w') as f:
			if differences:
				f.write(f"Differences found in {book}:\n")
				f.write("\n".join(differences))
			else:
				f.write(f"No significant differences found in {book}")
		
		print(f"Comparison complete for {book}")
	
	# Save summary report
	summary_file = tests_dir / "metrics" / "comparison_summary.json"
	with open(summary_file, 'w') as f:
		json.dump(summary, f, indent=2)

if __name__ == "__main__":
	main()