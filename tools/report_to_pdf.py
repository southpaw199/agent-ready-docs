#!/usr/bin/env python3
"""Build a PDF of a case study's agent task review report.

The PDF holds the report, then four appendices: the method and the rubric,
as of the version the report used, the prompts each agent was given, and the
case study's findings log, printed in landscape. Links between these parts become links within the PDF; links to
files that aren't included point to GitHub.

Usage:
    python tools/report_to_pdf.py ~/projects/agent-ready-lancedb
    python tools/report_to_pdf.py ~/projects/agent-ready-nvidia -o nvidia.pdf

The PDF is printed with headless Chrome or Edge. In WSL, the Windows browser is
used. See tools/README.md for setup.
"""
import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pypdfium2 as pdfium
from markdown_it import MarkdownIt
from mdit_py_plugins.anchors import anchors_plugin
from pypdf import PdfReader, PdfWriter
from pypdf.annotations import Link

METHOD_REPO = Path(__file__).resolve().parents[1]
METHOD_DIR = "methods/agent-task-review"
REVIEW_DIR = "reviews/agent-task-review"
GITHUB = "https://github.com/southpaw199"
METHOD_LINK = re.compile(
    r"https://github\.com/southpaw199/agent-ready-docs/blob/(v[\d.]+)/methods/agent-task-review/(method|rubric)\.md(#[\w-]+)?$"
)
MD_LINK = re.compile(r"\]\(([^)\s]+)\)")
AUTHOR_LINE = re.compile(r"^\*\*Author:\*\* (.+?) · \[[^\]]*\]\((https://www\.linkedin\.com/[^)]+)\)", re.M)
FOOTER_TOP = 45  # points from the bottom edge; footer text sits below this, body text above
BROWSERS = [
    "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
    "/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "google-chrome",
    "chromium",
    "chromium-browser",
]

PAGE_CSS = """
@page { size: letter; margin: 0.75in 0.75in 0.85in;
  @top-right { content: "{title}"; font: italic 8.5pt "Segoe UI", Arial, sans-serif; color: #666; }
  @bottom-left { content: "{footer}"; font: 8.5pt "Segoe UI", Arial, sans-serif; color: #666; }
  @bottom-right { content: "Page " counter(page) " of " counter(pages); font: 8.5pt "Segoe UI", Arial, sans-serif; color: #666; } }
@page :first { @top-right { content: none; } }
@page landscape { size: letter landscape; margin: 0.6in 0.6in 0.75in; }
"""

CSS = """
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 10pt; line-height: 1.45; color: #1f2328; }
h1 { font-size: 20pt; margin: 0 0 0.4em; }
h2 { font-size: 14pt; border-bottom: 1px solid #d0d7de; padding-bottom: 0.2em; margin-top: 1.6em; }
h3 { font-size: 11.5pt; margin-top: 1.3em; }
h4 { font-size: 10.5pt; }
h2, h3, h4 { break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 0.6em 0 1em; font-size: 8.8pt; break-inside: avoid; }
th, td { border: 1px solid #d0d7de; padding: 4px 6px; vertical-align: top; text-align: left; overflow-wrap: break-word; }
td:first-child { white-space: nowrap; }
td ul, td ol { margin: 0; padding-left: 1.2em; }
td li + li, td li ul { margin-top: 0.3em; }
th { background: #f6f8fa; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
code { font-family: Consolas, "Courier New", monospace; font-size: 0.92em; background: #f6f8fa; padding: 0 0.2em; border-radius: 3px; }
pre { background: #f6f8fa; padding: 0.6em; font-size: 8.5pt; white-space: pre-wrap; break-inside: avoid; }
pre code { background: none; padding: 0; }
a { color: #0969da; text-decoration: none; }
hr { border: 0; border-top: 1px solid #d0d7de; }
blockquote { margin: 0.6em 0 1em; padding: 0 1em; border-left: 3px solid #d0d7de; color: #3d444d; }
.appendix { break-before: page; }
.landscape { page: landscape; }
.landscape table { font-size: 8pt; break-inside: auto; }
.note { color: #57606a; font-style: italic; }
.toc ul { list-style: none; padding: 0; margin: 0.5em 0 0; }
.toc li { margin: 0.2em 0; }
.toc li.gap { margin-top: 0.7em; }
.toc a { display: flex; color: inherit; }
.toc .leader { flex: 1; border-bottom: 1px dotted #8c959f; margin: 0 0.4em 0.35em; }
"""
PROMPTS_POINTER = "[Appendix C](#prompts) gives each task's full prompt, word for word, as the agents received it."


