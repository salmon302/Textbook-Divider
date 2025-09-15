import sys
from pathlib import Path
import difflib
import json

# Compare two output directories and summarize changes in chapter files

def list_chapter_files(dir_path: Path):
    return sorted([p for p in dir_path.glob("**/*.txt") if p.is_file()])


def text_similarity(a: str, b: str) -> float:
    sm = difflib.SequenceMatcher(None, a, b)
    return sm.ratio()


def compare_dirs(dir_a: str, dir_b: str):
    A = Path(dir_a)
    B = Path(dir_b)
    files_a = {p.name: p for p in list_chapter_files(A)}
    files_b = {p.name: p for p in list_chapter_files(B)}

    added = sorted(set(files_b) - set(files_a))
    removed = sorted(set(files_a) - set(files_b))
    common = sorted(set(files_a) & set(files_b))

    changed = []
    for name in common:
        ta = files_a[name].read_text(encoding="utf-8", errors="ignore")
        tb = files_b[name].read_text(encoding="utf-8", errors="ignore")
        if ta != tb:
            changed.append({
                "file": name,
                "similarity": round(text_similarity(ta, tb), 4),
                "a_path": str(files_a[name]),
                "b_path": str(files_b[name])
            })

    summary = {
        "dir_a": str(A),
        "dir_b": str(B),
        "added": added,
        "removed": removed,
        "changed_top": sorted(changed, key=lambda x: x["similarity"])[:10]
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/diff_outputs.py <dir_a> <dir_b>")
        sys.exit(2)
    compare_dirs(sys.argv[1], sys.argv[2])
