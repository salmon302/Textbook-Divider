from pathlib import Path
from src.textbook_divider.processor import process_file

def main():
	input_file = Path("/home/seth-n/CLionProjects/Textbook Divider/input/(Oxford Studies in Music Theory) Dmitri Tymoczko - A Geometry of Music_ Harmony and Counterpoint in the Extended Common Practice-Oxford University Press (2011).pdf")
	process_file(input_file)


if __name__ == "__main__":
	main()