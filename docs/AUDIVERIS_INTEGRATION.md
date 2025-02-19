# Audiveris Integration Plan

## Prerequisites
1. Java Runtime Environment (JRE) 11 or later
   ```bash
   sudo apt install openjdk-17-jre-headless
   ```
2. Audiveris installation
   ```bash
   git clone https://github.com/Audiveris/audiveris.git
   cd audiveris
   ./gradlew build
   ```

## Integration Steps

### 1. System Setup
- Install Java dependencies
- Build Audiveris from source
- Set up environment variables for Java and Audiveris

### 2. Python Integration
1. Create OMRProcessor class extending current OCR capabilities
2. Use JPype or py4j for Java-Python bridge
3. Implement fallback chain: Audiveris -> Tesseract -> Manual OCR

### 3. Implementation Plan
1. Create `omr_processor.py` for Audiveris integration
2. Extend OCRWrapper to handle OMR
3. Add OMR-specific preprocessing for sheet music
4. Implement result parsing for MusicXML output

### 4. Testing Strategy
1. Use sample music scores from test corpus
2. Validate against ground truth
3. Measure accuracy metrics
4. Performance benchmarking

## Usage Example
```python
from textbook_divider.omr_processor import OMRProcessor

omr = OMRProcessor()
result = omr.process_page("input.pdf", page_num=1)
if result.has_music:
	musicxml = result.to_musicxml()
	midi = result.to_midi()
```

## Dependencies to Add
```
jpype1>=1.4.1
py4j>=0.10.9.7
```