import json
import sys
import subprocess
import time
from pathlib import Path
import csv

"""
Run multiple OCR presets and collect key metrics into a CSV for comparison.
Usage:
  python scripts/ocr_benchmark.py configs/ocr_dev.json configs/ocr_dev_speed.json configs/ocr_dev_speed_max.json
Outputs a CSV in data/output/benchmarks/ with timestamped filename.
"""

def run_preset(preset_path: Path):
    preset = json.loads(preset_path.read_text(encoding="utf-8"))
    t0 = time.time()
    proc = subprocess.run([
        sys.executable, "scripts/ocr_dev_loop.py", str(preset_path)
    ], capture_output=True, text=True)
    elapsed = time.time() - t0
    # Load manifest and metadata from the last run dir
    out_root = Path(preset["output_dir"]).resolve()
    dirs = [p for p in out_root.iterdir() if p.is_dir()]
    if not dirs:
        return {
            "preset": preset_path.name,
            "elapsed_sec": elapsed,
            "rc": proc.returncode,
            "pages": 0,
            "throughput": 0.0,
            "reprocessed": 0,
            "reprocess_conf": None,
            "reprocess_chars": None,
            "reprocess_logic": None,
            "text_clean": 0,
            "text_raw": 0,
            "process_pool": False,
            "auto_tuned": False,
        }
    dirs.sort(key=lambda p: p.name)
    last = dirs[-1]
    meta = None
    for p in last.glob("*_metadata.json"):
        meta = json.loads(p.read_text(encoding="utf-8"))
        break
    pages = 0
    throughput = 0.0
    reproc = 0
    conf_thr = None
    chars_thr = None
    logic = None
    text_clean = 0
    text_raw = 0
    process_pool = False
    auto_tuned = False
    if meta:
        ps = meta.get("processing_stats", {})
        fh = ps.get("file_handler", {})
        pages = fh.get("pages", 0)
        total_ocr = fh.get("total_ocr_sec", 0.0)
        throughput = (pages / total_ocr) if total_ocr > 0 else 0.0
        reproc = fh.get("reprocessed_pages", 0)
        conf_thr = fh.get("reprocess_threshold_conf")
        chars_thr = fh.get("reprocess_threshold_chars")
        logic = fh.get("reprocess_logic")
        text_clean = ps.get("text_length", 0)
        text_raw = ps.get("raw_text_length", 0)
        process_pool = fh.get("process_pool", False)
        auto_tuned = fh.get("auto_tuned", False)
        # Extras
        per = fh.get("per_page_secs", []) or []
        rasterizer = fh.get("rasterizer", "")
    else:
        per = []
        rasterizer = ""
    # Percentiles
    if per:
        per_sorted = sorted(per)
        avg = sum(per_sorted)/len(per_sorted)
        med = per_sorted[len(per_sorted)//2]
        p90 = per_sorted[int(0.9*len(per_sorted))-1] if len(per_sorted) >= 10 else per_sorted[-1]
    else:
        avg = med = p90 = 0.0
    return {
        "preset": preset_path.name,
        "elapsed_sec": elapsed,
        "rc": proc.returncode,
        "pages": pages,
        "throughput": throughput,
        "reprocessed": reproc,
        "reprocess_conf": conf_thr,
        "reprocess_chars": chars_thr,
        "reprocess_logic": logic,
        "text_clean": text_clean,
        "text_raw": text_raw,
        "process_pool": process_pool,
        "auto_tuned": auto_tuned,
        "avg_page_s": avg,
        "med_page_s": med,
        "p90_page_s": p90,
        "rasterizer": rasterizer,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/ocr_benchmark.py <preset1.json> [preset2.json ...]")
        return 2
    rows = []
    for arg in sys.argv[1:]:
        rows.append(run_preset(Path(arg)))
    bench_dir = Path("data/output/benchmarks").resolve()
    bench_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    csv_path = bench_dir / f"ocr_bench_{ts}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote benchmark results: {csv_path}")
    for r in rows:
        print(f"{r['preset']}: pages={r['pages']} thr={r['throughput']:.2f} rproc={r['reprocessed']} logic={r['reprocess_logic']} text={r['text_clean']}/{r['text_raw']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
