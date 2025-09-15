OCR Benchmarking

This harness runs multiple OCR presets and collects key metrics into a CSV for easy comparison.

Presets
- configs/ocr_dev.json — completeness-first, auto-tune ON, reprocess_logic=or
- configs/ocr_dev_speed.json — balanced speed, reprocess_logic=and, relaxed thresholds
- configs/ocr_dev_speed_max.json — maximum throughput, reprocess disabled

How to run
- From VS Code: Run task "OCR benchmark (3 presets)"
- Or via terminal:

```
python scripts/ocr_benchmark.py configs/ocr_dev.json configs/ocr_dev_speed.json configs/ocr_dev_speed_max.json
```

Outputs
- CSV at `data/output/benchmarks/ocr_bench_<timestamp>.csv`
- Console summary of pages, throughput, reprocessed pages, logic, and text lengths

Notes
- Speed-max is for bounding throughput; it will reduce text length significantly.
- For faster runs, adjust `page_range` or `raster_scale` in presets.
- For other documents, tweak thresholds or keep auto-tune enabled.