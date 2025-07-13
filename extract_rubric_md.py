import argparse
import re
from pathlib import Path

from pdfminer.high_level import extract_text

# Known dimension codes and headings for simple extraction
TECH_KEYS = [
    "BENEFITS",
    "SOTA",
    "RISK",
    "PLAN",
    "TEAM",
    "WRITE",
]
COMM_KEYS = [
    "MARKET KNOWLEDGE",
    "CUSTOMER",
    "VALUE",
    "COMPETITION",
    "TRANSITION",
    "WRITE",
]


def normalize(code: str) -> str:
    return code.upper().replace(" ", "_")


def parse_table(text: str, keywords: list) -> list:
    dims = []
    for key in keywords:
        pattern = re.compile(rf"{re.escape(key)}\s+(\d+)\s*%", re.IGNORECASE)
        m = pattern.search(text)
        if m:
            weight = int(m.group(1)) / 100.0
            dims.append((normalize(key), weight))
    return dims


def extract_rubrics(pdf: Path) -> tuple:
    text = extract_text(str(pdf))

    # naive: assume technical section precedes commercial
    tech_dims = parse_table(text, TECH_KEYS)
    comm_dims = parse_table(text, COMM_KEYS)
    return tech_dims, comm_dims


def write_markdown(out: Path, tech: list, comm: list, tech_weight: float, comm_weight: float) -> None:
    lines = ["# Combined Rubric", ""]
    lines.append("| Code | Source | Dim Weight | Overall Weight |")
    lines.append("| ---- | ------ | ---------- | -------------- |")

    for code, w in tech:
        lines.append(f"| {code} | Technical | {w:.2f} | {w * tech_weight:.2f} |")
    for code, w in comm:
        lines.append(f"| {code} | Commercial | {w:.2f} | {w * comm_weight:.2f} |")

    out.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract rubric to markdown")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--tech_weight", type=float, default=0.70)
    parser.add_argument("--comm_weight", type=float, default=0.30)
    args = parser.parse_args()

    tech, comm = extract_rubrics(args.pdf)
    write_markdown(args.output, tech, comm, args.tech_weight, args.comm_weight)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
