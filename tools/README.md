# Tools

Scripts shared across case studies. Scripts that only one case study needs belong in that case study's repo.

| Script | What it does |
| --- | --- |
| [`report_to_pdf.py`](report_to_pdf.py) | Builds a PDF of a case study's agent task review report, with the method, the rubric, the task prompts, and the findings log as appendices. |

## report_to_pdf.py

The PDF is meant to stand on its own, for example to share with someone who won't browse the repos. It holds:

- **The report**, from the case study's `reviews/agent-task-review/report.md`, with two additions that exist only in the PDF: a table of contents below the title and author line, listing the report's sections and the appendices with their page numbers, and a sentence after the Summary's task table pointing to Appendix C.
- **Appendix A, the method**, and **Appendix B, the rubric**, from this repo, at the tagged version the report links to. When a report used more than one version, the appendices reproduce the later one. If that version's rubric predates the severity scale, the scale's section is added from the first version that defines it. A note at the start of each appendix says which version it is, and why.
- **Appendix C, the task prompts**, from the case study's `reviews/agent-task-review/tasks.md`: each set of standard instructions, and each task's prompt, word for word. The success criteria and the rest of the task file are left out.
- **Appendix D, the findings log**, printed in landscape so its tables stay readable.

Links between these parts jump within the PDF, including links to the parts of the task file that Appendix C reproduces. Links to files that aren't included, such as the run log or transcripts, or to the rest of the task file, point to GitHub.

Every page after the first has the report's title in italics at the top right. Every page's footer has the author, linked to their LinkedIn profile, and the case study's repo, linked to GitHub, on the left, and "Page X of Y" on the right. The author's name and LinkedIn link come from the report's `**Author:**` line, so the script stops if that line is missing. Browsers can't number a table of contents, so the script prints the PDF twice: once to find the page each section starts on, and again with those page numbers filled in.

The PDF has bookmarks for every heading, nested as in the document, and opens with them showing. Its document properties give the report's title, the author, a subject, keywords, and the copyright notice. The notice is the "Copyright ©" line from the case study's `COPYRIGHT.md`, so the script stops if that file or line is missing. It's stored where Acrobat shows it under Copyright Status, linked to that file on GitHub. Table rows never break across pages; a row that doesn't fit moves to the next page. The page size is US Letter.

### Set up

You need Python 3 and Chrome or Edge. In WSL, the script uses the Windows browser, so nothing else needs installing. From the root of this repo:

```bash
python3 -m venv tools/.venv
tools/.venv/bin/pip install -r tools/requirements.txt
```

`requirements.txt` installs `markdown-it-py` and `mdit-py-plugins`, which turn the Markdown into HTML the way GitHub does, and `pypdf` and `pypdfium2`, which add the footer links after the browser prints the PDF. Browsers print page headers and footers as plain text, so links there have to be added afterwards. Rerun the `pip install` line after pulling a change to `requirements.txt`.

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

### Open the PDF from Windows

When you run the script in WSL, the PDF is written inside the Linux file system. To open it in Windows, do one of these:

- **Write it straight to a Windows folder** with `-o`. Windows drives are under `/mnt/`, so your Downloads folder is `/mnt/c/Users/<your Windows user name>/Downloads`:

  ```bash
  tools/.venv/bin/python tools/report_to_pdf.py ~/projects/agent-ready-nvidia -o /mnt/c/Users/<your Windows user name>/Downloads/nvidia-report.pdf
  ```

  To find your Windows user name from WSL, run `cmd.exe /c "echo %USERNAME%"`.

- **Copy a PDF you've already made** to a Windows folder:

  ```bash
  cp agent-ready-nvidia-report.pdf /mnt/c/Users/<your Windows user name>/Downloads/
  ```

- **Open it in your default PDF viewer** without copying it:

  ```bash
  explorer.exe "$(wslpath -w agent-ready-nvidia-report.pdf)"
  ```

- **Browse to it in File Explorer.** Linux folders are under `\\wsl.localhost\<distribution name>\` in the address bar, for example `\\wsl.localhost\Ubuntu-24.04\home\<your Linux user name>\projects\agent-ready-docs`. To list your distribution names, run `wsl.exe -l` in a Windows terminal.
