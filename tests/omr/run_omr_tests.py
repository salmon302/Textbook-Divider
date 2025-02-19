import unittest
import json
import sys
import time
from pathlib import Path
from datetime import datetime
import logging
from test_omr import TestOMR

def setup_logging():
	"""Configure logging for test execution"""
	log_dir = Path(__file__).parent.parent / 'logs'
	log_dir.mkdir(exist_ok=True)
	
	timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
	log_file = log_dir / f'omr_test_{timestamp}.log'
	
	logging.basicConfig(
		level=logging.INFO,
		format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
		handlers=[
			logging.FileHandler(log_file),
			logging.StreamHandler(sys.stdout)
		]
	)
	return logging.getLogger(__name__)

def run_test_suite():
	"""Run the OMR test suite and collect results"""
	logger = setup_logging()
	
	# Create test suite
	suite = unittest.TestLoader().loadTestsFromTestCase(TestOMR)
	
	# Run tests and collect results
	start_time = time.time()
	result = unittest.TextTestRunner(verbosity=2).run(suite)
	end_time = time.time()
	
	# Generate test report
	report = {
		'timestamp': datetime.now().isoformat(),
		'total_tests': result.testsRun,
		'passed': result.testsRun - len(result.failures) - len(result.errors),
		'failures': len(result.failures),
		'errors': len(result.errors),
		'execution_time': end_time - start_time,
		'test_details': {
			'failures': [
				{
					'test': test[0]._testMethodName,
					'message': str(test[1])
				} for test in result.failures
			],
			'errors': [
				{
					'test': test[0]._testMethodName,
					'message': str(test[1])
				} for test in result.errors
			]
		}
	}
	
	# Save report
	reports_dir = Path(__file__).parent.parent / 'reports'
	reports_dir.mkdir(exist_ok=True)
	
	report_file = reports_dir / f'omr_test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
	with report_file.open('w') as f:
		json.dump(report, f, indent=2)
	
	logger.info(f"Test report saved to {report_file}")
	return report

if __name__ == '__main__':
	report = run_test_suite()
	print(f"\nTest Summary:")
	print(f"Total Tests: {report['total_tests']}")
	print(f"Passed: {report['passed']}")
	print(f"Failed: {report['failures']}")
	print(f"Errors: {report['errors']}")
	print(f"Execution Time: {report['execution_time']:.2f} seconds")