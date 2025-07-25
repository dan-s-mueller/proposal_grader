# Proposal Development User’s Manual (Detailed)

This manual provides complete, step‑by‑step guidance—from brainstorm to final SBIR package—and highlights **every** task that requires manual input or reviewer action. Whenever you adjust tasks or the Excel workbook, rerun the scripts to keep budget and scores aligned.

---

## 1. Prepare Your Brain Dump

1. **Gather your notes.** Compile all notes, ideas, journal entries and rough thoughts about the proposal topic. Set aside at least five minutes to capture whatever comes to mind without editing or organising.
2. **Perform a general dump.** Write down any words, phrases or sentences that occur to you about your proposal. Don’t worry about spelling or order.
3. **Highlight key themes.** Circle or highlight phrases that seem central to your project. For each highlighted term, perform a detail dump to explore related ideas.
4. **Group similar ideas.** After your general and detail dumps, group related concepts together and note any missing components.
5. **Generate outline.** Run:
   ```bash
   python scripts/run_brain_dump.py --idea idea.txt
   ```
   This creates `outline.md` organised into logical sections (introduction, objectives, methodology, team, commercialisation) and flags gaps.

---

## 2. Ingest the Solicitation and Set Evaluation Criteria

1. **Obtain the solicitation.** Download the funding opportunity PDF.
2. **Extract criteria.**
   ```bash
   python -m core.loader --ingest-solicitation solicitation.pdf
   ```
   This outputs `criteria.json` listing evaluation bullets (e.g. innovation, technical merit, team qualifications, commercial potential).
3. **Customise prompts.**
   ```bash
   python -m core.reviewers customise_role_prompts --criteria criteria.json
   ```
   This tailors the detail reviewer and panel questions so they map directly to the solicitation.

---

## 3. Assign T‑Shirt Sizes and Estimate Budget

1. **List tasks.** Break down your project into discrete tasks (one‑person chunks).
2. **Assign sizes.** For each task choose XS (4 h), S (8 h), M (24 h), L (56 h), XL (120 h). Agree on what each size means and keep the mapping in the Hours Mapping table.
3. **Define mapping.** Adjust hours if your team differs.
4. **Estimate costs.**
   ```bash
   python -m core.budget_engine push sheets/Task_Estimation.xlsx \
          --hourly-rate 150 --overhead 0.30 --buffer 0.15
   ```
   The script applies overhead (indirect) and buffer (schedule slack).
5. **Review and adjust.** If `TOTAL_COST` in Excel exceeds the Phase I cap, reduce task sizes or scope.

---

## 4. Draft the Proposal and Run the Multi‑Role Review

1. **Prepare draft.** Align each section with evaluation criteria. Export to `draft_v1.pdf`.
2. **Select roles.**
   - Technical reviewer
   - Business strategist
   - Detail reviewer
   - Panel reviewer
   - Storytelling reviewer (optional)
3. **Run review.**
   ```bash
   python scripts/run_iterative_review.py \
          --proposal draft_v1.pdf \
          --criteria criteria.json \
          --xls sheets/Task_Estimation.xlsx \
          --roles technical,business,detail,panel,storytelling
   ```
   **Outputs**
   - `feedback/<role>.md` – role comments
   - `scorecard.json` – ratings (High = 3, Medium = 2, Low = 1)
   - Updated Excel tabs (**Actual Hours**, **Burn‑down**)
4. **Interpret feedback.** Address criteria with Low ratings first.
5. **Iterate.** Revise the draft or budget and rerun until targets are met.

---

## 5. Manage Reviewer Actions

### Reviewer Checklist

| Role         | Responsibilities                                               |
| ------------ | -------------------------------------------------------------- |
| Technical    | Confirm feasibility, correct equations, realistic TRL progress |
| Business     | Validate market size, pricing, IP strategy, ROI timeline       |
| Detail       | Cross‑check every solicitation bullet, formatting, page limits |
| Panel        | Score each criterion H/M/L, justify ratings                    |
| Storytelling | Ensure clear narrative (problem → solution → benefit)          |

### Proposal Owner Checklist

- Provide reviewers with **solicitation PDF**, latest draft and criteria.
- Collect markdown feedback files.
- Consolidate comments into an action list and update draft.
- Track version history, score improvements and budget deltas.

---

## 6. Iteration Targets

- Weighted score ≥ 2.3.
- Total cost ≤ \$150 000.
- Reserve ≥ 15 % (shown in Burn‑down chart).
- All criteria Medium or better.

---

## 7. Export Final Package

1. Generate SBIR budget form:
   ```bash
   python scripts/export_sbir_form.py --xls sheets/Task_Estimation.xlsx --out budget_form.xlsx
   ```
2. Finalise `proposal_final.pdf`.
3. Collect letters of support and any certifications.
4. Upload to Valid Eval.

---

## 8. Troubleshooting

| Issue             | Likely Cause                       | Fix                             |
| ----------------- | ---------------------------------- | ------------------------------- |
| Named range error | Range missing in Excel             | Excel → Formulas → Name Manager |
| LLM quota error   | Missing key or exhausted quota     | Check `OPENAI_API_KEY`, billing |
| PDF extract empty | Encrypted PDF                      | `qpdf --decrypt file.pdf`       |
| Budget over cap   | Too many L/XL tasks, high overhead | Adjust scope or rates           |

---

## 9. Spreadsheet Behaviour and Fixed Variables

- **Auto‑calculation.** Scripts write values to named ranges. Excel recalculates pivot tables and formulas when the workbook is opened or when you press **Data ▷ Refresh All**.
- **Immutable ranges.** Any cell/range whose name begins with `` is treated as read‑only by scripts. Place overhead %, fringe %, G&A etc. there and adjust manually.

---

## 10. Monitoring the Workflow

- **CLI banners.** Every major step prints a banner (`[budget_engine]`, `[reviewers]`, `[scorer]`).
- **Verbose mode.** Add `-v` to any script for raw JSON payloads, list of updated ranges and full LLM responses.
- **Run log.** Each iteration writes `runs/<timestamp>.log` capturing Excel writes, OpenAI calls, scores and budget deltas.

---

## 11. Package Assembly (Attachments, Letters, Quotes)

1. Place supplemental docs in ``:
   - `assets/budget_form.xlsx` – generated budget sheet
   - `assets/letters/…` – PDFs of letters of support
   - `assets/contracts/…` – contractor quotes or subaward budgets
2. Create a manifest:
   ```bash
   python scripts/export_sbir_form.py --xls sheets/Task_Estimation.xlsx \
          --out assets/budget_form.xlsx --manifest assets/manifest.json
   ```
3. Package submission:
   ```bash
   python scripts/package_submission.py --manifest assets/manifest.json
   ```
   Outputs `submission.zip` ready for Valid Eval.

---

## 12. Optional Add‑Ons to Consider

| Gap                             | Action                                                                          |
| ------------------------------- | ------------------------------------------------------------------------------- |
| Risk & Mitigation matrix        | Add `risks.csv`; detail reviewer verifies each risk has mitigation and TRL path |
| Schedule Gantt                  | Auto‑generate PNG from task dates and embed in draft                            |
| ITAR / non‑US disclosure        | Detail reviewer checklist item                                                  |
| Data management plan            | Storytelling reviewer ensures appendix exists                                   |
| Compliance forms (SF‑LLL, etc.) | Store in `assets/forms/` and include in manifest                                |

---