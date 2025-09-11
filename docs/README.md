# Textbook Divider Documentation

## Overview
The Textbook Divider is a sophisticated document processing system that converts various text-based book formats (TXT, PDF, EPUB) into organized, chapter-separated files with enhanced OCR, OMR (Optical Music Recognition), and mathematical notation processing capabilities.

## Quick Start
- **System Requirements**: See [SRS.md](SRS.md)
- **Project Status**: See [PROJECT_STATUS.md](PROJECT_STATUS.md) for current capabilities and roadmap
- **Testing Guide**: See [TESTING_GUIDE.md](TESTING_GUIDE.md) for comprehensive testing information

## Core Documentation

### System Architecture & Requirements
- **[System Requirements Specification (SRS)](SRS.md)** - Complete technical specifications, functional requirements, and architecture overview
- **[Project Status & Roadmap](PROJECT_STATUS.md)** - Current achievements, performance metrics, and development roadmap

### Development Guidelines
- **[Development Plans](development/)** - Feature-specific development documentation
  - [OCR Enhancement Plan](development/OCR_IMPROVEMENT_PLAN.md) - OCR optimization strategies and implementation
  - [Diagram Detection Plan](development/DIAGRAM_DETECTION_PLAN.md) - Mathematical and musical diagram processing

### Testing & Quality Assurance
- **[Testing Guide](TESTING_GUIDE.md)** - Comprehensive testing strategy, implementation guidelines, and quality metrics
- **[Audiveris Integration](AUDIVERIS_INTEGRATION.md)** - OMR system integration documentation

## Current Capabilities

### Processing Performance
- **OCR Speed**: 6.73s/page (4x improvement from baseline)
- **Success Rate**: 99.2% for complex textbooks (tested on Schoenberg's Fundamentals)
- **Musical Notation**: 95% staff detection accuracy, 92% note recognition
- **Memory Usage**: Stable under 1GB for large documents

### Supported Content Types
- **Text Processing**: Multi-column layouts, mathematical formulas, footnotes
- **Musical Notation**: Staff detection, symbol recognition, mixed content
- **Graph Analysis**: Transformation networks, mathematical diagrams, isomorphism detection
- **File Formats**: PDF (text and scanned), TXT, EPUB

### Real-World Testing
- ✅ **Schoenberg's Fundamentals of Musical Composition** (125 pages, 99.2% success)
- 🔄 **Lewin's Generalized Musical Intervals** (43/300+ pages tested, 100% success)
- 📋 **Tymoczko's Geometry of Music** (planned)
- 📋 **Lerdahl's Tonal Pitch Space** (planned)

## Project Structure
```
/src/                   # Core C++ implementation
/src/textbook_divider/  # Python implementation
/graph_extractor/       # Mathematical diagram analysis
/tests/                 # Comprehensive test suite
/docs/                  # Documentation
/data/                  # Input/output data
```

## Getting Help
- Check the [Testing Guide](TESTING_GUIDE.md) for troubleshooting
- Review [Project Status](PROJECT_STATUS.md) for known issues and limitations
- See individual development plans for feature-specific information

## Windows Quick Start (build & launch)

A convenience PowerShell script `build_and_launch.ps1` is provided to prepare a Python venv, install Python dependencies, build the C++ GUI, check required external tools, and launch a GUI backend.

Usage (from repository root in PowerShell):

```powershell
# Build and launch the C++ GUI (default)
.\build_and_launch.ps1 -Backend cpp

# Prepare venv and launch the Python Tk GUI
.\build_and_launch.ps1 -Backend py

# Skip the C++ build step and just run the Python GUI
#.\build_and_launch.ps1 -Backend py -SkipBuild
```

Prerequisites for Windows:

- Python 3.8+ on PATH (used to create `./venv`)
- CMake and a C++ toolchain (Visual Studio / MSVC) for building the C++ GUI
- Poppler (for `pdftoppm`) added to PATH if you intend to process scanned PDFs via the C++ pipeline
- Tesseract OCR added to PATH for OCR (used by the Python pipeline)

If `pdftoppm` or `tesseract` are missing the script will warn and the C++ GUI will show a friendly error modal explaining the missing dependency.