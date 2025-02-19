# Test Output Directory Structure

## Organization
Each textbook has its own directory with the following structure:

```
output/
├── schoenberg_fundamentals/
│   ├── chapters/         # Extracted chapters
│   ├── music_notation/   # Extracted musical examples
│   ├── metrics/          # Performance and accuracy metrics
│   └── errors/          # Error logs and problematic sections
├── lewin_intervals/
│   ├── chapters/
│   ├── music_notation/
│   ├── metrics/
│   └── errors/
├── tymoczko_geometry/
│   ├── chapters/
│   ├── music_notation/
│   ├── metrics/
│   └── errors/
└── lerdahl_pitch_space/
	├── chapters/
	├── music_notation/
	├── metrics/
	└── errors/
```

## Directory Purposes
- chapters/: Contains extracted chapter text and structure
- music_notation/: Stores identified musical notation in MusicXML format
- metrics/: Performance data, processing times, and accuracy metrics
- errors/: Error logs and problematic sections requiring review