from PIL import Image, ImageDraw, ImageFont
import numpy as np
from ocr_processor import OCRProcessor

# Create a simple test image with text
def create_test_image():
	img = Image.new('RGB', (200, 50), color='white')
	d = ImageDraw.Draw(img)
	d.text((10,10), "Hello World", fill='black')
	return img

def main():
	# Create test image
	test_image = create_test_image()
	
	# Initialize OCR processor
	processor = OCRProcessor()
	
	# Process the image
	result = processor.process_image(test_image)
	print("OCR Result:", result)

if __name__ == "__main__":
	main()