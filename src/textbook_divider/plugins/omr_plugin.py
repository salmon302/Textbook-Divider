from textbook_divider.plugin_system import Plugin
from textbook_divider.omr_processor import OMRProcessor
from typing import Dict, Any
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class OMRPlugin(Plugin):
	def __init__(self):
		self._processor = None
		self._config = {}
		
	@property
	def name(self) -> str:
		return "omr_processor"
		
	def initialize(self, config: Dict[str, Any]) -> None:
		"""Initialize OMR processor with config"""
		self._config = config
		cache_dir = config.get('cache_dir')
		if cache_dir:
			cache_dir = Path(cache_dir)
			
		self._processor = OMRProcessor(cache_dir=cache_dir)
		
	def process(self, content: Any) -> Dict[str, Any]:
		"""Process content using OMR"""
		if not self._processor:
			raise RuntimeError("OMR processor not initialized")
			
		try:
			result = self._processor.process_page(content)
			
			# Enhance result with additional metrics
			enhanced_result = {
				"success": result.get("success", False),
				"engine": result.get("engine", "unknown"),
				"has_music": result.get("has_music", False),
				"staff_positions": result.get("staff_positions", []),
				"symbol_confidence": result.get("symbol_confidence", {}),
				"recovery_attempted": result.get("recovery_attempted", False)
			}
			
			# Add error details if present
			if not enhanced_result["success"]:
				enhanced_result["error"] = result.get("error")
				enhanced_result["error_details"] = result.get("error_details", {})
				
			return enhanced_result
			
		except Exception as e:
			logger.error(f"OMR processing failed: {e}")
			return {
				"success": False,
				"error": str(e),
				"has_music": False,
				"recovery_attempted": True,
				"error_details": {
					"type": type(e).__name__,
					"message": str(e),
					"recovery_possible": True
				}
			}