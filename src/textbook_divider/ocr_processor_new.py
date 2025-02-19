import logging
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont
from typing import Dict, Any

class OCRProcessor:
	"""OCR processor with confidence scoring capabilities"""
	
	def __init__(self, lang: str = 'eng', config: str = '--psm 3'):
		self.lang = lang
		self.config = config
		self.logger = logging.getLogger(__name__)
		
	def get_stats(self) -> Dict[str, Any]:
		"""Get processing statistics"""
		return {
			"language": self.lang,
			"config": self.config
		}
		
	def get_confidence_score(self, text: str) -> float:
		"""Calculate confidence score for OCR text based on word recognition"""
		try:
			image = self._text_to_image(text)
			data = pytesseract.image_to_data(
				image,
				lang=self.lang,
				config=self.config,
				output_type=pytesseract.Output.DICT
			)
			
			confidences = [float(conf) for conf in data['conf'] if conf != '-1']
			if not confidences:
				return 0.0
				
			word_lengths = [len(word) for word in data['text'] if word.strip()]
			weighted_conf = sum(conf * length for conf, length in zip(confidences, word_lengths))
			total_length = sum(word_lengths)
			
			return weighted_conf / total_length if total_length > 0 else 0.0
			
		except Exception as e:
			self.logger.error(f"Failed to calculate confidence score: {str(e)}")
			return 0.0

	def _text_to_image(self, text: str) -> Image.Image:
		"""Convert text to image for OCR analysis"""
		width = 1000
		height = max(200, len(text.split('\n')) * 30)
		image = Image.new('L', (width, height), 255)
		draw = ImageDraw.Draw(image)
		
		try:
			font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
		except:
			font = ImageFont.load_default()
		
		draw.text((10, 10), text, font=font, fill=0)
		return image