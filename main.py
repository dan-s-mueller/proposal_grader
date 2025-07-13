import argparse
import json
import os
from pathlib import Path
import yaml
import openai
from parser import extract_pdf

import compliance


PROMPT_MAP = {
    "RISK": "prompts/tech_risk.md",
    "MARKET_KNOWLEDGE": "prompts/market_knowledge.md",
}


def load_rubrics() -> list:
    rubrics = []
    for p in Path("rubrics").glob("*.json"):
        with open(p) as f:
            rubrics.append(json.load(f))
    return rubrics


def render_prompt(template_path: str, **kwargs) -> str:
    with open(template_path) as f:
        template = f.read()
    return template.format(**kwargs)


def llm_score(prompt: str) -> float:
    resp = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
    try:
        data = json.loads(resp.choices[0].message.content)
        return float(data.get("score", 0)), data.get("evidence", [])
    except Exception:
        return 0.0, []


def grade(bundle: Path, openai_key: str) -> dict:
    openai.api_key = openai_key
    rubrics = load_rubrics()
    config = yaml.safe_load(open("config/2025.yaml"))
    compliance.check(bundle, config)

    text, _ = extract_pdf(str(bundle / "tech_proposal.pdf"))

    results = {"dimensions": {}}

    for rub in rubrics:
        for dim in rub["dimensions"]:
            code = dim["code"]
            if code not in PROMPT_MAP:
                continue
            prompt = render_prompt(PROMPT_MAP[code], weight=dim["weight"], guideline_text="", section_text=text[:2000])
            score, evidence = llm_score(prompt)
            weighted = score * dim["weight"] * rub["weight"] * 5
            results["dimensions"][code] = {"score": score, "weight": dim["weight"], "evidence": evidence, "weighted": weighted}
    results["overall"] = sum(v["weighted"] for v in results["dimensions"].values())
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--openai_key", required=False, default=os.getenv("OPENAI_API_KEY"))
    args = parser.parse_args()

    bundle = Path(args.bundle)
    res = grade(bundle, args.openai_key)
    out = bundle / "results.json"
    with open(out, "w") as f:
        json.dump(res, f, indent=2)
    print(f"Grades saved to {out}")
    print(f"Overall Phase I score: {res['overall']:.1f}")


if __name__ == "__main__":
    main()
