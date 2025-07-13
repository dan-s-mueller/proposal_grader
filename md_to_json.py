import argparse
import json
import re
from pathlib import Path


def parse_md(md_path: Path):
    text = md_path.read_text()
    rows = []
    for line in text.splitlines():
        m = re.match(r"\|\s*(\w+)\s*\|\s*(\w+)\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|", line)
        if m:
            code = m.group(1)
            src = m.group(2)
            dim_w = float(m.group(3))
            overall = float(m.group(4))
            rows.append({"code": code, "source": src, "dim_weight": dim_w, "weight": overall})
    return rows


def main():
    parser = argparse.ArgumentParser(description="Convert rubric markdown to JSON")
    parser.add_argument("markdown", type=Path)
    parser.add_argument("rubric_id")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    dims = parse_md(args.markdown)
    rubric = {"rubric_id": args.rubric_id, "dimensions": dims}
    args.output.write_text(json.dumps(rubric, indent=2))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
