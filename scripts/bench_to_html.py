import sys
from pathlib import Path
import csv

TEMPLATE = """<html><head><meta charset='utf-8'><title>OCR Bench</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;margin:20px}} table{{border-collapse:collapse}} th,td{{border:1px solid #ccc;padding:6px 10px}} th{{background:#f4f4f4}} .num{{text-align:right}} .ok{{color:#0a0}} .warn{{color:#a60}} .bad{{color:#a00}}</style>
</head><body>
<h2>OCR Benchmark Results</h2>
<p>File: {csv_name}</p>
<table>
<thead><tr>{headers}</tr></thead>
<tbody>
{rows}
</tbody>
</table>
</body></html>"""

COLUMNS = [
    ("preset", str),
    ("pages", int),
    ("throughput", float),
    ("avg_page_s", float),
    ("med_page_s", float),
    ("p90_page_s", float),
    ("reprocessed", int),
    ("reprocess_logic", str),
    ("reprocess_conf", float),
    ("reprocess_chars", float),
    ("text_clean", int),
    ("text_raw", int),
    ("process_pool", str),
    ("auto_tuned", str),
    ("rasterizer", str),
]

def fmt(val):
    if isinstance(val, float):
        return f"{val:.2f}"
    return str(val)

def to_html_table(csv_path: Path) -> str:
    with open(csv_path, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        headers_html = ''.join(f"<th>{h}</th>" for h,_ in COLUMNS)
        rows_html = []
        for row in r:
            tds = []
            for key, _ in COLUMNS:
                tds.append(f"<td class='num'>{fmt(row.get(key, ''))}</td>")
            rows_html.append('<tr>' + ''.join(tds) + '</tr>')
        return TEMPLATE.format(csv_name=csv_path.name, headers=headers_html, rows='\n'.join(rows_html))

def main():
    if len(sys.argv) < 2:
        # pick the newest bench CSV
        bench_dir = Path('data/output/benchmarks')
        csvs = sorted(bench_dir.glob('ocr_bench_*.csv'))
        if not csvs:
            print('No benchmark CSVs found.')
            return 2
        csv_path = csvs[-1]
    else:
        csv_path = Path(sys.argv[1])
    html = to_html_table(csv_path)
    out_path = csv_path.with_suffix('.html')
    out_path.write_text(html, encoding='utf-8')
    print(f"Wrote HTML report: {out_path}")
    return 0

if __name__ == '__main__':
    sys.exit(main())