def git_show(ref, path):
    return subprocess.run(["git", "-C", str(METHOD_REPO), "show", f"{ref}:{path}"],
                          capture_output=True, text=True, check=True).stdout


def method_tags():
    out = subprocess.run(["git", "-C", str(METHOD_REPO), "tag", "--list", "v*"],
                         capture_output=True, text=True, check=True).stdout.split()
    return sorted(out, key=version_key)


def version_key(tag):
    return tuple(int(n) for n in tag.lstrip("v").split("."))


def repo_name(repo):
    url = subprocess.run(["git", "-C", str(repo), "remote", "get-url", "origin"],
                         capture_output=True, text=True).stdout.strip()
    m = re.search(r"github\.com[/:]southpaw199/([\w.-]+?)(?:\.git)?$", url)
    return m.group(1) if m else repo.name


def section(text, heading):
    """Return the "## heading" section of a Markdown file, up to the next ## heading."""
    m = re.search(rf"^## {re.escape(heading)}\n.*?(?=^## |\Z)", text, re.S | re.M)
    return m.group(0).rstrip() + "\n" if m else None


def drop_title(text):
    """Remove a file's own # title, since the appendix supplies its own."""
    return re.sub(r"\A# .*\n+", "", text)


def prompts(tasks):
    """Return the standard instructions and each task's prompt from a task file, word for word.

    Each standard instructions section is kept up to its next heading. Each task keeps
    its ## heading and the blockquote after "**Prompt given to the agent:**"."""
    out = []
    for m in re.finditer(r"^## (.*?)\n(.*?)(?=^#{2,3} |^---$|\Z)", tasks, re.S | re.M):
        heading, body = m.groups()
        if heading.lower().endswith("standard instructions"):
            out.append(f"## {heading}\n\n{body.strip()}\n")
        elif heading.startswith("Task "):
            prompt = re.search(r"^\*\*Prompt given to the agent:\*\*\n((?:>.*\n)+)", body, re.M)
            if not prompt:
                sys.exit(f"The task file's {heading!r} has no prompt.")
            out.append(f"## {heading}\n\n{prompt.group(1)}")
    return "\n".join(out)


class Linker:
    """Rewrites a part's Markdown links for the combined PDF."""

    def __init__(self, case_repo, case_name, method_tag, prompt_ids=()):
        self.case_repo = case_repo
        self.case_name = case_name
        self.method_tag = method_tag
        self.prompt_ids = set(prompt_ids)  # heading ids in the prompts appendix

    def rewrite(self, text, part, repo, file_dir):
        """part: anchor prefix for this part ("" for the report); repo: "case" or "method";
        file_dir: the file's folder, relative to its repo root."""
        def fix(m):
            return "](" + self.target(m.group(1), part, repo, file_dir) + ")"
        return MD_LINK.sub(fix, text)

    def target(self, url, part, repo, file_dir):
        m = METHOD_LINK.match(url)
        if m:
            return self.anchor(m.group(2), m.group(3))
        if "://" in url or url.startswith("mailto:"):
            return url
        if url.startswith("#"):
            return self.anchor(part, url)
        path, _, frag = url.partition("#")
        frag = "#" + frag if frag else None
        resolved = os.path.normpath(os.path.join(file_dir, path))
        if repo == "case":
            if resolved == f"{REVIEW_DIR}/report.md":
                return self.anchor("", frag) if frag else "#top"
            if resolved == f"{REVIEW_DIR}/findings.md":
                return self.anchor("findings", frag)
            # The task file's sections that the prompts appendix reproduces; the rest stays on GitHub.
            if resolved == f"{REVIEW_DIR}/tasks.md" and frag and frag[1:] in self.prompt_ids:
                return self.anchor("prompts", frag)
            return f"{GITHUB}/{self.case_name}/blob/main/{resolved}" + (frag or "")
        if resolved in (f"{METHOD_DIR}/method.md", f"{METHOD_DIR}/rubric.md"):
            return self.anchor(Path(resolved).stem, frag)
        return f"{GITHUB}/agent-ready-docs/blob/{self.method_tag}/{resolved}" + (frag or "")

    @staticmethod
    def anchor(part, frag):
        if not frag:
            return f"#{part}"
        return f"#{part}-{frag[1:]}" if part else frag


