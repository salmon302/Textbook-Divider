import logging
import json
from pathlib import Path
from datetime import datetime
from functools import wraps
import inspect

def get_test_logger(test_name):
	"""Get a logger configured for a specific test module"""
	logger = logging.getLogger(test_name)
	
	if not logger.handlers:
		# Set up log directory
		log_dir = Path(__file__).parent.parent / 'logs'
		log_dir.mkdir(exist_ok=True)
		
		# Create log file with timestamp
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		log_file = log_dir / f'{test_name}_{timestamp}.log'
		
		# Configure handlers
		file_handler = logging.FileHandler(log_file)
		console_handler = logging.StreamHandler()
		
		# Set formats
		formatter = logging.Formatter(
			'%(asctime)s - %(name)s - %(levelname)s - %(message)s'
		)
		file_handler.setFormatter(formatter)
		console_handler.setFormatter(formatter)
		
		# Add handlers
		logger.addHandler(file_handler)
		logger.addHandler(console_handler)
		logger.setLevel(logging.DEBUG)
	
	return logger

def log_test_case(func):
	"""Decorator to log test case execution"""
	@wraps(func)
	def wrapper(self, *args, **kwargs):
		logger = get_test_logger(self.__class__.__module__)
		test_name = func.__name__
		
		logger.info(f"Starting test: {test_name}")
		logger.debug(f"Test function signature: {inspect.signature(func)}")
		
		try:
			result = func(self, *args, **kwargs)
			logger.info(f"Test completed successfully: {test_name}")
			return result
		except Exception as e:
			logger.error(f"Test failed: {test_name}")
			logger.exception(e)
			raise
	
	return wrapper

def log_test_data(data, category):
	"""Log test data with proper formatting"""
	logger = get_test_logger('test_data')
	if isinstance(data, (dict, list)):
		logger.debug(f"{category}: {json.dumps(data, indent=2)}")
	else:
		logger.debug(f"{category}: {data}")