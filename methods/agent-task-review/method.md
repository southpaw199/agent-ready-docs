# Agent task review

**Author:** Alan Sloan · [linkedin.com/in/alansloan](https://www.linkedin.com/in/alansloan) · [github.com/southpaw199](https://github.com/southpaw199)

**Question:** Can an AI coding agent complete real developer tasks using only a product's documentation, and where does it get stuck?

**Version:** 0.4 (draft). Record the method version in each case study's report.

## Procedure

1. **Choose the tasks.** Pick four to six tasks a new developer would actually attempt, from first install to a production concern such as indexing or error handling. Write each one with [task-template.md](task-template.md).
2. **Prepare a clean environment.** Start every attempt in a new, empty folder with a fresh virtual environment, so nothing from an earlier attempt helps.
3. **Restrict the agent to the docs.** Point the agent at the product's documentation entry point (for example, its `llms.txt` file) and instruct it to use only pages from that site and to cite every page it relies on. To test a documentation MCP server, run the same tasks again as a second condition, `docs+mcp`: register the server only in that run's folder, tell the agent it's available without telling it to use it, and ask it to name the tool and query behind each step that relies on an MCP result.
4. **Run without help.** Give the agent the task and let it work. When it stalls, record what it was missing, then give the smallest hint that lets it continue, and record the hint.
5. **Verify the result yourself.** Run the agent's code and check the output against the task's success criteria. An agent reporting success is not evidence of success.
6. **Log every attempt.** Add one row per attempt to the case study's `run-log.csv`, using the columns in [run-log-template.csv](run-log-template.csv) and the categories in [rubric.md](rubric.md). Save transcripts and code in `runs/<date>-<agent>/`.
7. **Repeat with a second agent** where possible. A failure that two different agents share is stronger evidence of a docs gap than a failure in one.
8. **Report.** Summarize findings by root cause, rate each one's severity using the [rubric](rubric.md#severity), credit what the docs already do well, and propose a specific fix for each gap.

## Running and recording a session

| | Claude Code (VS Code extension) | Codex CLI |
| --- | --- | --- |
| Check for standing instructions | `~/.claude/CLAUDE.md`, plus `/mcp` for connected servers | `~/.codex/AGENTS.md`, plus `/status` |
| Settings used for a clean run | `autoMemoryEnabled: false` and `disableClaudeAiConnectors: true` in `~/.claude/settings.json` | `web_search = "disabled"`, `approval_policy = "on-request"`, and `apps = false` and `memories = false` under `[features]` in `~/.codex/config.toml` |
| Start from a clean terminal | Run `deactivate`, or open a new terminal, before `code <run folder>`; the session inherits the terminal's environment, including any virtual environment left active by a rerun | Run `deactivate`, or open a new terminal, before starting `codex` in the run folder |
| Record version and model | `/status` | `codex --version` and `/status` |
| Save the conversation | `/export transcript.md` | `/export transcript.md` |
| Watch progress | The **Output** panel, set to the Claude Code log, shows each step; `Ctrl+Alt+F` toggles hidden tool calls in the chat panel | Shown in the terminal as it runs |

Restore your usual settings when the runs are finished. To check afterwards which Python a session started with, read `.venv/pyvenv.cfg` in the run folder: its `command` line shows the interpreter that created the agent's environment. Before committing a transcript, remove any long passages of downloaded docs content, keeping the commands and the agent's messages.

## Known limitations

- **Prior knowledge.** Models may already know a popular product from training data, so a run tests the docs plus that prior knowledge, not the docs alone. Requiring page citations reduces this effect but does not remove it.
- **Non-determinism.** The same agent can behave differently on repeated runs. Record agent and model versions, and treat a single run as a signal, not a verdict.
- **Product defects.** Some failures come from the product, not the docs. Log them under `product-defect` and keep them out of the docs findings.

## Changelog

- **0.4 (2026-10-27):** Added a severity scale for findings (High, Medium, Low) to the [rubric](rubric.md#severity), first used in NVIDIA's Tier 1 report. Outcomes and root causes are unchanged. LanceDB's findings, reviewed under 0.1, were rated on this scale afterwards.
- **0.3 (2026-10-26):** Added the `docs+mcp` condition for testing a documentation MCP server: `condition` and `mcp_calls` columns in the [run log](run-log-template.csv), and MCP results counted as sources, checked like cited pages, so a wrong or outdated MCP result the agent relied on scores `pass-with-issues` (see the [rubric](rubric.md)). Docs-only runs scored under 0.2, such as NVIDIA's Tier 1, keep their scores and take `docs` in the new column.
- **0.2 (2026-10-23):** Added the `pass-with-issues` outcome to the [rubric](rubric.md), for runs that meet every success criterion but have unreported warnings, knowledge not from the docs, or citations that don't hold up. Reviews run under 0.1, such as LanceDB's, keep their published scores. Updated 2026-10-25: added the "Start from a clean terminal" row, after three NVIDIA sessions inherited a reviewer's rerun environment. No change to scoring.
- **0.1 (2026-10-21):** First version, used for the LanceDB review.

---

© 2026 Alan Sloan. All rights reserved. You may read and link to this method; you may not copy, republish, or adapt it without permission. See [COPYRIGHT.md](../../COPYRIGHT.md).
