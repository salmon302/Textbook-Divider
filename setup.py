from setuptools import setup, find_packages

setup(
	name="textbook_divider",
	version="0.1",
	packages=find_packages(),
	install_requires=[
		"PyPDF2>=3.0.0",
		"ebooklib>=0.17.1",
		"html2text>=2020.1.16",
		"pytesseract>=0.3.13",
		"Pillow>=10.0.0",
		"numpy>=2.2.2",
		"opencv-python>=4.8.0",
		"fpdf>=1.7.2",
		"psutil>=5.9.0",
		"pdfminer.six>=20221105",
		"pdf2image>=1.16.3",
		"jpype1>=1.4.1",
		"py4j>=0.10.9.7",
		"requests>=2.31.0",
		"tqdm>=4.66.1",
		"PyMuPDF>=1.23.0",
		"networkx>=2.5",
		"pytest>=6.0.0"
	],
	python_requires=">=3.8",
)

