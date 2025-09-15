# Developer Iteration Loop

This document captures a fast, repeatable workflow for tuning OCR and chapter detection, with minimal manual effort.

## Presets

Place small JSON presets under `configs/` with the input path, output directory, and tuning knobs. Example: `configs/example_preset.json`.

## One-command run

Use the dev harness to run a preset and capture a manifest:

- VS Code: Run task "Run preset (example)"
- Or CLI: `python scripts/dev_run.py configs/example_preset.json`

Artifacts are written under `output_dir/<run_id>/` with a `manifest.json` containing the command, elapsed time, and output.

## Diffing outputs

Compare two run directories to see chapter/text changes:

- VS Code Task: "Diff last two runs (manual)"
- CLI: `python scripts/diff_outputs.py <dir_a> <dir_b>`

Outputs a JSON summary of added/removed/changed chapter files and similarity scores.

## Tuning knobs (CLI)

- `--min-confidence`: float, minimum confidence threshold
- `--disable-title-line`: disables heuristic title-line matching
- `--header-months`: comma-separated override for month tokens in headers
- `--header-keywords`: comma-separated override for other header keywords

These are plumbed into the `ChapterDetector` and can be set in presets.

## Suggested tight loop

1. Run fast unit/golden tests (to be added in `tests/`)
2. Run a small preset slice (e.g., 5 pages) via dev harness
3. Inspect diff vs last run
4. Iterate heuristic or parameter
5. When satisfied, run the full chunk preset

## Caching

OCR caching and paragraph stitching are built into the pipeline. For rapid iteration on detection only, consider caching page-level text outputs for reuse.

## CI

As we add tests, wire them into CI to prevent regressions.
