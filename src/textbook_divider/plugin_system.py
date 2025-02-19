from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path
import importlib.util
import logging
import json

logger = logging.getLogger(__name__)

class Plugin(ABC):
	"""Base class for all plugins"""
	
	@abstractmethod
	def initialize(self, config: Dict[str, Any]) -> None:
		"""Initialize plugin with configuration"""
		pass
		
	@abstractmethod
	def process(self, content: Any) -> Dict[str, Any]:
		"""Process content and return results"""
		pass
		
	@property
	@abstractmethod
	def name(self) -> str:
		"""Plugin name"""
		pass

class PluginManager:
	"""Manages plugin loading and execution"""
	
	def __init__(self, plugin_dir: Optional[Path] = None):
		self.plugins: Dict[str, Plugin] = {}
		self.plugin_dir = plugin_dir or Path(__file__).parent / 'plugins'
		self.plugin_dir.mkdir(exist_ok=True)
		self.config_file = self.plugin_dir / 'plugin_config.json'
		self._load_plugins()
		
	def _load_plugins(self) -> None:
		"""Load all plugins from the plugin directory"""
		if not self.plugin_dir.exists():
			logger.warning(f"Plugin directory not found: {self.plugin_dir}")
			return
			
		# Load plugin configuration
		config = {}
		if self.config_file.exists():
			with open(self.config_file, 'r') as f:
				config = json.load(f)
		
		# Load each plugin module
		for plugin_file in self.plugin_dir.glob('*.py'):
			if plugin_file.stem.startswith('__'):
				continue
				
			try:
				spec = importlib.util.spec_from_file_location(
					plugin_file.stem, plugin_file)
				if spec and spec.loader:
					module = importlib.util.module_from_spec(spec)
					spec.loader.exec_module(module)
					
					# Look for Plugin subclasses in the module
					for attr_name in dir(module):
						attr = getattr(module, attr_name)
						if (isinstance(attr, type) and 
							issubclass(attr, Plugin) and 
							attr != Plugin):
							plugin = attr()
							plugin_config = config.get(plugin.name, {})
							plugin.initialize(plugin_config)
							self.plugins[plugin.name] = plugin
							logger.info(f"Loaded plugin: {plugin.name}")
							
			except Exception as e:
				logger.error(f"Failed to load plugin {plugin_file}: {e}")
	
	def get_plugin(self, name: str) -> Optional[Plugin]:
		"""Get plugin by name"""
		return self.plugins.get(name)
	
	def list_plugins(self) -> List[str]:
		"""List all loaded plugins"""
		return list(self.plugins.keys())
	
	def process_with_plugin(self, name: str, content: Any) -> Dict[str, Any]:
		"""Process content with specified plugin"""
		plugin = self.get_plugin(name)
		if not plugin:
			raise ValueError(f"Plugin not found: {name}")
		return plugin.process(content)