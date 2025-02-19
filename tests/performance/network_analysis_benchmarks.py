import time
import random
import networkx as nx
from typing import Dict, List
from graph_extractor.graph_types import MusicTheoryGraph, Node, Edge, NodeType
from graph_extractor.graph_analyzer import GraphAnalyzer

def create_test_graph(num_nodes: int, edge_probability: float) -> MusicTheoryGraph:
	graph = MusicTheoryGraph()
	# Create transformation nodes
	for i in range(num_nodes):
		node = Node(
			id=f"t{i}",
			type=NodeType.TRANSFORMATION,
			label=f"Transform_{i}",
			properties={}
		)
		graph.add_node(node)
	
	# Add random edges
	for i in range(num_nodes):
		for j in range(i + 1, num_nodes):
			if random.random() < edge_probability:
				edge = Edge(
					source=f"t{i}",
					target=f"t{j}",
					label=f"e{i}_{j}",
					properties={"weight": random.random()}
				)
				graph.add_edge(edge)
	
	return graph

def benchmark_operation(func, *args) -> Dict[str, float]:
	start_time = time.time()
	result = func(*args)
	end_time = time.time()
	return {
		"execution_time": end_time - start_time,
		"result_size": len(result) if isinstance(result, (list, dict, set)) else 1
	}

def run_benchmarks(sizes: List[int], trials: int = 3) -> Dict[str, Dict[str, float]]:
	results = {}
	
	for size in sizes:
		size_results = {
			"find_cycles": {"avg_time": 0, "avg_size": 0},
			"connected_components": {"avg_time": 0, "avg_size": 0},
			"transformation_analysis": {"avg_time": 0, "avg_size": 0}
		}
		
		for _ in range(trials):
			graph = create_test_graph(size, 0.3)
			analyzer = GraphAnalyzer(graph)
			
			# Benchmark cycle detection
			cycle_result = benchmark_operation(analyzer.find_transformation_cycles)
			size_results["find_cycles"]["avg_time"] += cycle_result["execution_time"]
			size_results["find_cycles"]["avg_size"] += cycle_result["result_size"]
			
			# Benchmark connected components
			comp_result = benchmark_operation(analyzer.get_connected_components)
			size_results["connected_components"]["avg_time"] += comp_result["execution_time"]
			size_results["connected_components"]["avg_size"] += comp_result["result_size"]
			
			# Benchmark transformation analysis
			trans_result = benchmark_operation(analyzer.analyze_transformation_network)
			size_results["transformation_analysis"]["avg_time"] += trans_result["execution_time"]
			size_results["transformation_analysis"]["avg_size"] += 1
		
		# Average the results
		for op in size_results:
			size_results[op]["avg_time"] /= trials
			size_results[op]["avg_size"] /= trials
		
		results[size] = size_results
	
	return results

if __name__ == "__main__":
	sizes = [10, 50, 100, 500]
	results = run_benchmarks(sizes)
	
	print("\nNetwork Analysis Performance Benchmarks")
	print("======================================")
	for size in sizes:
		print(f"\nGraph Size: {size} nodes")
		for op, metrics in results[size].items():
			print(f"{op}:")
			print(f"  Average time: {metrics['avg_time']:.4f} seconds")
			print(f"  Average result size: {metrics['avg_size']:.2f}")