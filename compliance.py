import json
from pathlib import Path
from typing import Dict

from parser import extract_pdf, extract_budget_xlsx


class ComplianceError(Exception):
    pass


def check(bundle: Path, config: Dict[str, int]) -> float:
    tech_pdf = bundle / "tech_proposal.pdf"
    budget_xlsx = bundle / "budget.xlsx"
    text, meta = extract_pdf(str(tech_pdf))
    budget = extract_budget_xlsx(str(budget_xlsx))

    if meta["page_count"] > config.get("proposal_page_limit", 15):
        raise ComplianceError("Too many pages")

    if budget["total"] > config.get("max_budget", 150000):
        raise ComplianceError("Budget exceeds limit")

    # Simple subcontract ratio check
    if budget["subcontract_total"] and budget["total"]:
        ratio = budget["subcontract_total"] / budget["total"]
        if ratio > 0.33:
            raise ComplianceError("Subcontract ratio too high")

    return 1.0
