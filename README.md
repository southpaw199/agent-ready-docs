# agent-ready-docs

Methods and case studies for testing whether documentation works for AI agents as well as for people.

## Why this project exists

More and more developers meet a product through an AI coding agent: they ask Claude Code or Codex to set something up, and the agent reads the docs for them. When the docs leave out a prerequisite, show an example that doesn't run, or document an API in only one language, the agent either gets stuck or fills the gap from memory. The developer may never know which happened.

Docs are usually reviewed by people reading them. This project tests them the way agents use them: it gives an agent a real developer task and only the docs, then checks what the agent produces and where it went beyond them.

## How a review works

The [agent task review](methods/agent-task-review/method.md) is the method behind each case study:

1. **Choose real tasks.** Four to six tasks a new developer would attempt, from first install to a production concern.
2. **Limit the agent to the docs.** Each attempt starts in a clean environment, and the agent must cite every page it relies on.
3. **Verify independently.** The reviewer reruns the agent's code and checks the result against written success criteria. An agent saying it succeeded isn't evidence that it did.
4. **Check the sources.** Cited pages must say what the agent claims, and anything it used that isn't in the docs is recorded.
5. **Use two agents.** A gap that two different agents hit is stronger evidence than one.
6. **Report by root cause.** Each finding is traced to a cause, such as a missing prerequisite, an incomplete example, or a page the agent couldn't find, and comes with a specific fix. The report also credits what the docs do well.

Every run is scored on a shared [rubric](methods/agent-task-review/rubric.md): pass, pass with issues, pass with hints, or fail. Every finding is rated High, Medium, or Low severity. The method can also compare the docs alone with the docs plus a documentation MCP server.

## What each case study publishes

Everything needed to check a finding: the tasks and success criteria, reference solutions and the checkers that score each run, every agent's code and transcript, a run log, a findings log with the evidence for each finding, and the report.

## Who this is for

- **Documentation and developer-experience teams** who want to know how their docs work for agents, and what to fix first.
- **Anyone evaluating AI agents against docs**, who wants to see how such a review can be run and scored.

## Status

The method is at version 0.4, a draft that improves as each case study tests it. Each version is tagged, and its [changelog](methods/agent-task-review/method.md#changelog) says what changed. Both case studies, LanceDB and NVIDIA OpenUSD, are complete. A related case study on NVIDIA's Omniverse and Isaac Sim, which are built on OpenUSD, is a possible future project.

Each case study has its own repo, listed below.

## Case studies

| Product | Method | Result |
| --- | --- | --- |
| [LanceDB](https://github.com/southpaw199/agent-ready-lancedb) | Agent task review, with Claude Code and Codex | Both agents passed 5 of 5 tasks; 4 main findings, led by deprecated APIs in the sync Python examples. [Report](https://github.com/southpaw199/agent-ready-lancedb/blob/main/reviews/agent-task-review/report.md) |
| [NVIDIA OpenUSD](https://github.com/southpaw199/agent-ready-nvidia) | Agent task review, with Claude Code and Codex, then rerun with NVIDIA's USD Code MCP server | Both agents completed 5 of 5 OpenUSD tasks with no hints; 2 main findings, led by Python names missing from the C++-only API reference. [Report](https://github.com/southpaw199/agent-ready-nvidia/blob/main/reviews/agent-task-review/report.md) |

## How this repo is organized

| Folder | What it holds |
| --- | --- |
| [`methods/`](methods/) | Reusable evaluation methods. Each method defines its procedure, scoring rubric, and templates. |
| [`tools/`](tools/) | Scripts shared across case studies, such as [`report_to_pdf.py`](tools/report_to_pdf.py), which builds a PDF of a case study's report with the method, rubric, and findings log as appendices. |

A method's folder name is the same everywhere it appears: `methods/agent-task-review/` here defines the method, and `reviews/agent-task-review/` in a case study's repo applies it.

## Methods

| Method | Question it answers |
| --- | --- |
| [Agent task review](methods/agent-task-review/method.md) | Can an AI coding agent complete real developer tasks using only the product's docs? |

Each method version is tagged (`v0.1`, `v0.2`, and so on), and each case study links to the version it used.

## Use of AI tools

AI coding assistants helped draft code and content in this repo. I ran, tested, and verified every example and every finding myself. Agent outputs are evidence to check, not results to trust.

## License

Created by Alan Sloan ([LinkedIn](https://www.linkedin.com/in/alansloan)).

- **Code** (Python files, notebooks, and workflows) is licensed under the [MIT License](LICENSE).
- **Written content** (methods, reports, findings, task definitions, and READMEs) is © 2026 Alan Sloan. All rights reserved: you may read and link to it, but not copy, republish, or adapt it without permission. See [COPYRIGHT.md](COPYRIGHT.md).
