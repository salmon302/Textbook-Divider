#!/usr/bin/env python3
import unittest
import time
import json
import sys
import logging
from pathlib import Path
from datetime import datetime

def setup_logging():
	"""Setup logging configuration"""
	log_dir = Path(__file__).parent / 'logs'
	log_dir.mkdir(exist_ok=True)
	log_file = log_dir / f'test_run_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
	
	logging.basicConfig(
		level=logging.DEBUG,
		format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
		handlers=[
			logging.FileHandler(log_file),
			logging.StreamHandler(sys.stdout)
		]
	)
	return logging.getLogger(__name__)

class DetailedTestResult(unittest.TestResult):
	def __init__(self, logger):
		super().__init__()
		self.successes = []
		self.logger = logger
		
	def addSuccess(self, test):
		self.successes.append(test)
		self.logger.info(f"Test passed: {test}")
		
	def addError(self, test, err):
		self.errors.append((test, self._exc_info_to_string(err, test)))
		self.logger.error(f"Error in {test}\n{self._exc_info_to_string(err, test)}")
		
	def addFailure(self, test, err):
		self.failures.append((test, self._exc_info_to_string(err, test)))
		self.logger.error(f"Failure in {test}\n{self._exc_info_to_string(err, test)}")

def run_test_suite(test_module, suite_name, logger):
	"""Run a test suite and return results"""
	loader = unittest.TestLoader()
	suite = loader.loadTestsFromModule(test_module)
	result = DetailedTestResult(logger)
	logger.info(f"Running test suite: {suite_name}")
	suite.run(result)
	
	return {
		'name': suite_name,
		'total': result.testsRun,
		'failures': len(result.failures),
		'errors': len(result.errors),
		'success': result.wasSuccessful(),
		'failure_details': [str(f[1]) for f in result.failures],
		'error_details': [str(e[1]) for e in result.errors]
	}

def main():
	logger = setup_logging()
	logger.info("Starting test run")
	
	# Import test modules
	import test_chapter_detection
	import test_improvements
	
	# Setup paths
	base_dir = Path(__file__).parent
	report_dir = base_dir / 'test_reports'
	report_dir.mkdir(exist_ok=True)
	
	# Run test suites
	start_time = time.time()
	results = []
	
	test_suites = [
		(test_chapter_detection, "Chapter Detection Tests"),
		(test_improvements, "Improvement Tests")
	]
	
	for module, name in test_suites:
		logger.info(f"\nRunning {name}...")
		result = run_test_suite(module, name, logger)
		results.append(result)
		
		# Log detailed results
		if result['failure_details'] or result['error_details']:
			logger.error("\nDetailed test failures:")
			for detail in result['failure_details']:
				logger.error(f"\nFAILURE: {detail}")
			for detail in result['error_details']:
				logger.error(f"\nERROR: {detail}")
	
	# Generate report
	total_time = time.time() - start_time
	report = {
		'timestamp': datetime.now().isoformat(),
		'duration': total_time,
		'suites': results,
		'overall_success': all(r['success'] for r in results)
	}
	
	# Save report
	report_file = report_dir / f'test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
	with open(report_file, 'w') as f:
		json.dump(report, f, indent=2)
	
	# Log summary
	logger.info("\nTest Summary:")
	logger.info(f"Total time: {total_time:.2f} seconds")
	for result in results:
		logger.info(f"\n{result['name']}:")
		logger.info(f"  Tests run: {result['total']}")
		logger.info(f"  Failures: {result['failures']}")
		logger.info(f"  Errors: {result['errors']}")
		logger.info(f"  Success: {result['success']}")
	
	# Exit with appropriate code
	sys.exit(0 if report['overall_success'] else 1)

if __name__ == '__main__':
	main()