def point_to_prompts(report):
    """Add a sentence to the report's Summary that points to the prompts appendix:
    after the Summary's first table, or else at the end of the Summary."""
    summary = section(report, "Summary")
    if summary is None:
        sys.exit("The report has no ## Summary section.")
    table = re.search(r"^\|.*\n(?!\|)", summary, re.M)
    end = table.end() if table else len(summary)
    return report.replace(summary, summary[:end] + "\n" + PROMPTS_POINTER + "\n" + summary[end:].rstrip("\n") + "\n", 1)


def contents(entries, pages):
    """The table of contents. entries: (id, title, starts_group) for each entry;
    pages: id -> page number, empty on the first pass."""
    items = "".join(f'<li class="{"gap" if gap else ""}"><a href="#{id_}"><span>{title}</span>'
                    f'<span class="leader"></span><span>{pages.get(id_, "")}</span></a></li>'
                    for id_, title, gap in entries)
    return f'<nav class="toc"><h2>Contents</h2><ul>{items}</ul></nav>\n'


def page_numbers(pdf_file):
    """Map each named destination in the PDF, which Chrome writes for every linked anchor, to its page."""
    reader = PdfReader(str(pdf_file))
    return {name.lstrip("/"): reader.get_destination_page_number(dest) + 1
            for name, dest in reader.named_destinations.items()}


def render(md, text, prefix):
    out = md.render(text)
    if prefix:
        out = re.sub(r'(<h[1-6] id=")', rf"\1{prefix}-", out)
    return out


def css_string(text):
    return text.replace("\\", "\\\\").replace('"', '\\"')


def link_footer(pdf_file, links):
    """Add clickable links over footer text. Chrome prints page margins as plain
    text, so links there have to be added to the PDF afterwards.

    links: (text, url) pairs; each match of text in a page's footer gets a link."""
    found = []
    doc = pdfium.PdfDocument(str(pdf_file))
    for i in range(len(doc)):
        textpage = doc[i].get_textpage()
        for text, url in links:
            searcher = textpage.search(text, match_case=True)
            while hit := searcher.get_next():
                boxes = [textpage.get_charbox(j) for j in range(hit[0], hit[0] + hit[1])]
                rect = (min(b[0] for b in boxes), min(b[1] for b in boxes),
                        max(b[2] for b in boxes), max(b[3] for b in boxes))
                if rect[3] < FOOTER_TOP:
                    found.append((i, rect, url))
    doc.close()
    writer = PdfWriter(clone_from=PdfReader(str(pdf_file)))
    for i, rect, url in found:
        writer.add_annotation(page_number=i, annotation=Link(rect=rect, url=url))
    with open(pdf_file, "wb") as f:
        writer.write(f)
    return len(found)


def find_browser(arg):
    for candidate in ([arg] if arg else BROWSERS):
        path = shutil.which(candidate) or (candidate if Path(candidate).exists() else None)
        if path:
            return path
    sys.exit("No Chrome or Edge found; pass its path with --browser.")


