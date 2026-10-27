# Tools

Scripts shared across case studies. Scripts that only one case study needs belong in that case study's repo.

| Script | What it does |
| --- | --- |
| [`report_to_pdf.py`](report_to_pdf.py) | Builds a PDF of a case study's agent task review report, with the method, the rubric, and the findings log as appendices. |

## report_to_pdf.py

The PDF is meant to stand on its own, for example to share with someone who won't browse the repos. It holds:

- **The report**, from the case study's `reviews/agent-task-review/report.md`.
- **Appendix A, the method**, and **Appendix B, the rubric**, from this repo, at the tagged version the report links to. When a report used more than one version, the appendices reproduce the later one. If that version's rubric predates the severity scale, the scale's section is added from the first version that defines it. A note at the start of each appendix says which version it is, and why.
- **Appendix C, the findings log**, printed in landscape so its tables stay readable.

Links between these parts jump within the PDF. Links to files that aren't included, such as the run log or transcripts, point to GitHub. The page size is US Letter.

### Set up

You need Python 3 and Chrome or Edge. In WSL, the script uses the Windows browser, so nothing else needs installing. From the root of this repo:

```bash
python3 -m venv tools/.venv
tools/.venv/bin/pip install -r tools/requirements.txt
```

### Run

Pass the case study's repo folder:

```bash
tools/.venv/bin/python tools/report_to_pdf.py ~/projects/agent-ready-lancedb
```

That writes `agent-ready-lancedb-report.pdf` to the current folder. Options:

| Option | Use |
| --- | --- |
| `-o PATH` | Write the PDF somewhere else. |
| `--html` | Also keep the HTML next to the PDF, to check the layout in a browser. |
| `--browser PATH` | Use a specific Chrome or Edge, if the script doesn't find one. |

The PDF is built from the files as they are on disk, including uncommitted changes, so check that the case study's repo is on the branch you mean to share.
