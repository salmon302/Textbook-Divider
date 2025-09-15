import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime
import subprocess

"""
OCR development loop:
 - Reads a preset JSON (like configs/ocr_dev.json)
 - Runs textbook_divider.main with those args into a timestamped run folder
 - Persists a compact manifest
 - Automatically diffs against the previous run in the same output root

Usage:
  python scripts/ocr_dev_loop.py configs/ocr_dev.json
"""


def run_once(preset_path: str) -> Path:
    preset = json.loads(Path(preset_path).read_text(encoding="utf-8"))
    input_file = preset["input_file"]
    output_dir = preset["output_dir"]
    page_range = preset.get("page_range")
    max_pages = str(preset.get("max_pages", 50))
    force_ocr = bool(preset.get("force_ocr", True))
    ocr_psm = str(preset.get("ocr_psm", 6))
    raster_scale = str(preset.get("raster_scale", 2.5))
    fast_pre = bool(preset.get("fast_preprocess", False))
    parallel_workers = int(preset.get("parallel_workers", 1))
    enable_omr = bool(preset.get("enable_omr", False))
    min_conf = str(preset.get("min_confidence", 0.5))
    reprocess_below_conf = str(preset.get("reprocess_below_conf", 55.0))
    min_chars_reprocess = str(preset.get("min_chars_reprocess", 200))
    ocr_word_conf_threshold = str(preset.get("ocr_word_conf_threshold", 30))
    process_pool = bool(preset.get("process_pool", False))
    auto_tune = bool(preset.get("auto_tune", False))
    reprocess_logic = preset.get("reprocess_logic")
    disable_title_line = bool(preset.get("disable_title_line", False))
    header_months = preset.get("header_months") or ""
    header_keywords = preset.get("header_keywords") or ""

    # Timestamped run dir
    run_root = Path(output_dir)
    run_root.mkdir(parents=True, exist_ok=True)
    run_dir = run_root / datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "textbook_divider.main",
        input_file, str(run_dir),
        "--max-pages", max_pages,
        "--ocr-psm", ocr_psm,
        "--raster-scale", raster_scale,
        "--min-confidence", min_conf,
        "--reprocess-below-conf", reprocess_below_conf,
        "--min-chars-reprocess", min_chars_reprocess,
        "--ocr-word-conf-threshold", ocr_word_conf_threshold,
    ]
    if process_pool:
        cmd.append("--process-pool")
    if auto_tune:
        cmd.append("--auto-tune")
    if reprocess_logic:
        cmd += ["--reprocess-logic", str(reprocess_logic)]
    if force_ocr:
        cmd.append("--force-ocr")
    if enable_omr:
        cmd.append("--enable-omr")
    if disable_title_line:
        cmd.append("--disable-title-line")
    if header_months:
        cmd += ["--header-months", header_months]
    if header_keywords:
        cmd += ["--header-keywords", header_keywords]
    if page_range:
        cmd += ["--page-range", page_range]
    if fast_pre:
        cmd.append("--fast-preprocess")
    if parallel_workers and parallel_workers > 1:
        cmd += ["--parallel-workers", str(parallel_workers)]

    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0
    manifest = {
        "preset": preset,
        "cmd": cmd,
        "elapsed_sec": elapsed,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
        "run_dir": str(run_dir),
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Run complete in {elapsed:.2f}s with rc={proc.returncode}")
    return run_dir


def latest_two_dirs(root: Path):
    dirs = [p for p in root.iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: p.name)
    return dirs[-2:] if len(dirs) >= 2 else []


def diff_last_two(root: Path):
    pair = latest_two_dirs(root)
    if len(pair) < 2:
        print("Not enough runs to diff yet.")
        return 0
    a, b = pair[-2], pair[-1]
    print(f"Diffing:\n A: {a}\n B: {b}")
    proc = subprocess.run([
        sys.executable, "scripts/diff_outputs.py", str(a), str(b)
    ], capture_output=True, text=True)
    if proc.returncode == 0:
        # Print summary
        print(proc.stdout)
        return 0
    else:
        print(proc.stderr)
        return proc.returncode


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/ocr_dev_loop.py <configs/ocr_dev.json>")
        return 2
    preset = sys.argv[1]
    run_dir = run_once(preset)
    # Print performance summary from metadata if present
    try:
        meta_path = next(run_dir.glob("*_metadata.json"), None)
        if meta_path and meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            ps = meta.get("processing_stats", {})
            fh = ps.get("file_handler", {})
            pages = fh.get("pages", 0)
            total_ocr = fh.get("total_ocr_sec", 0.0)
            per = fh.get("per_page_secs", []) or []
            rasterizer = fh.get("rasterizer", "")
            reproc_pages = fh.get("reprocessed_pages", 0)
            reproc_thr_conf = fh.get("reprocess_threshold_conf", None)
            reproc_thr_chars = fh.get("reprocess_threshold_chars", None)
            reproc_logic = fh.get("reprocess_logic", "or").upper()
            text_len = ps.get("text_length", 0)
            raw_text_len = ps.get("raw_text_length", None)
            chapters = meta.get("chapters", 0)
            process_pool_flag = fh.get("process_pool", False)
            auto_tuned = fh.get("auto_tuned", False)
            tuned_conf = fh.get("tuned_conf")
            tuned_min_chars = fh.get("tuned_min_chars")
            if per:
                per_sorted = sorted(per)
                avg = sum(per_sorted) / len(per_sorted)
                med = per_sorted[len(per_sorted)//2]
                p90 = per_sorted[int(0.9*len(per_sorted))-1] if len(per_sorted) >= 10 else per_sorted[-1]
                throughput = (pages / total_ocr) if total_ocr > 0 else 0.0
            else:
                avg = med = p90 = throughput = 0.0
            print("=== Performance Summary ===")
            print(f"Pages: {pages} | Total OCR: {total_ocr:.2f}s | Avg/Med/P90 per-page: {avg:.2f}/{med:.2f}/{p90:.2f}s | Thruput: {throughput:.2f} pages/s | Rasterizer: {rasterizer}")
            if reproc_thr_conf is not None and reproc_thr_chars is not None:
                print(f"Reprocessed pages: {reproc_pages} (conf<{reproc_thr_conf} {reproc_logic} chars<{reproc_thr_chars})")
            if raw_text_len is not None:
                print(f"Text length: {text_len} (clean) / {raw_text_len} (raw) chars | Chapters: {chapters}")
            else:
                print(f"Text length: {text_len} chars | Chapters: {chapters}")
            print(f"Process pool: {process_pool_flag} | Auto-tuned: {auto_tuned}"
                  + (f" (conf={tuned_conf}, min_chars={tuned_min_chars})" if auto_tuned else ""))
    except Exception as e:
        print(f"Perf summary unavailable: {e}")
    root = Path(json.loads(Path(preset).read_text(encoding="utf-8"))["output_dir"]).resolve()
    # Auto-diff last two
    return diff_last_two(root)


if __name__ == "__main__":
    sys.exit(main())
