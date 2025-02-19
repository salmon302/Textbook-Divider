#!/usr/bin/env python3

import json
import os
from pathlib import Path
from difflib import SequenceMatcher

def calculate_text_similarity(text1: str, text2: str) -> float:
	"""Calculate text similarity ratio using SequenceMatcher"""
	return SequenceMatcher(None, text1, text2).ratio()

def calculate_metrics(ground_truth_file: Path, output_file: Path) -> dict:
	"""Calculate accuracy metrics between ground truth and output"""
	with open(ground_truth_file) as f:
		ground_truth = json.load(f)
	with open(output_file) as f:
		output = json.load(f)
	
	metrics = {
		"chapter_detection": {
			"true_positives": 0,
			"false_positives": 0,
			"false_negatives": 0,
			"f1_score": 0.0
		},
		"content_preservation": {
			"text_accuracy": 0.0,
			"mathematical_notation": 0.0,
			"musical_notation": 0.0,
			"figures_diagrams": 0.0,
			"tables": 0.0
		},
		"feature_detection": {
			"math_formulas": False,
			"musical_symbols": False,
			"complex_figures": False,
			"technical_diagrams": False,
			"tables": False
		},
		"extraction_methods": {
			"pypdf2_success": 0,
			"pdfminer_success": 0,
			"ocr_fallback_used": 0
		}
	}
	
	# Compare chapters
	gt_chapters = set(str(ch["number"]) for ch in ground_truth["chapters"])
	out_chapters = set(str(ch["number"]) for ch in output["chapters"])
	
	metrics["chapter_detection"]["true_positives"] = len(gt_chapters & out_chapters)
	metrics["chapter_detection"]["false_positives"] = len(out_chapters - gt_chapters)
	metrics["chapter_detection"]["false_negatives"] = len(gt_chapters - out_chapters)
	
	# Calculate F1 score
	precision = metrics["chapter_detection"]["true_positives"] / (
		metrics["chapter_detection"]["true_positives"] + 
		metrics["chapter_detection"]["false_positives"]
	) if metrics["chapter_detection"]["true_positives"] > 0 else 0
	
	recall = metrics["chapter_detection"]["true_positives"] / (
		metrics["chapter_detection"]["true_positives"] + 
		metrics["chapter_detection"]["false_negatives"]
	) if metrics["chapter_detection"]["true_positives"] > 0 else 0
	
	metrics["chapter_detection"]["f1_score"] = (
		2 * (precision * recall) / (precision + recall)
		if precision + recall > 0 else 0
	)
	
	# Compare content and features
	total_text_sim = 0.0
	total_chapters = len(gt_chapters & out_chapters)
	
	if total_chapters > 0:
		for gt_ch in ground_truth["chapters"]:
			for out_ch in output["chapters"]:
				if str(gt_ch["number"]) == str(out_ch["number"]):
					# Text accuracy
					text_sim = calculate_text_similarity(
						gt_ch["content"], out_ch["content"]
					)
					total_text_sim += text_sim
					
					# Feature detection
					if "features" in gt_ch and "features" in out_ch:
						metrics["feature_detection"].update({
							k: out_ch["features"].get(k, False)
							for k in metrics["feature_detection"].keys()
						})
					
					# Extraction method tracking
					if "extraction_method" in out_ch:
						method = out_ch["extraction_method"]
						if method == "pypdf2":
							metrics["extraction_methods"]["pypdf2_success"] += 1
						elif method == "pdfminer":
							metrics["extraction_methods"]["pdfminer_success"] += 1
						elif method == "ocr":
							metrics["extraction_methods"]["ocr_fallback_used"] += 1
		
		metrics["content_preservation"]["text_accuracy"] = total_text_sim / total_chapters
	
	# Calculate content preservation metrics
	if "accuracy_metrics" in output:
		metrics["content_preservation"].update(output["accuracy_metrics"])
	
	return metrics

def main():
	tests_dir = Path(__file__).parent.parent
	metrics_dir = tests_dir / "metrics"
	metrics_dir.mkdir(exist_ok=True)
	
	# Process each book in the test set
	books = [
		"Schoenberg_Fundamentals",
		"Lewin_GMIT",
		"Tymoczko_Geometry",
		"Erdahl_PitchSpace"
	]
	
	overall_metrics = {}
	
	for book in books:
		ground_truth = tests_dir / "ground_truth" / f"{book}.json"
		output = tests_dir / "output" / f"{book}_output.json"
		
		if ground_truth.exists() and output.exists():
			metrics = calculate_metrics(ground_truth, output)
			overall_metrics[book] = metrics
			
			# Save individual metrics
			metrics_file = metrics_dir / f"{book}_metrics.json"
			with open(metrics_file, 'w') as f:
				json.dump(metrics, f, indent=2)
	
	# Save overall metrics summary
	summary_file = metrics_dir / "overall_metrics.json"
	with open(summary_file, 'w') as f:
		json.dump(overall_metrics, f, indent=2)
	
	print("Metrics calculation complete. Results saved in metrics directory.")

if __name__ == "__main__":
	main()