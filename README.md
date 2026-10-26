# agent-ready-docs

Methods and case studies for testing whether documentation works for AI agents as well as for people.

AI coding agents increasingly learn a product from its docs before a developer ever reads them. This repo asks a practical question: given only a product's documentation, can an agent complete real developer tasks, and where does it get stuck? Each finding traces a failure back to the docs (a missing prerequisite, an incomplete example, an unclear error) and proposes a fix.

## Case studies

| Product | Method | Result |
| --- | --- | --- |
| [LanceDB](case-studies/lancedb/) | Agent task review, with Claude Code and Codex | Both agents passed 5 of 5 tasks; 4 main findings, led by deprecated APIs in the sync Python examples. [Report](case-studies/lancedb/reviews/agent-task-review/report.md) |
| [NVIDIA OpenUSD](case-studies/nvidia/) | Agent task review, with Claude Code and Codex (Tier 1 of 3; Omniverse and Isaac Sim to come) | Both agents completed 5 of 5 OpenUSD tasks with no hints; 2 main findings, led by Python names missing from the C++-only API reference. [Report](case-studies/nvidia/reviews/agent-task-review/report.md) |

## How this repo is organized

| Folder | What it holds |
| --- | --- |
| [`methods/`](methods/) | Reusable evaluation methods. Each method defines its procedure, scoring rubric, and templates. |
| [`case-studies/`](case-studies/) | One folder per product evaluated. Each holds runnable examples and one review folder per method applied. |
| [`tools/`](tools/) | Scripts shared across case studies. |

A method's folder name is the same everywhere it appears: `methods/agent-task-review/` defines the method, and `case-studies/<product>/reviews/agent-task-review/` applies it.

## Methods

| Method | Question it answers |
| --- | --- |
| [Agent task review](methods/agent-task-review/method.md) | Can an AI coding agent complete real developer tasks using only the product's docs? |

## Use of AI tools

AI coding assistants helped draft code and content in this repo. I ran, tested, and verified every example and every finding myself. Agent outputs are evidence to check, not results to trust.

## License

Created by Alan Sloan ([LinkedIn](https://www.linkedin.com/in/alansloan)).

- **Code** (Python files, notebooks, and workflows) is licensed under the [MIT License](LICENSE).
- **Written content** (methods, reports, findings, task definitions, and READMEs) is © 2026 Alan Sloan. All rights reserved: you may read and link to it, but not copy, republish, or adapt it without permission. See [COPYRIGHT.md](COPYRIGHT.md).
- **Agent transcripts** in the `runs/` folders are records of each agent's output, included as evidence.