def print_pdf(browser, html_file, pdf_file):
    windows = browser.startswith("/mnt/")
    to_arg = (lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True,
                                       text=True, check=True).stdout.strip()) if windows else str
    profile = tempfile.mkdtemp(dir=html_file.parent)
    cmd = [browser, "--headless=new", "--disable-gpu", "--no-first-run", "--no-pdf-header-footer",
           f"--user-data-dir={to_arg(profile)}", f"--print-to-pdf={to_arg(pdf_file)}", to_arg(html_file)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if not pdf_file.exists():
        sys.exit(f"The browser didn't write a PDF.\n{result.stderr[-2000:]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("case_study", type=Path, help="the case study repo, for example ~/projects/agent-ready-lancedb")
    parser.add_argument("-o", "--output", type=Path, help="the PDF to write (default: <repo>-report.pdf here)")
    parser.add_argument("--browser", help="path to Chrome or Edge, if it isn't found automatically")
    parser.add_argument("--html", action="store_true", help="also keep the HTML, to check the layout in a browser")
    args = parser.parse_args()

    case_repo = args.case_study.expanduser().resolve()
    report_path = case_repo / REVIEW_DIR / "report.md"
    findings_path = case_repo / REVIEW_DIR / "findings.md"
    tasks_path = case_repo / REVIEW_DIR / "tasks.md"
    if not report_path.exists():
        sys.exit(f"No report at {report_path}")
    case_name = repo_name(case_repo)
    report = report_path.read_text(encoding="utf-8")
    findings = findings_path.read_text(encoding="utf-8")
    tasks = tasks_path.read_text(encoding="utf-8")

    # The method version: the latest one the report links to.
    used = sorted({m.group(1) for url in MD_LINK.findall(report)
                   if (m := METHOD_LINK.match(url)) and m.group(2) == "method"}, key=version_key)
    if not used:
        sys.exit("The report doesn't link to a tagged method version.")
    tag = used[-1]
    version = tag.lstrip("v")
    method = git_show(tag, f"{METHOD_DIR}/method.md")
    rubric = git_show(tag, f"{METHOD_DIR}/rubric.md")

    if len(used) == 1:
        method_note = f"This appendix reproduces the agent task review method as of version {version}, the version this review used."
    else:
        earlier = ", ".join(t.lstrip("v") for t in used[:-1])
        method_note = (f"This review used method versions {earlier} and {version}. This appendix reproduces "
                       f"version {version}, the later of them; its changelog lists what changed.")
    method_note += f" The source is the [{tag} tag]({GITHUB}/agent-ready-docs/tree/{tag}/{METHOD_DIR}) in agent-ready-docs."
    rubric_note = f"This appendix reproduces the rubric as of method version {version}."

    # Severity: the rubric didn't define it before 0.4, though both reports rate findings by it.
    if "| Severity |" in report and section(rubric, "Severity") is None:
        source = next(t for t in method_tags() if section(git_show(t, f"{METHOD_DIR}/rubric.md"), "Severity"))
        severity = section(git_show(source, f"{METHOD_DIR}/rubric.md"), "Severity")
        rubric = rubric.rstrip() + "\n\n" + severity
        rubric_note += (f" Version {version} didn't define severity; the scale was added in version "
                        f"{source.lstrip('v')}, so its Severity section, reproduced from that version, closes this "
                        f"appendix. The report's Main findings section defines the same scale.")

    md = MarkdownIt("commonmark").enable("table").use(anchors_plugin, min_level=1, max_level=6)
    prompts_md = prompts(tasks)
    prompt_ids = re.findall(r'<h[1-6] id="([^"]+)"', md.render(prompts_md))
    linker = Linker(case_repo, case_name, tag, prompt_ids)

    title = re.match(r"# (.*)", report).group(1)
    report_md = linker.rewrite(point_to_prompts(report), "", "case", REVIEW_DIR)
    report_html = render(md, report_md, "")
    parts = [
        "",  # the report, which holds the table of contents, filled in below

        '<section id="method" class="appendix">'
        + render(md, f"# Appendix A. Agent task review method, version {version}\n\n*{method_note}*\n\n"
                 + drop_title(linker.rewrite(method, "method", "method", METHOD_DIR)), "method")
        + "</section>",
        '<section id="rubric" class="appendix">'
        + render(md, f"# Appendix B. Rubric, version {version}\n\n*{rubric_note}*\n\n"
                 + drop_title(linker.rewrite(rubric, "rubric", "method", METHOD_DIR)), "rubric")
        + "</section>",
        '<section id="prompts" class="appendix">'
        + render(md, "# Appendix C. Task prompts\n\n*This appendix reproduces, word for word, what each agent "
                 "was told, from the case study's task file. Each session began with the standard instructions, "
                 "then the task's prompt. The task file also gives each task's success criteria, which the "
                 "agents never saw.*\n\n"
                 + linker.rewrite(prompts_md, "prompts", "case", REVIEW_DIR), "prompts")
        + "</section>",
        '<section id="findings" class="appendix landscape">'
        + render(md, "# Appendix D. Findings log\n\n*This appendix reproduces the case study's findings log, "
                 "the evidence behind each finding in the report.*\n\n"
                 + drop_title(linker.rewrite(findings, "findings", "case", REVIEW_DIR)), "findings")
        + "</section>",
    ]
    # Header and footer: the title on every page but the first; the author and repo on every page.
    author = AUTHOR_LINE.search(report)
    if not author:
        sys.exit("The report has no **Author:** line with a LinkedIn link, which the footer needs.")
    author_name, linkedin = author.groups()
    repo_text = f"github.com/southpaw199/{case_name}"
    footer = f"Author: {author_name} · {repo_text}"
    page_css = PAGE_CSS.replace("{title}", css_string(title)).replace("{footer}", css_string(footer))
    footer_links = [(author_name, linkedin), (repo_text, f"https://{repo_text}")]

    # Table of contents, below the title and author line: the report's ## sections, then the appendices.
    entries = [(id_, title_, False) for id_, title_ in re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', report_html)]
    entries += [(id_, re.search(r"<h1[^>]*>(.*?)</h1>", part).group(1), i == 0)
                for i, (id_, part) in enumerate(re.findall(r'<section id="([^"]+)" class="appendix[^"]*">(.*?)</section>',
                                                           "".join(parts), re.S))]

    def page(numbers):
        parts[0] = f'<section id="top">{report_html.replace("</p>", "</p>" + contents(entries, numbers), 1)}</section>'
        return (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)}</title>'
                f"<style>{page_css}{CSS}</style></head><body>\n" + "\n".join(parts) + "\n</body></html>\n")

    output = (args.output or Path.cwd() / f"{case_name}-report.pdf").expanduser().resolve()
    browser = find_browser(args.browser)
    work = Path(tempfile.mkdtemp(prefix="report-pdf-"))
    try:
        html_file = work / "report.html"
        pdf_file = work / "report.pdf"
        # Chrome can't number the contents itself, so print once to find each entry's page, then
        # again with the numbers, until they stop changing.
        numbers = {}
        for _ in range(3):
            html_file.write_text(page(numbers), encoding="utf-8")
            pdf_file.unlink(missing_ok=True)
            print_pdf(browser, html_file, pdf_file)
            found = page_numbers(pdf_file)
            if numbers and all(numbers.get(e[0]) == found.get(e[0]) for e in entries):
                break
            numbers = found
        else:
            sys.exit("The table of contents' page numbers kept changing between printings.")
        if missing := [e[0] for e in entries if e[0] not in numbers]:
            sys.exit(f"Couldn't find the page for these contents entries: {', '.join(missing)}")
        pages = len(PdfReader(str(pdf_file)).pages)
        if link_footer(pdf_file, footer_links) != 2 * pages:
            sys.exit("Couldn't find the author and repo in every page's footer, so the footer links are incomplete.")
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(pdf_file), output)
        if args.html:
            shutil.copy(html_file, output.with_suffix(".html"))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
