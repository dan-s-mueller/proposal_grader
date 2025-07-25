# Proposal Development User’s Manual
This manual provides step‑by‑step guidance for using the iterative proposal workflow
and highlights tasks that require manual input or reviewer action. The process
supports the entire lifecycle of proposal creation, from brainstorming through
evaluation and budgeting.

## 1. Prepare Your Brain Dump
1. **Gather your notes.** Compile all notes, ideas, journal entries and rough thoughts about the proposal topic. Set aside at least five minutes to capture whatever comes to mind without editing or organising.
2. **Perform a general dump.** Write down any words, phrases or sentences that occur to you about your proposal. Don’t worry about spelling or order.
3. **Highlight key themes.** Circle or highlight phrases that seem central to
your project. For each highlighted term, perform a detail dump to explore related ideas
4. **Group similar ideas.** After your general and detail dumps, group related concepts together and note any missing components.

Use the `generate_outline` function in `iterative_proposal_workflow.py` to transform this brain dump into a preliminary outline. This LLM call will organise your ideas into logical sections (e.g., introduction, objectives, methodology, team, commercialisation) and identify missing pieces.

## 2. Ingest the Solicitation and Set Evaluation Criteria
1. **Obtain the solicitation.** Download the funding opportunity’s
solicitation document (PDF). All solicitations include a section
describing the evaluation criteria.
2. **Extract criteria.** Use the `ingest_solicitation` function to summarise the solicitation and extract the evaluation criteria as a list of topics. For example, NASA SBIR solicitations typically include innovation, technical merit, team qualifications and commercial potential.
3. **Customise prompts.** Pass the extracted criteria to `customise_role_prompts` to tailor the detail reviewer and panel questions. This ensures that the reviewers check whether your draft addresses each criterion.

## 3. Assign T‑Shirt Sizes and Estimate Budget
1. **List tasks.** Break down your project into discrete tasks based on the outline. Keep tasks coarse‑grained—something that could be done by a person or small team.
2. **Assign sizes.** For each task, assign a t‑shirt size (XS, S, M, L, XL). According to project management best practices, you should decide up front what each size represents (scope, effort, or complexity) and ensure all team members understand the definitions.
3. **Define the mapping.** Establish the hours associated with each size (e.g., XS=4h, S=8h, M=24h, L=56h, XL=120h). You may customise these values depending on your team and project type.
4. **Estimate costs.** Use `estimate_budget(tasks, size_to_hours, hourly_rate, overhead, buffer)` to compute the labour hours and cost for each task and the total budget. The function applies overhead (indirect costs) and schedule buffer to avoid over‑commitment and burnout.
5. **Review and adjust.** Examine the budget output. If the total exceeds the allowable proposal amount, adjust task sizes or scope. Consider adding or removing tasks, combining similar items or reassigning work to reduce cost.

## 4. Run the Multi‑Role Review
1. **Prepare your draft.** Once you have an outline and an initial draft of the proposal, save it as a PDF (or text). Ideally, each section should align with the evaluation criteria.

1. **Select roles.** Decide which reviewer roles to engage. The available roles include:
    - **Technical reviewer:** Focuses on engineering excellence and feasibility.
    - **Business strategist:** Evaluates commercial potential and business strategy.
    - **Detail reviewer:** Ensures completeness and compliance with the solicitation; checks formatting and missing elements.
    - **Panel reviewer:** Scores each criterion from solicitation (High/Medium/Low) and provides justification.
    - **Storytelling reviewer (optional):** Evaluates narrative flow and coherence. If desired, add this role by defining a new system prompt and question in your code.

3. **Run the review.** Call run_iterative_review(proposal_pdf, criteria, roles, …). If you include criteria, the NASA panel and detail reviewer prompts are customised. The function returns:
    -`feedback`: raw text from each reviewer.
    -`scorecard`: mapping from each criterion to a rating and numeric score (High=3, Medium=2, Low=1).
    -`average_score`: mean of the numeric scores.
    -`weighted_score`: weighted average if you provide a weights dictionary mapping criterion names to importance factors when calling `run_iterative_review`.

4. **Interpret feedback.** Read the reviewer comments and note strengths, weaknesses and suggestions for improvement. Focus on criteria with low ratings or weak justifications.

5. **Iterate.** Revise the draft based on feedback and rerun the review. Track how scores and comments change across iterations. According to writing experts, embracing multiple drafts and incorporating feedback yields better results.

## 5. Manage Reviewer Actions
### For Reviewers 
* **Read the customised instructions.** Each reviewer receives a system prompt and a question tailored to their role. Reviewers should familiarise themselves with these instructions before evaluating a draft.
* **Focus on your domain.** Technical reviewers should assess the engineering soundness, feasibility and innovation relative to the state of the art. Business strategists should assess market need, commercial readiness and business model viability. Detail reviewers should cross‑reference the solicitation to ensure nothing is missing.
* **Provide constructive feedback.** Note both strengths and areas for improvement. Avoid vague statements; instead, cite specific sections and suggest concrete changes.
* **Assign ratings where applicable.** NASA panel reviewers (or any scoring reviewer) should rate each evaluation criterion as High, Medium or Low, with justification.

### For the Proposal Owner (You)
* **Coordinate reviewers.** Ensure that all reviewers have access to the solicitation criteria and the latest draft. Provide deadlines and clarifications as needed.
* **Synthesize feedback.** After each review, consolidate comments into a single action list. Prioritise fixes that affect multiple criteria or that carry the heaviest weight in the solicitation.
* **Track versions and scores.** Maintain a record of each draft, its associated scorecard and the changes made. This will show progress and help justify your improvements in case you need to discuss them with a partner or advisor.

## 6. Example Workflow Summary
1. Use `generate_outline` on your brain dump to create a structured outline.
2. Read the solicitation, extract criteria with `ingest_solicitation`.
3. Customise reviewer prompts via `customise_role_prompts`.
4. Decompose the project into tasks and assign t‑shirt sizes; estimate the budget with `estimate_budget` and adjust as needed.
5. Draft the proposal (initial sections can follow the outline) and save as a PDF.
6. Run `run_iterative_review` with the proposal PDF and extracted criteria; include all reviewer roles.
7. Review the feedback and scorecard; note action items and revise.
8. Iterate: repeat steps 5–7 until you achieve satisfactory scores and completeness.
