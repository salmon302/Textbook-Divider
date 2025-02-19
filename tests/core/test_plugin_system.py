#!/usr/bin/env python3

import unittest
from pathlib import Path
import json
import shutil
import tempfile
from textbook_divider.plugin_system import PluginManager
from textbook_divider.main import TextbookDivider

class TestPluginSystem(unittest.TestCase):
	def setUp(self):
		self.test_dir = Path(__file__).parent.parent
		self.temp_dir = Path(tempfile.mkdtemp())
		self.plugin_dir = self.temp_dir / 'plugins'
		self.plugin_dir.mkdir()
		
		# Copy test plugins to temp directory
		src_plugins = Path(__file__).parent.parent.parent / 'src' / 'textbook_divider' / 'plugins'
		if src_plugins.exists():
			shutil.copytree(src_plugins, self.plugin_dir, dirs_exist_ok=True)
			
	def tearDown(self):
		shutil.rmtree(self.temp_dir)
		
	def test_plugin_loading(self):
		"""Test plugin loading and initialization"""
		manager = PluginManager(self.plugin_dir)
		plugins = manager.list_plugins()
		
		self.assertIn("ocr_processor", plugins)
		self.assertIn("omr_processor", plugins)
		
		# Test plugin retrieval
		ocr_plugin = manager.get_plugin("ocr_processor")
		self.assertIsNotNone(ocr_plugin)
		self.assertEqual(ocr_plugin.name, "ocr_processor")
		
	def test_plugin_processing(self):
		"""Test plugin processing functionality"""
		divider = TextbookDivider(plugin_dir=self.plugin_dir)
		test_file = self.test_dir / 'sample_books' / 'mixed_layout.pdf'
		output_dir = self.temp_dir / 'output'
		
		output_files = divider.process_book(str(test_file), str(output_dir))
		
		# Verify output
		self.assertTrue(len(output_files) > 0)
		
		# Check metadata
		metadata_file = output_dir / f"{test_file.stem}_metadata.json"
		self.assertTrue(metadata_file.exists())
		
		with open(metadata_file) as f:
			metadata = json.load(f)
			self.assertIn("plugins_used", metadata)
			self.assertIn("ocr_processor", metadata["plugins_used"])
			self.assertIn("omr_processor", metadata["plugins_used"])
			
	def test_plugin_configuration(self):
		"""Test plugin configuration loading"""
		config = {
			"ocr_processor": {
				"language": "eng",
				"force_ocr": True
			},
			"omr_processor": {
				"cache_dir": str(self.temp_dir / "omr_cache")
			}
		}
		
		# Write test configuration
		config_file = self.plugin_dir / 'plugin_config.json'
		with open(config_file, 'w') as f:
			json.dump(config, f)
			
		manager = PluginManager(self.plugin_dir)
		ocr_plugin = manager.get_plugin("ocr_processor")
		
		self.assertIsNotNone(ocr_plugin)
		self.assertEqual(ocr_plugin._config["language"], "eng")
		self.assertTrue(ocr_plugin._config["force_ocr"])

if __name__ == '__main__':
	unittest.main()