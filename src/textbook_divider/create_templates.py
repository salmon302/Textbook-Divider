#!/usr/bin/env python3

import cv2
import numpy as np
from pathlib import Path

def create_basic_templates():
	"""Create basic musical notation templates"""
	base_dir = Path(__file__).parent / 'templates'
	
	# Create template directories
	template_dirs = ['notes', 'clefs', 'time_signatures', 'accidentals']
	for dir_name in template_dirs:
		(base_dir / dir_name).mkdir(parents=True, exist_ok=True)
	
	# Create quarter note
	note = np.full((50, 30), 255, dtype=np.uint8)
	cv2.circle(note, (15, 35), 6, 0, -1)  # note head
	cv2.line(note, (21, 35), (21, 10), 0, 2)  # stem
	cv2.imwrite(str(base_dir / 'notes' / 'quarter_note.png'), note)
	
	# Create treble clef
	clef = np.full((80, 40), 255, dtype=np.uint8)
	cv2.ellipse(clef, (20, 50), (15, 20), 0, 0, 360, 0, 2)
	cv2.ellipse(clef, (20, 25), (10, 15), 0, 0, 360, 0, 2)
	cv2.line(clef, (20, 65), (20, 15), 0, 2)
	cv2.imwrite(str(base_dir / 'clefs' / 'treble_clef.png'), clef)
	
	# Create time signature
	time_sig = np.full((60, 30), 255, dtype=np.uint8)
	cv2.putText(time_sig, "4", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 1, 0, 2)
	cv2.putText(time_sig, "4", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, 0, 2)
	cv2.imwrite(str(base_dir / 'time_signatures' / '4_4.png'), time_sig)
	
	# Create sharp symbol
	sharp = np.full((40, 20), 255, dtype=np.uint8)
	cv2.line(sharp, (5, 10), (15, 10), 0, 2)  # horizontal lines
	cv2.line(sharp, (5, 30), (15, 30), 0, 2)
	cv2.line(sharp, (8, 5), (8, 35), 0, 2)    # vertical lines
	cv2.line(sharp, (12, 5), (12, 35), 0, 2)
	cv2.imwrite(str(base_dir / 'accidentals' / 'sharp.png'), sharp)

if __name__ == '__main__':
	create_basic_templates()
