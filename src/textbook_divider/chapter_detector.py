import re
from typing import List, Tuple, Pattern, Dict, Optional
from dataclasses import dataclass
import logging
from difflib import SequenceMatcher

@dataclass
class Chapter:
	"""Represents a detected chapter with its content"""
	number: int
	title: str
	content: str
	start_pos: int
	end_pos: int
	confidence: float = 1.0
	is_subchapter: bool = False
	parent_chapter: Optional[int] = None

class ChapterDetector:
	"""Enhanced chapter detection with validation and content analysis"""
	
	def __init__(self, debug: bool = False):
		self.logger = logging.getLogger(__name__)
		self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
		self._compile_patterns()
		self.min_chapter_length = 10
		self.max_title_length = 200
		self.min_confidence = 0.5  # Lower threshold for OCR results

	
	def _compile_patterns(self):
		"""Compile enhanced chapter detection patterns with OCR tolerance"""
		self.patterns = {
			'standard': re.compile(
				r'^\s*(?:ch[a-z]*\.?|CH[A-Z]*\.?|[Cc]hapter|CHAPTER)\s*[-\.]?\s*([0-9]+|[IVXLCDM]+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)(?:[:.,-]\s*|\s+)(.*)$',
				re.MULTILINE | re.IGNORECASE
			),
			'nested': re.compile(
				r'^\s*(\d+)[\.,](\d+)\s+(.*)$',
				re.MULTILINE
			),
			'section': re.compile(
				r'^\s*(?:PART|Part|Section|SECTION|Unit|UNIT)\s+([0-9]+|[IVXLCDM]+)(?:[:.,-]\s*|\s+)(.*)$',
				re.MULTILINE
			),
			'numbered': re.compile(
				r'^\s*(?:[\(\[])?([0-9]+|[IVXLCDM]+)(?:[\)\]])?[\s:.,-]+([A-Z][^\n]{2,})$',
				re.MULTILINE
			),
			'appendix': re.compile(
				r'^\s*(?:Appendix|APPENDIX)\s+([A-Z0-9]+)(?:[:.,-]\s*|\s+)(.*)$',
				re.MULTILINE
			),
			'ocr_chapter': re.compile(
				r'^\s*[cC][hH][aA][pP][tT][eE][rR]\s*([0-9]+|[IVXLCDM]+)(?:[:.,-]\s*|\s+)(.*)$',
				re.MULTILINE
			)
		}

		
	def detect_chapters(self, text: str) -> List[Chapter]:
		"""Enhanced chapter detection with validation"""
		matches = self._find_potential_chapters(text)
		self.logger.debug("Potential matches: %s", matches)
		matches = self._validate_matches(matches, text)
		self.logger.debug("Validated matches: %s", matches)
		chapters = self._create_chapters(matches, text)
		self.logger.debug("Created chapters: %s", 
			[(ch.number, ch.title, ch.confidence) for ch in chapters])
		chapters = self._validate_chapters(chapters)
		self.logger.debug("Final chapters: %s",
			[(ch.number, ch.title, ch.confidence) for ch in chapters])

		return chapters
	
	def _find_potential_chapters(self, text: str) -> List[Tuple]:
		"""Find all potential chapter matches with pattern type"""
		matches = []
		for pattern_type, pattern in self.patterns.items():
			for match in pattern.finditer(text):
				start_pos = match.start()
				if pattern_type == 'nested':
					parent_num = match.group(1)
					sub_num = match.group(2)
					title = match.group(3)
					num = f"{parent_num}.{sub_num}"
				else:
					num = match.group(1) if match.group(1) else '1'
					title = match.group(2) if len(match.groups()) > 1 else ''
				
				matches.append((start_pos, num, title.strip(), pattern_type))
		
		return sorted(matches, key=lambda x: x[0])
	
	def _validate_matches(self, matches: List[Tuple], text: str) -> List[Tuple]:
		"""Validate matches and remove false positives"""
		validated = []
		for i, match in enumerate(matches):
			start_pos, num, title, pattern_type = match
			
			# Skip if title is too long
			if len(title) > self.max_title_length:
				continue
			
			# Calculate confidence score
			confidence = self._calculate_confidence(match, text)
			
			if confidence >= self.min_confidence:
				validated.append((*match, confidence))
		
		return validated
	
	def _calculate_confidence(self, match: Tuple, text: str) -> float:
		start_pos, num, title, pattern_type = match
		confidence = 1.0
		
		pattern_weights = {
			'standard': 1.0,
			'nested': 0.95,
			'section': 0.9,
			'numbered': 0.8,
			'appendix': 0.9,
			'ocr_chapter': 0.85
		}
		confidence *= pattern_weights[pattern_type]
		
		# Check surrounding context
		context_start = max(0, start_pos - 100)
		context_end = min(len(text), start_pos + 100)
		context = text[context_start:context_end]
		
		# Less strict OCR artifact checking
		if re.search(r'[^\w\s,.:\-\(\)\[\]]', title):
			confidence *= 0.8
		
		# More lenient title length check
		if len(title.strip()) < 2:
			confidence *= 0.7
		
		# Boost confidence for clean chapter numbers
		try:
			if pattern_type in ['standard', 'numbered', 'ocr_chapter']:
				chapter_num = int(num)
				if 1 <= chapter_num <= 50:  # Extended reasonable chapter range
					confidence *= 1.2
		except ValueError:
			pass
		
		return min(confidence, 1.0)
	
	def _create_chapters(self, matches: List[Tuple], text: str) -> List[Chapter]:
		"""Create chapter objects with enhanced metadata"""
		chapters = []
		current_main_chapter = 1
		
		for i, (start_pos, num, title, pattern_type, confidence) in enumerate(matches):
			end_pos = matches[i + 1][0] if i < len(matches) - 1 else len(text)
			
			# Detect if this is a subchapter
			is_subchapter = False
			parent_chapter = None
			chapter_num = 0
			
			if '.' in str(num):  # Check if it's a nested chapter number
				try:
					parent_num, sub_num = map(int, str(num).split('.'))
					is_subchapter = True
					parent_chapter = parent_num
					chapter_num = sub_num
				except ValueError:
					chapter_num = self._convert_to_number(num)
			else:
				chapter_num = self._convert_to_number(num)
				if not is_subchapter:
					current_main_chapter = chapter_num
			
			chapter_content = text[start_pos:end_pos].strip()
			
			# Preserve formatting in content
			chapter_content = self._preserve_formatting(chapter_content)
			
			chapters.append(Chapter(
				number=chapter_num,
				title=title.strip(),
				content=chapter_content,
				start_pos=start_pos,
				end_pos=end_pos,
				confidence=confidence,
				is_subchapter=is_subchapter,
				parent_chapter=parent_chapter
			))
		
		return chapters
	
	def _validate_chapters(self, chapters: List[Chapter]) -> List[Chapter]:
		"""Validate chapters and their relationships"""
		validated = []
		current_main_chapter = None
		
		for chapter in chapters:
			# Skip empty chapters
			if not chapter.content.strip() or not chapter.title.strip():
				continue
			
			if not chapter.is_subchapter:
				current_main_chapter = chapter.number
			elif current_main_chapter:
				chapter.parent_chapter = current_main_chapter
			
			# Preserve text formatting
			chapter.content = self._preserve_formatting(chapter.content)
			validated.append(chapter)
		
		return validated


	def _preserve_formatting(self, text: str) -> str:
		"""Preserve text formatting like emphasis, code blocks, tables, etc."""
		# First preserve code blocks with language specification
		code_pattern = r'(```(?:\w+)?\n[\s\S]*?\n```)'
		code_blocks = re.findall(code_pattern, text, re.MULTILINE)
		
		# Replace code blocks with placeholders
		for i, block in enumerate(code_blocks):
			text = text.replace(block, f"__CODE_BLOCK_{i}__")
		
		# Preserve tables
		table_pattern = r'(\|[^\n]+\|(?:\n\|[-|\s]+\|)?(?:\n\|[^\n]+\|)*)'
		table_blocks = re.findall(table_pattern, text, re.MULTILINE)
		for i, block in enumerate(table_blocks):
			text = text.replace(block, f"__TABLE_BLOCK_{i}__")
		
		# Preserve inline formatting
		text = re.sub(r'(?<![\*_])\*(?!\*)([^\*\n]+)\*(?!\*)', r'*\1*', text)  # Single asterisk
		text = re.sub(r'(?<![\*_])\*\*(?!\*)([^\*\n]+)\*\*(?!\*)', r'**\1**', text)  # Double asterisk
		text = re.sub(r'(?<![\*_])_([^_\n]+)_(?![\*_])', r'_\1_', text)  # Underscore
		
		# Restore code blocks
		for i, block in enumerate(code_blocks):
			text = text.replace(f"__CODE_BLOCK_{i}__", block)
		
		# Restore table blocks
		for i, block in enumerate(table_blocks):
			text = text.replace(f"__TABLE_BLOCK_{i}__", block)
		
		return text

	
	def _convert_to_number(self, num_str: str) -> int:
		"""Convert string number (arabic, roman, or word) to integer"""
		word_to_num = {
			'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
			'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
		}
		
		# Try direct integer conversion first
		try:
			return int(num_str)
		except ValueError:
			# Try word to number conversion
			num_str_lower = num_str.lower()
			if num_str_lower in word_to_num:
				return word_to_num[num_str_lower]
				
			# Try roman numeral conversion
			try:
				roman_values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
				num_str = num_str.upper()
				result = 0
				
				for i in range(len(num_str)):
					if i > 0 and roman_values[num_str[i]] > roman_values[num_str[i - 1]]:
						result += roman_values[num_str[i]] - 2 * roman_values[num_str[i - 1]]
					else:
						result += roman_values[num_str[i]]
						
				return result
			except (KeyError, IndexError):
				return 0  # Return 0 if conversion fails