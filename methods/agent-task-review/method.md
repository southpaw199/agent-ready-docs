# Agent task review

**Question:** Can an AI coding agent complete real developer tasks using only a product's documentation, and where does it get stuck?

**Version:** 0.1 (draft). Record the method version in each case study's report.

## Procedure

1. **Choose the tasks.** Pick four to six tasks a new developer would actually attempt, from first install to a production concern such as indexing or error handling. Write each one with [task-template.md](task-template.md).
2. **Prepare a clean environment.** Start every attempt in a new, empty folder with a fresh virtual environment, so nothing from an earlier attempt helps.
3. **Restrict the agent to the docs.** Point the agent at the product's documentation entry point (for example, its `llms.txt` file) and instruct it to use only pages from that site and to cite every page it relies on.
4. **Run without help.** Give the agent the task and let it work. When it stalls, record what it was missing, then give the smallest hint that lets it continue, and record the hint.
5. **Verify the result yourself.** Run the agent's code and check the output against the task's success criteria. An agent reporting success is not evidence of success.
6. **Log every attempt.** Add one row per attempt to the case study's `run-log.csv`, using the columns in [run-log-template.csv](run-log-template.csv) and the categories in [rubric.md](rubric.md). Save transcripts and code in `runs/<date>-<agent>/`.
7. **Repeat with a second agent** where possible. A failure that two different agents share is stronger evidence of a docs gap than a failure in one.
8. **Report.** Summarize findings by root cause, credit what the docs already do well, and propose a specific fix for each gap.

## Known limitations

- **Prior knowledge.** Models may already know a popular product from training data, so a run tests the docs plus that prior knowledge, not the docs alone. Requiring page citations reduces this effect but does not remove it.
- **Non-determinism.** The same agent can behave differently on repeated runs. Record agent and model versions, and treat a single run as a signal, not a verdict.
- **Product defects.** Some failures come from the product, not the docs. Log them under `product-defect` and keep them out of the docs findings.
