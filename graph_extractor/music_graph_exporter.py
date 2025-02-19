from typing import Dict, List, Optional
import json
import xml.etree.ElementTree as ET
from .graph_types import MusicTheoryGraph, Node, Edge, NodeType

class MusicGraphExporter:
	def __init__(self):
		self.export_formats = {
			'musicxml': self._export_musicxml,
			'humdrum': self._export_humdrum,
			'lilypond': self._export_lilypond,
			'mei': self._export_mei
		}
		
	def export(self, graph: MusicTheoryGraph, 
			   format: str, filepath: str) -> None:
		if format not in self.export_formats:
			raise ValueError(f"Unsupported format: {format}")
			
		export_func = self.export_formats[format]
		export_func(graph, filepath)
		
	def _export_musicxml(self, graph: MusicTheoryGraph, filepath: str) -> None:
		root = ET.Element("score-partwise", version="4.0")
		
		# Add part-list
		part_list = ET.SubElement(root, "part-list")
		score_part = ET.SubElement(part_list, "score-part", id="P1")
		ET.SubElement(score_part, "part-name").text = "Music Graph"
		
		# Create main part
		part = ET.SubElement(root, "part", id="P1")
		
		# Convert nodes to measures
		self._add_measures_from_nodes(part, graph)
		
		# Write to file
		tree = ET.ElementTree(root)
		tree.write(filepath, encoding="utf-8", xml_declaration=True)
		
	def _export_humdrum(self, graph: MusicTheoryGraph, filepath: str) -> None:
		lines = []
		
		# Add header
		lines.append("!!!COM: Music Theory Graph")
		lines.append("**kern\t**dynam")
		
		# Convert nodes to spine entries
		for node in graph.nodes.values():
			if node.type == NodeType.PITCH_CLASS:
				lines.append(f"{node.label}\t.")
			elif node.type == NodeType.TRANSFORMATION:
				lines.append(f".\t{node.label}")
				
		# Write to file
		with open(filepath, 'w') as f:
			f.write('\n'.join(lines))
			
	def _export_lilypond(self, graph: MusicTheoryGraph, filepath: str) -> None:
		lines = []
		
		# Add header
		lines.append('\\version "2.20.0"')
		lines.append('\\header {')
		lines.append('  title = "Music Theory Graph"')
		lines.append('}')
		
		# Start score
		lines.append('\\score {')
		
		# Convert nodes to music
		music_lines = self._nodes_to_lilypond(graph)
		lines.extend(['  ' + line for line in music_lines])
		
		# Close score
		lines.append('}')
		
		# Write to file
		with open(filepath, 'w') as f:
			f.write('\n'.join(lines))
			
	def _export_mei(self, graph: MusicTheoryGraph, filepath: str) -> None:
		# Create MEI root
		mei = ET.Element("mei")
		mei.set("xmlns", "http://www.music-encoding.org/ns/mei")
		
		# Add header
		header = ET.SubElement(mei, "meiHead")
		file_desc = ET.SubElement(header, "fileDesc")
		title_stmt = ET.SubElement(file_desc, "titleStmt")
		ET.SubElement(title_stmt, "title").text = "Music Theory Graph"
		
		# Create music element
		music = ET.SubElement(mei, "music")
		body = ET.SubElement(music, "body")
		mdiv = ET.SubElement(body, "mdiv")
		score = ET.SubElement(mdiv, "score")
		
		# Convert nodes to MEI elements
		self._add_mei_elements(score, graph)
		
		# Write to file
		tree = ET.ElementTree(mei)
		tree.write(filepath, encoding="utf-8", xml_declaration=True)
		
	def _add_measures_from_nodes(self, part: ET.Element, 
								graph: MusicTheoryGraph) -> None:
		measure = ET.SubElement(part, "measure", number="1")
		attributes = ET.SubElement(measure, "attributes")
		
		# Add time signature
		time = ET.SubElement(attributes, "time")
		ET.SubElement(time, "beats").text = "4"
		ET.SubElement(time, "beat-type").text = "4"
		
		# Convert nodes to notes
		for node in graph.nodes.values():
			if node.type == NodeType.PITCH_CLASS:
				note = ET.SubElement(measure, "note")
				pitch = ET.SubElement(note, "pitch")
				ET.SubElement(pitch, "step").text = node.label[0]
				if len(node.label) > 1:
					ET.SubElement(pitch, "alter").text = "1" if node.label[1] == "#" else "-1"
				ET.SubElement(note, "duration").text = "4"
				
	def _nodes_to_lilypond(self, graph: MusicTheoryGraph) -> List[str]:
		lines = []
		lines.append('\\new Staff {')
		
		# Convert nodes to notes
		notes = []
		for node in graph.nodes.values():
			if node.type == NodeType.PITCH_CLASS:
				note = node.label.lower()
				if '#' in note:
					note = note.replace('#', 'is')
				elif 'b' in note:
					note = note.replace('b', 'es')
				notes.append(note + "4")
				
		if notes:
			lines.append('  ' + ' '.join(notes))
			
		lines.append('}')
		return lines
		
	def _add_mei_elements(self, score: ET.Element, 
						 graph: MusicTheoryGraph) -> None:
		section = ET.SubElement(score, "section")
		staff = ET.SubElement(section, "staff")
		layer = ET.SubElement(staff, "layer")
		
		# Convert nodes to MEI elements
		for node in graph.nodes.values():
			if node.type == NodeType.PITCH_CLASS:
				note = ET.SubElement(layer, "note")
				note.set("pname", node.label[0].lower())
				if len(node.label) > 1:
					note.set("accid", "s" if node.label[1] == "#" else "f")
				note.set("dur", "4")