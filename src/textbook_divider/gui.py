import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
from .main import TextbookDivider

class TextbookDividerGUI:
	def __init__(self):
		self.root = tk.Tk()
		self.root.title("Textbook Divider")
		self.root.geometry("500x400")
		
		# Create main frame
		main_frame = ttk.Frame(self.root, padding="10")
		main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
		
		# Input file selection
		ttk.Label(main_frame, text="Input File:").grid(row=0, column=0, sticky=tk.W)
		self.input_file = ttk.Entry(main_frame, width=50)
		self.input_file.grid(row=0, column=1, padx=5)
		ttk.Button(main_frame, text="Browse", command=self.browse_input).grid(row=0, column=2)
		
		# Output directory selection
		ttk.Label(main_frame, text="Output Dir:").grid(row=1, column=0, sticky=tk.W)
		self.output_dir = ttk.Entry(main_frame, width=50)
		self.output_dir.grid(row=1, column=1, padx=5)
		ttk.Button(main_frame, text="Browse", command=self.browse_output).grid(row=1, column=2)
		
		# Progress bar
		self.progress = ttk.Progressbar(main_frame, length=400, mode='determinate')
		self.progress.grid(row=2, column=0, columnspan=3, pady=10)
		
		# Process button
		self.process_btn = ttk.Button(main_frame, text="Process", command=self.process)
		self.process_btn.grid(row=3, column=0, columnspan=3)
		
		# Status text
		self.status_text = tk.Text(main_frame, height=10, width=50)
		self.status_text.grid(row=4, column=0, columnspan=3, pady=10)
		self.status_text.insert('1.0', "Ready to process. Please select input file and output directory.")
		
		# Configure grid
		for child in main_frame.winfo_children():
			child.grid_configure(padx=5, pady=5)
	
	def browse_input(self):
		filetypes = [
			('Supported Files', '*.pdf;*.epub;*.txt'),
			('PDF Files', '*.pdf'),
			('EPUB Files', '*.epub'),
			('Text Files', '*.txt'),
			('All Files', '*.*')
		]
		filename = filedialog.askopenfilename(filetypes=filetypes)
		if filename:
			self.input_file.delete(0, tk.END)
			self.input_file.insert(0, filename)
			self.status_text.delete('1.0', tk.END)
			self.status_text.insert('1.0', f"Selected file: {Path(filename).name}\nReady to process.")
	
	def browse_output(self):
		dirname = filedialog.askdirectory()
		if dirname:
			self.output_dir.delete(0, tk.END)
			self.output_dir.insert(0, dirname)
			self.status_text.delete('1.0', tk.END)
			self.status_text.insert('1.0', f"Output directory: {dirname}\nReady to process.")
	
	def process(self):
		input_path = self.input_file.get()
		output_path = self.output_dir.get()
		
		if not input_path or not output_path:
			self.status_text.delete('1.0', tk.END)
			self.status_text.insert('1.0', "Please select both input file and output directory")
			return
		
		try:
			self.progress['value'] = 0
			self.process_btn['state'] = 'disabled'
			self.status_text.delete('1.0', tk.END)
			self.status_text.insert('1.0', f"Processing {input_path}...\n")
			
			divider = TextbookDivider()
			self.progress['value'] = 50
			output_files = divider.process_book(input_path, output_path)
			self.progress['value'] = 100
			
			status_text = f"Successfully processed into {len(output_files)} chapters:\n"
			for file in output_files:
				status_text += f"- {Path(file).name}\n"
			
			self.status_text.delete('1.0', tk.END)
			self.status_text.insert('1.0', status_text)
		except Exception as e:
			self.status_text.delete('1.0', tk.END)
			self.status_text.insert('1.0', f"Error: {str(e)}")
		finally:
			self.process_btn['state'] = 'normal'
	
	def run(self):
		self.root.mainloop()

def main():
	gui = TextbookDividerGUI()
	gui.run()

if __name__ == '__main__':
	main()
