from textbook_divider.plugin_system import Plugin
from textbook_divider.ocr_processor import OCRProcessor
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class OCRPlugin(Plugin):
	def __init__(self):
		self._processor = None
		self._config = {}
		
	@property
	def name(self) -> str:
		return "ocr_processor"
		
	def initialize(self, config: Dict[str, Any]) -> None:
		"""Initialize OCR processor with config"""
		self._config = config
		self._processor = OCRProcessor(
			lang=config.get('language', 'eng'),
			enable_gpu=config.get('enable_gpu', False),
			cache_size=config.get('cache_size', 1000)
		)
		
	def process(self, content: Any) -> Dict[str, Any]:
		"""Process content using OCR"""
		if not self._processor:
			raise RuntimeError("OCR processor not initialized")
			
		try:
			text = self._processor.process_image(content)
			return {
				"text": text,
				"confidence": 1.0 if text else 0.0,
				"language": self._config.get("language", "eng"),
				"success": bool(text)
			}
		except Exception as e:
			logger.error(f"OCR processing failed: {e}")
			return {
				"text": "",
				"confidence": 0.0,
				"error": str(e),
				"success": False
			}