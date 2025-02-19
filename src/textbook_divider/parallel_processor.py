import os
import psutil
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass

@dataclass
class WorkerStats:
	processed_items: int = 0
	failed_items: int = 0
	memory_usage: float = 0.0

class ParallelProcessor:
	def __init__(self, max_workers: int = 4, memory_limit_mb: int = 500):
		self.max_workers = max_workers
		self.memory_limit_mb = memory_limit_mb
		self.logger = logging.getLogger(__name__)
		self.worker_stats = {}
		
	def process_batch(self, items: List[Any], process_func: Callable) -> Dict[str, Any]:
		results = []
		failed = []
		
		with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
			future_to_item = {executor.submit(self._process_with_stats, process_func, item): item 
							for item in items}
			
			for future in as_completed(future_to_item):
				item = future_to_item[future]
				try:
					result = future.result()
					if result is not None:
						results.append(result)
					else:
						failed.append(item)
				except Exception as e:
					self.logger.error(f"Processing failed for {item}: {str(e)}")
					failed.append(item)
		
		return {
			'results': results,
			'failed': failed
		}
	
	def _process_with_stats(self, process_func: Callable, item: Any) -> Optional[Any]:
		worker_id = os.getpid()
		if worker_id not in self.worker_stats:
			self.worker_stats[worker_id] = WorkerStats()
		
		try:
			# Check memory usage
			process = psutil.Process(worker_id)
			memory_mb = process.memory_info().rss / 1024 / 1024
			self.worker_stats[worker_id].memory_usage = memory_mb
			
			if memory_mb > self.memory_limit_mb:
				self.logger.warning(f"Worker {worker_id} exceeded memory limit")
				return None
			
			result = process_func(item)
			self.worker_stats[worker_id].processed_items += 1
			return result
			
		except Exception as e:
			self.logger.error(f"Worker {worker_id} failed: {str(e)}")
			self.worker_stats[worker_id].failed_items += 1
			return None
