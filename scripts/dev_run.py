import json
import os
import sys
import time
import hashlib
from pathlib import Path
from datetime import datetime
import subprocess

# Simple dev harness that loads a preset and runs the CLI once, saving a manifest.

def sha_short(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]


def run_from_preset(preset_path: str):
    preset = json.loads(Path(preset_path).read_text(encoding="utf-8"))

    input_file = preset["input_file"]
    output_dir = preset["output_dir"]
    page_range = preset.get("page_range")
    max_pages = preset.get("max_pages", 50)
    force_ocr = preset.get("force_ocr", False)
    ocr_psm = preset.get("ocr_psm", 3)
    raster_scale = preset.get("raster_scale", 2.0)
    enable_omr = preset.get("enable_omr", False)

    min_confidence = preset.get("min_confidence", 0.5)
    disable_title_line = preset.get("disable_title_line", False)
    header_months = preset.get("header_months") or None
    header_keywords = preset.get("header_keywords") or None

    # Create a run-id
    now = datetime.now().strftime("%Y%m%d-%H%M%S")
    preset_key = sha_short(json.dumps(preset, sort_keys=True))
    run_id = f"{now}-{preset_key}"

    out_dir = Path(output_dir) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "textbook_divider.main",
        input_file,
        str(out_dir),
        "--max-pages",
        str(max_pages),
        "--ocr-psm",
        str(ocr_psm),
        "--raster-scale",
        str(raster_scale),
        "--min-confidence",
        str(min_confidence),
    ]

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

    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0

    manifest = {
        "preset": preset,
        "cmd": cmd,
        "elapsed_sec": elapsed,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-4000:],  # tail to keep small
        "stderr": proc.stderr[-4000:],
        "run_id": run_id,
    }

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote manifest to {out_dir / 'manifest.json'}")
    print(f"Elapsed: {elapsed:.2f}s ReturnCode: {proc.returncode}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/dev_run.py <configs/preset.json>")
        sys.exit(2)
    run_from_preset(sys.argv[1])
