#!/usr/bin/env python3
import argparse
import glob
import os
import re
from datetime import datetime


def find_latest_dated_file(directory: str) -> str | None:
    pattern = os.path.join(directory, "healthtech-tools-*.md")
    candidates = glob.glob(pattern)
    if not candidates:
        return None
    rx = re.compile(r"healthtech-tools-(\d{4}-\d{2}-\d{2})\.md$")
    dated = []
    for p in candidates:
        m = rx.search(os.path.basename(p))
        if not m:
            continue
        try:
            dt = datetime.strptime(m.group(1), "%Y-%m-%d")
        except ValueError:
            continue
        dated.append((dt, p))
    if not dated:
        return None
    dated.sort(key=lambda x: x[0])
    return dated[-1][1]


essage = """
Aggregate the most recent dated markdown into the latest file.
By default, writes result/healthtech-tools.md from the newest result/healthtech-tools-YYYY-MM-DD.md.
"""

def main():
    ap = argparse.ArgumentParser(description="Aggregate latest dated results into latest index")
    ap.add_argument("--dir", default="result", help="Directory containing dated result files")
    ap.add_argument("--output", default=None, help="Path to write the latest index (default: <dir>/healthtech-tools.md)")
    args = ap.parse_args()

    target_dir = args.dir
    output_path = args.output or os.path.join(target_dir, "healthtech-tools.md")

    os.makedirs(target_dir, exist_ok=True)

    latest_file = find_latest_dated_file(target_dir)
    if not latest_file:
        # nothing to aggregate; create an empty stub
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# Curated Healthcare Technology Tools\n\n")
        print(f"No dated files found in {target_dir}. Wrote empty stub to {output_path}")
        return

    with open(latest_file, "r", encoding="utf-8") as src:
        content = src.read()
    with open(output_path, "w", encoding="utf-8") as dst:
        dst.write(content)
    print(f"Aggregated {os.path.basename(latest_file)} -> {output_path}")


if __name__ == "__main__":
    main()
