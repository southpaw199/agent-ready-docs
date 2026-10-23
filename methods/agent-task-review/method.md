# Agent task review

**Author:** Alan Sloan · [linkedin.com/in/alansloan](https://www.linkedin.com/in/alansloan) · [github.com/southpaw199](https://github.com/southpaw199)

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

## Running and recording a session

| | Claude Code (VS Code extension) | Codex CLI |
| --- | --- | --- |
| Check for standing instructions | `~/.claude/CLAUDE.md`, plus `/mcp` for connected servers | `~/.codex/AGENTS.md`, plus `/status` |
| Settings used for a clean run | `autoMemoryEnabled: false` and `disableClaudeAiConnectors: true` in `~/.claude/settings.json` | `web_search = "disabled"`, `approval_policy = "on-request"`, and `apps = false` and `memories = false` under `[features]` in `~/.codex/config.toml` |
| Record version and model | `/status` | `codex --version` and `/status` |
| Save the conversation | `/export transcript.md` | `/export transcript.md` |
| Watch progress | The **Output** panel, set to the Claude Code log, shows each step; `Ctrl+Alt+F` toggles hidden tool calls in the chat panel | Shown in the terminal as it runs |

Restore your usual settings when the runs are finished. Before committing a transcript, remove any long passages of downloaded docs content, keeping the commands and the agent's messages.

## Known limitations

- **Prior knowledge.** Models may already know a popular product from training data, so a run tests the docs plus that prior knowledge, not the docs alone. Requiring page citations reduces this effect but does not remove it.
- **Non-determinism.** The same agent can behave differently on repeated runs. Record agent and model versions, and treat a single run as a signal, not a verdict.
- **Product defects.** Some failures come from the product, not the docs. Log them under `product-defect` and keep them out of the docs findings.

---

© 2026 Alan Sloan. This method is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): you may share and adapt it, with credit to the author.
