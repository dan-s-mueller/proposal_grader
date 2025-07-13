import argparse
import json
import re
from pathlib import Path
from pdfminer.high_level import extract_text


def parse_rubric(text: str):
    pattern = re.compile(r"([A-Za-z\-/ ]+)\s+(\d+)\s*%")
    dims = []
    for line in text.splitlines():
        m = pattern.search(line)
        if m:
            code = m.group(1).strip().replace(' ', '_').replace('-', '_').upper()
            weight = int(m.group(2)) / 100.0
            dims.append({"code": code, "weight": weight})
    return dims


def extract_rubric(pdf_path: Path, rubric_id: str, weight: float) -> dict:
    text = extract_text(str(pdf_path))
    dimensions = parse_rubric(text)
    return {"rubric_id": rubric_id, "weight": weight, "dimensions": dimensions}


def main():
    parser = argparse.ArgumentParser(description="Extract rubric table from PDF")
    parser.add_argument("pdf")
    parser.add_argument("rubric_id")
    parser.add_argument("weight", type=float)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    rubric = extract_rubric(Path(args.pdf), args.rubric_id, args.weight)
    with open(args.output, "w") as f:
        json.dump(rubric, f, indent=2)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
