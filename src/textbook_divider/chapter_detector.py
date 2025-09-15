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

	def __init__(
		self,
		debug: bool = False,
		min_confidence: float = 0.5,
		enable_title_line: bool = True,
		header_months: Optional[List[str]] = None,
		header_keywords: Optional[List[str]] = None,
	):
		self.logger = logging.getLogger(__name__)
		self.logger.setLevel(logging.DEBUG if debug else logging.INFO)

		# Tunables
		self.min_chapter_length = 10
		self.max_title_length = 200
		self.min_confidence = float(min_confidence)
		self.enable_title_line = bool(enable_title_line)

		# Preference order when multiple patterns hit the same position
		self.pattern_priority: Dict[str, int] = {
			'standard': 100,
			'ocr_chapter': 95,
			'section': 90,
			'appendix': 88,
			'nested': 85,
			'numbered': 80,
			'title_line': 60,
		}

		# Common header/footer words to avoid as titles (helps filter OCR page headers)
		default_months = {
			"JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
			"JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"
		}
		self.month_stopwords = set(m.upper() for m in (header_months or [])) or default_months

		# Additional common running header/footer keywords (journal/issue markers etc.)
		default_header_keywords = {
			"OCTOBER", "OCT", "VOLUME", "VOL", "NO", "NUMBER", "ISSUE",
			"CONTENTS", "INDEX"
		}
		self.header_keywords = set(k.upper() for k in (header_keywords or [])) or default_header_keywords

		# Reasonable upper bound for numeric chapter indices (helps filter years like 1937)
		self.max_reasonable_chapter_num = 300

		# Compile patterns after tunables are set
		self._compile_patterns()

	
	def _compile_patterns(self):
		"""Compile enhanced chapter detection patterns with OCR tolerance"""
		patterns: Dict[str, Pattern] = {
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
			),
		}

		if self.enable_title_line:
			patterns['title_line'] = re.compile(
				r'^\s*((?:'
				 r'(?:[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){0,5})'
				 r'|'
				 r'(?:[A-Z]{3,}(?:\s+[A-Z]{3,}){0,5})'
				 r'|'
				 r'(?:[A-Z][a-z]+[A-Z][A-Za-z]+)'
				 r'))\s*$',
				re.MULTILINE
			)

		self.patterns = patterns

		
	def detect_chapters(self, text: str) -> List[Chapter]:
		"""Enhanced chapter detection with validation"""
		matches = self._find_potential_chapters(text)
		self.logger.debug("Potential matches: %s", matches)
		matches = self._validate_matches(matches, text)
		self.logger.debug("Validated matches: %s", matches)
		# Deduplicate overlapping matches that start at the same location (or within a few chars)
		matches = self._deduplicate_matches(matches)
		self.logger.debug("Deduplicated matches: %s", matches)
		chapters = self._create_chapters(matches, text)
		self.logger.debug("Created chapters: %s", 
			[(ch.number, ch.title, ch.confidence) for ch in chapters])
		chapters = self._validate_chapters(chapters)
		self.logger.debug("Final chapters: %s",
			[(ch.number, ch.title, ch.confidence) for ch in chapters])

		return chapters

	def _deduplicate_matches(self, matches: List[Tuple]) -> List[Tuple]:
		"""Collapse overlapping/duplicate matches at the same start position.

		Keeps the match with highest confidence; ties broken by pattern priority and
		finally by longer non-empty title. Matches within a small offset window are
		treated as duplicates (to accommodate slight regex start differences).
		"""
		if not matches:
			return matches

		# Ensure sorted by start position
		sorted_matches = sorted(matches, key=lambda m: m[0])
		DEDUP_WINDOW = 3  # characters
		collapsed: List[Tuple] = []
		buffer: List[Tuple] = []

		def flush_buffer(buf: List[Tuple]):
			if not buf:
				return None
			# Choose best candidate from buffer
			best = buf[0]
			for cand in buf[1:]:
				# Tuple layout: (start_pos, num, title, pattern_type, confidence)
				_, _, title_b, pat_b, conf_b = cand
				_, _, title_a, pat_a, conf_a = best
				if conf_b > conf_a:
					best = cand
				elif conf_b == conf_a:
					# Tie-breaker: pattern priority
					pa = self.pattern_priority.get(pat_a, 0)
					pb = self.pattern_priority.get(pat_b, 0)
					if pb > pa:
						best = cand
					elif pb == pa:
						# Final tie-breaker: prefer longer non-empty title
						if len((title_b or '').strip()) > len((title_a or '').strip()):
							best = cand
			collapsed.append(best)

		# Group matches by proximity of start positions
		current_start = None
		for m in sorted_matches:
			start_pos = m[0]
			if current_start is None:
				buffer = [m]
				current_start = start_pos
				continue
			if abs(start_pos - current_start) <= DEDUP_WINDOW:
				buffer.append(m)
			else:
				flush_buffer(buffer)
				buffer = [m]
				current_start = start_pos

		# Flush remaining
		flush_buffer(buffer)

		# Return sorted by start position again
		return sorted(collapsed, key=lambda m: m[0])
	
	def _find_potential_chapters(self, text: str) -> List[Tuple]:
		"""Find all potential chapter matches with pattern type"""
		matches = []
		for pattern_type, pattern in self.patterns.items():
			for match in pattern.finditer(text):
				start_pos = match.start()
				groups = match.groups()
				if pattern_type == 'nested' and len(groups) >= 3:
					parent_num = groups[0]
					sub_num = groups[1]
					title = groups[2]
					num = f"{parent_num}.{sub_num}"
				elif pattern_type == 'title_line' and len(groups) >= 1:
					# Heuristic title without explicit number
					num = '0'
					title = groups[0]
				else:
					num = groups[0] if len(groups) >= 1 and groups[0] else '1'
					title = groups[1] if len(groups) >= 2 else ''
				
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

			# Fetch the full line where the match occurs for header/footer checks
			line_start = text.rfind('\n', 0, start_pos) + 1
			line_end = text.find('\n', start_pos)
			if line_end == -1:
				line_end = len(text)
			full_line = text[line_start:line_end].strip()

			# Filter probable running headers like "66 OCTOBER" or "OCTOBER 66" (with OCR variants)
			if self._looks_like_running_header(full_line):
				continue

			# Filter obvious page headers like "4 OCTOBER" captured by 'numbered' pattern
			if pattern_type == 'numbered':
				title_upper = title.strip().upper()
				first_word = title_upper.split()[0] if title_upper else ''
				# Hard match or fuzzy match to months (to catch OCR like "OBER" for OCTOBER)
				if first_word in self.month_stopwords or title_upper in self.month_stopwords or self._is_similar_to_month(first_word):
					continue
			
			# Reject standalone year-like titles (e.g., "1937" or "1939-40")
			if self._is_year_like(title):
				continue

			# Reject implausible numeric "chapter" numbers (likely years)
			try:
				num_val = int(str(num))
				if num_val > self.max_reasonable_chapter_num and pattern_type != 'nested':
					# Allow nested numbers like 1.2 etc., but drop large plain numbers
					continue
			except ValueError:
				pass

			# Calculate confidence score
			confidence = self._calculate_confidence(match, text)
			
			if confidence >= self.min_confidence:
				validated.append((*match, confidence))
		
		return validated

	def _is_similar_to_month(self, token: str) -> bool:
		"""Fuzzy check if token is similar to an English month (handles OCR glitches like 'OBER')."""
		token = (token or '').upper()
		if not token:
			return False
		for month in self.month_stopwords:
			# Quick length guard
			if abs(len(month) - len(token)) > 3:
				continue
			# Use SequenceMatcher ratio for fuzzy match
			if SequenceMatcher(None, month, token).ratio() >= 0.6:
				return True
		return False

	def _looks_like_running_header(self, line: str) -> bool:
		"""Heuristic to detect running headers/footers with page numbers and uppercase tokens."""
		if not line:
			return False
		L = line.strip()
		U = L.upper()
		# Patterns: 'NNN WORD...' or 'WORD NNN...'
		m1 = re.match(r'^(\d{1,4})\s+([A-Z]{3,})(?:\b|\s|$)', U)
		m2 = re.match(r'^([A-Z]{3,})\s+(\d{1,4})(?:\b|\s|$)', U)
		candidate = None
		if m1:
			candidate = m1.group(2)
		elif m2:
			candidate = m2.group(1)
		if candidate:
			# Direct keyword or fuzzy-month match
			if candidate in self.header_keywords or candidate in self.month_stopwords or self._is_similar_to_month(candidate):
				return True
			# Short ALL-CAPS token that is unlikely to be a chapter title
			if len(candidate) <= 10 and candidate.isalpha() and candidate == candidate.upper():
				# If rest of line has no obvious title punctuation, treat as header
				if not re.search(r'[:\-–—]', L):
					return True
		return False
	
	def _calculate_confidence(self, match: Tuple, text: str) -> float:
		start_pos, num, title, pattern_type = match
		confidence = 1.0
		
		pattern_weights = {
			'standard': 1.0,
			'nested': 0.95,
			'section': 0.9,
			'numbered': 0.8,
			'appendix': 0.9,
			'ocr_chapter': 0.85,
			'title_line': 0.7
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

		# Additional heuristics for title_line
		if pattern_type == 'title_line':
			title_stripped = title.strip()
			title_upper = title_stripped.upper()
			first_word = title_upper.split()[0] if title_upper else ''
			# Skip obvious headers
			if first_word in self.month_stopwords or title_upper in self.month_stopwords:
				confidence = 0.0
			# Hard reject if clearly not a title
			if len(title_stripped) > 70 or re.search(r'[.:]{2,}|\d{3,}|—|-{2,}', title_stripped):
				confidence = 0.0
			# Analyze surrounding lines
			line_start = text.rfind('\n', 0, start_pos) + 1
			line_end = text.find('\n', start_pos)
			if line_end == -1:
				line_end = len(text)
			before_ctx = text[max(0, line_start - 200):line_start]
			after_ctx = text[line_end: min(len(text), line_end + 400)]
			# Slight penalty if no visible separation
			if ('\n\n' not in before_ctx) and ('\n\n' not in after_ctx):
				confidence *= 0.8
			# Boost if followed by a long paragraph (typical body text)
			next_line_end = after_ctx.find('\n')
			if next_line_end == -1:
				next_line_end = len(after_ctx)
			next_line = after_ctx[:next_line_end].strip()
			if len(next_line) > 80 and not next_line.isupper():
				confidence *= 1.4
			# Demote if next line also looks like a short title (likely header/footer)
			elif 0 < len(next_line) <= 40 and (next_line.isupper() or re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$', next_line)):
				confidence *= 0.6
		
		# Boost confidence for clean chapter numbers
		try:
			if pattern_type in ['standard', 'numbered', 'ocr_chapter']:
				chapter_num = int(num)
				if 1 <= chapter_num <= 50:  # Extended reasonable chapter range
					confidence *= 1.2
				# Penalize implausibly large numeric indices (likely years)
				if chapter_num > self.max_reasonable_chapter_num:
					confidence *= 0.1
		except ValueError:
			pass
		
		return min(confidence, 1.0)

	def _is_year_like(self, s: str) -> bool:
		"""Return True if string looks like a standalone year or year range (e.g., 1937, 1939-40)."""
		if not s:
			return False
		s = s.strip()
		# Pure 4-digit
		if re.fullmatch(r'(?:18|19|20)\d{2}', s):
			return True
		# Range like 1939-40 or 1939-1940
		if re.fullmatch(r'(?:18|19|20)\d{2}\s*[-–—]\s*(?:\d{2}|(?:18|19|20)\d{2})', s):
			return True
		return False
	
	def _create_chapters(self, matches: List[Tuple], text: str) -> List[Chapter]:
		"""Create chapter objects with enhanced metadata"""
		chapters = []
		current_main_chapter = 0
		
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
				# Assign sequential numbering if no explicit number was detected
				if chapter_num == 0 and not is_subchapter:
					chapter_num = (current_main_chapter or 0) + 1
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