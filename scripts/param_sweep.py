import json
import itertools
import subprocess
import sys
import time
from pathlib import Path

"""
Quick param sweep on a short page slice for tuning.

Usage:
  python scripts/param_sweep.py <input_file> <output_root> <page_range>

Writes a simple CSV summary to <output_root>/sweep_results.csv
Each run is isolated into a timestamped subfolder with a manifest.
"""

PARAM_GRID = {
    # Keep chapter detector lenient while focusing on throughput
    "min_confidence": [0.5],
    # Test page segmentation modes known to be fast for dense vs sparse
    "ocr_psm": [6, 11],
    # Raster scales: smaller is faster; verify quality impact later
    "raster_scale": [1.5, 2.0],
    # Parallelism levels to test
    "parallel_workers": [1, 2, 3, 4],
    # Fast preprocess often boosts throughput; include both
    "fast_preprocess": [True, False],
}


def product_dict(d):
    keys = list(d.keys())
    for values in itertools.product(*[d[k] for k in keys]):
        yield dict(zip(keys, values))


def run_once(input_file: str, out_dir: Path, page_range: str, params: dict):
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, "-m", "textbook_divider.main",
        input_file, str(out_dir),
        "--page-range", page_range,
        "--max-pages", "50",
        "--min-confidence", str(params["min_confidence"]),
        "--ocr-psm", str(params["ocr_psm"]),
        "--raster-scale", str(params["raster_scale"]),
        "--force-ocr",
    ]
    if params.get("fast_preprocess", False):
        cmd.append("--fast-preprocess")
    if params.get("parallel_workers", 1) and int(params["parallel_workers"]) > 1:
        cmd += ["--parallel-workers", str(int(params["parallel_workers"]))]
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0
    manifest = {
        "params": params,
        "cmd": cmd,
        "elapsed_sec": elapsed,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return elapsed, proc.returncode


def count_chapters(out_dir: Path) -> int:
    return len(list(out_dir.glob("*.txt")))


def main():
    if len(sys.argv) < 4:
        print("Usage: python scripts/param_sweep.py <input_file> <output_root> <page_range>")
        sys.exit(2)
    input_file = sys.argv[1]
    output_root = Path(sys.argv[2])
    page_range = sys.argv[3]
    output_root.mkdir(parents=True, exist_ok=True)

    rows = ["min_confidence,ocr_psm,raster_scale,parallel_workers,fast_preprocess,elapsed_sec,returncode,chapters,run_dir"]
    idx = 0
    for params in product_dict(PARAM_GRID):
        idx += 1
        run_dir = output_root / (
            f"sweep_{idx:02d}_mc{params['min_confidence']}_psm{params['ocr_psm']}"
            f"_rs{params['raster_scale']}_pw{params['parallel_workers']}_fp{int(params['fast_preprocess'])}"
        )
        elapsed, rc = run_once(input_file, run_dir, page_range, params)
        chapters = count_chapters(run_dir)
        rows.append(
            f"{params['min_confidence']},{params['ocr_psm']},{params['raster_scale']},{params['parallel_workers']},{params['fast_preprocess']},{elapsed:.2f},{rc},{chapters},{run_dir}"
        )
        print(rows[-1])

    (output_root / "sweep_results.csv").write_text("\n".join(rows), encoding="utf-8")
    print(f"Wrote {output_root / 'sweep_results.csv'}")


if __name__ == "__main__":
    main()
