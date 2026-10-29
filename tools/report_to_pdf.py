#!/usr/bin/env python3
"""Build a PDF of a case study's agent task review report.

The PDF opens with a cover, filled from the case study's report-cover.yaml.
Then come the report and four appendices: the method and the rubric,
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
import base64
import datetime
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pypdfium2 as pdfium
import yaml
from markdown_it import MarkdownIt
from mdit_py_plugins.anchors import anchors_plugin
from pypdf import PdfReader, PdfWriter
from pypdf.annotations import Link
from pypdf.generic import BooleanObject, DictionaryObject, NameObject, StreamObject

METHOD_REPO = Path(__file__).resolve().parents[1]
METHOD_DIR = "methods/agent-task-review"
REVIEW_DIR = "reviews/agent-task-review"
COVER_FILE = "report-cover.yaml"
FONTS = Path(__file__).resolve().parent / "fonts"
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
h1, h2, h3, .toc-title { color: #9A5B00; }
h2, h3, h4 { break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 0.6em 0 1em; font-size: 8.8pt; break-inside: avoid; }
th, td { border: 1px solid #d0d7de; padding: 4px 6px; vertical-align: top; text-align: left; overflow-wrap: break-word; }
td:first-child { white-space: nowrap; }
td ul, td ol { margin: 0; padding-left: 1.2em; }
td li + li, td li ul { margin-top: 0.3em; }
th { background: #FBF3E6; color: #9A5B00; }
td.pass { background: #E3F4EA; color: #1E6B3F; }
td.issues { background: #FDF1DC; color: #7A4A00; }
td.hints { background: #E6F0FA; color: #1F4E79; }
td.fail { background: #FBE4E4; color: #8A1F1F; }
.summary-box { background: #F6F7F9; border: 1px solid #D5DBE1; border-radius: 8px; padding: 16px 18px; margin: 1em 0; }
.summary-box > p:first-child { margin-top: 0; }
.summary-box > p:last-child { margin-bottom: 0; }
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
.toc-title { font-size: 14pt; font-weight: bold; border-bottom: 1px solid #d0d7de; padding-bottom: 0.2em; margin: 1.6em 0 0; }
.toc ul { list-style: none; padding: 0; margin: 0.5em 0 0; }
.toc li { margin: 0.2em 0; }
.toc li.gap { margin-top: 0.7em; }
.toc a { display: flex; color: inherit; }
.toc .leader { flex: 1; overflow: hidden; white-space: nowrap; margin: 0 0.4em; color: #8c959f; }
.toc .leader::after { content: "LEADER"; }
""".replace("LEADER", " ." * 200)  # periods print as dots; a dotted border can print as dashes
OUTCOMES = {"Pass": "pass", "Pass with issues": "issues", "With issues": "issues",
            "Pass with hints": "hints", "Fail": "fail"}  # outcome -> its cell's class
OUTCOME_CELL = re.compile(r"<td([^>]*)>(<strong>)?([^<]+)(</strong>)?</td>")
FONT_FACES = [("IBM Plex Sans", 400, "IBMPlexSans-Regular"), ("IBM Plex Sans", 600, "IBMPlexSans-SemiBold"),
              ("IBM Plex Sans", 700, "IBMPlexSans-Bold"), ("IBM Plex Mono", 400, "IBMPlexMono-Regular"),
              ("IBM Plex Mono", 600, "IBMPlexMono-SemiBold")]

# The cover is printed on its own, with no margins, and put in front of the report afterwards,
# so it has no header, footer, or page number, and the report's page numbering starts after it.
COVER_CSS = """
@page { size: letter; margin: 0; }
html, body { margin: 0; background: #FFFFFF; }
.cover { width: 8.5in; height: 11in; box-sizing: border-box; display: flex; flex-direction: column;
         font-family: "IBM Plex Sans", sans-serif; color: #141A21; background: #FFFFFF; }
.band { height: 14px; flex: none; background: #F2A93B; }
.inner { flex: 1; box-sizing: border-box; padding: 72px 72px 0.6in; display: flex; flex-direction: column; }
/* 32 px between the main blocks and at least 16 px above the footer, a little under the design's 40 px,
   so that the covers fit on a Letter page. */
.inner > :not(:first-child) { margin-top: 32px; }
.steps { margin-bottom: 16px; }
.head { display: flex; flex-direction: column; gap: 20px; }
.label { font-family: "IBM Plex Mono", monospace; font-size: 15px; font-weight: 600; letter-spacing: 0.06em;
         text-transform: uppercase; color: #9A5B00; }
h1 { margin: 0; font-size: 52px; line-height: 1.05; font-weight: 700; letter-spacing: -0.02em; text-wrap: balance; }
.question { font-size: 26px; line-height: 1.3; color: #3B4652; }
.stats { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }
.stat { border: 1.5px solid #D5DBE1; border-radius: 12px; padding: 24px; display: flex; flex-direction: column; gap: 8px; }
.stat .n { font-family: "IBM Plex Mono", monospace; font-size: 52px; font-weight: 600; line-height: 1; color: #9A5B00; }
.stat .t { font-size: 16px; line-height: 1.45; color: #2A333D; }
.details { border-top: 1.5px solid #D5DBE1; }
.row { display: grid; grid-template-columns: 160px minmax(0, 1fr); gap: 16px; padding: 14px 0;
       border-bottom: 1px solid #E4E8EC; font-size: 16px; line-height: 1.45; }
.row .k { color: #5B6672; font-weight: 600; }
.steps { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; font-family: "IBM Plex Mono", monospace;
         font-size: 13px; color: #2A333D; }
.step { border: 1.5px solid #B8C1CA; border-radius: 8px; padding: 8px 12px; white-space: nowrap; }
.arrow { color: #5B6672; }
.inner > .foot { margin-top: auto; display: flex; flex-direction: column; gap: 8px; border-top: 1.5px solid #D5DBE1; padding-top: 20px; }
.foot .name { font-size: 20px; font-weight: 600; }
.foot .links { font-family: "IBM Plex Mono", monospace; font-size: 13px; color: #3B4652; }
.foot a { color: inherit; text-decoration: none; }
.foot .copy { font-size: 12px; color: #5B6672; }
"""
COVER_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title><style>{fonts}{css}</style></head><body>
<div class="cover">
  <div class="band"></div>
  <div class="inner">
    <div class="head">
      <div class="label">agent-ready-docs · Case study {number}</div>
      <h1>{title}</h1>
      <div class="question">{question}</div>
    </div>
    <div class="stats">{stats}</div>
    <div class="details">{details}</div>
    <div class="steps">{steps}</div>
    <div class="foot">
      <div class="name">{author}</div>
      <div class="links"><a href="{linkedin}">{linkedin_text}</a> · <a href="https://{repo}">{repo}</a></div>
      <div class="copy">{copyright}</div>
    </div>
  </div>
</div>
</body></html>
"""
COPYRIGHT_LINE = re.compile(r"^Copyright © .+$", re.M)
XMP = """<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:pdf="http://ns.adobe.com/pdf/1.3/" xmlns:xmpRights="http://ns.adobe.com/xap/1.0/rights/">
   <dc:title><rdf:Alt><rdf:li xml:lang="x-default">{title}</rdf:li></rdf:Alt></dc:title>
   <dc:creator><rdf:Seq><rdf:li>{author}</rdf:li></rdf:Seq></dc:creator>
   <dc:description><rdf:Alt><rdf:li xml:lang="x-default">{subject}</rdf:li></rdf:Alt></dc:description>
   <dc:rights><rdf:Alt><rdf:li xml:lang="x-default">{copyright}</rdf:li></rdf:Alt></dc:rights>
   <pdf:Keywords>{keywords}</pdf:Keywords>
   <xmpRights:Marked>True</xmpRights:Marked>
   <xmpRights:WebStatement>{url}</xmpRights:WebStatement>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>"""
PROMPTS_POINTER ="[Appendix C](#prompts) gives each task's full prompt, word for word, as the agents received it."


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


def read_cover(path, release_date):
    """Read the cover's data file, stopping if it's missing or any field is missing or empty.

    release_date: a date to show as the report release instead of the file's, or None."""
    if not path.exists():
        sys.exit(f"No cover data at {path}. See tools/README.md for the fields it needs.")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        sys.exit(f"{path} isn't valid YAML: {e}")

    def text(value, field):
        if isinstance(value, bool) or not isinstance(value, (str, int, float)) or not str(value).strip():
            sys.exit(f"{path}: {field} is missing or empty.")
        return str(value).strip()

    def items(value, field):
        if not isinstance(value, list) or not value:
            sys.exit(f"{path}: {field} is missing or empty.")
        return value

    def pairs(field, keys):
        out = []
        for i, item in enumerate(items(data.get(field), field), 1):
            if not isinstance(item, dict):
                sys.exit(f"{path}: {field} item {i} needs {' and '.join(keys)}.")
            out.append(tuple(text(item.get(k), f"{field} item {i}'s {k}") for k in keys))
        return out

    if not isinstance(data, dict):
        sys.exit(f"{path} should hold the cover's fields. See tools/README.md.")
    cover = {k: text(data.get(k), k) for k in ("case_study_number", "title", "question", "repo")}
    cover["stats"] = pairs("stats", ("number", "text"))
    cover["details"] = pairs("details", ("label", "value"))
    cover["method_steps"] = [text(s, f"method_steps item {i}")
                             for i, s in enumerate(items(data.get("method_steps"), "method_steps"), 1)]
    if release_date:
        rows = [i for i, (label, _) in enumerate(cover["details"]) if label == "Report release"]
        if not rows:
            sys.exit(f"{path} has no \"Report release\" detail for --release-date to replace.")
        cover["details"][rows[0]] = ("Report release", f"{release_date:%B} {release_date.day}, {release_date.year}")
    return cover


def release_date(value):
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} isn't a date like 2026-10-29")


def font_faces():
    """The cover's fonts, as data in the CSS, so the browser embeds these files whatever is installed."""
    faces = []
    for family, weight, name in FONT_FACES:
        data = base64.b64encode((FONTS / f"{name}.woff2").read_bytes()).decode("ascii")
        faces.append(f'@font-face {{ font-family: "{family}"; font-weight: {weight}; '
                     f'src: url(data:font/woff2;base64,{data}) format("woff2"); }}')
    return "\n".join(faces)


def cover_page(cover, author, linkedin, copyright):
    e = lambda s: html.escape(s, quote=True)
    return COVER_HTML.format(
        fonts=font_faces(), css=COVER_CSS, title=e(cover["title"]), number=e(cover["case_study_number"]),
        question=e(cover["question"]),
        stats="".join(f'<div class="stat"><div class="n">{e(n)}</div><div class="t">{e(t)}</div></div>'
                      for n, t in cover["stats"]),
        details="".join(f'<div class="row"><div class="k">{e(k)}</div><div>{e(v)}</div></div>'
                        for k, v in cover["details"]),
        steps='<div class="arrow">→</div>'.join(f'<div class="step">{e(s)}</div>' for s in cover["method_steps"]),
        author=e(author), linkedin=e(linkedin),
        linkedin_text=e(re.sub(r"^https://(www\.)?", "", linkedin).rstrip("/")),
        repo=e(cover["repo"]), copyright=e(copyright))


def add_cover(pdf_file, cover_file):
    """Put the cover in front of the report. Viewers show the cover as "Cover" and number the
    pages after it from 1, as the footers do."""
    writer = PdfWriter(clone_from=PdfReader(str(pdf_file)))
    writer.insert_page(PdfReader(str(cover_file)).pages[0], 0)
    writer.set_page_label(0, 0, prefix="Cover")
    writer.set_page_label(1, len(writer.pages) - 1, style="/D", start=1)
    with open(pdf_file, "wb") as f:
        writer.write(f)


def tint_outcomes(text):
    """Give each table cell whose whole content is an outcome, such as "Pass", its outcome's class."""
    def tint(m):
        cls = OUTCOMES.get(m.group(3).strip())
        if not cls or bool(m.group(2)) != bool(m.group(4)):
            return m.group(0)
        return f'<td class="{cls}"{m.group(1)}>' + m.group(0)[len(f"<td{m.group(1)}>"):]
    return OUTCOME_CELL.sub(tint, text)


def box_summary(text):
    """Put a box around the Summary's opening paragraphs, up to its first table."""
    m = re.search(r'(<h2 id="summary">.*?</h2>\n)(.*?)(?=<table|<h[1-6])', text, re.S)
    if not m or not m.group(2).strip():
        sys.exit("The report's Summary has no opening paragraphs to box.")
    return text[:m.start(2)] + f'<div class="summary-box">\n{m.group(2)}</div>\n' + text[m.end(2):]


def contents(entries, pages):
    """The table of contents. entries: (id, title, starts_group) for each entry;
    pages: id -> page number, empty on the first pass."""
    items = "".join(f'<li class="{"gap" if gap else ""}"><a href="#{id_}"><span>{title}</span>'
                    f'<span class="leader"></span><span>{pages.get(id_, "")}</span></a></li>'
                    for id_, title, gap in entries)
    # Not an <h2>, so the contents don't get a bookmark of their own.
    return f'<nav class="toc"><p class="toc-title">Contents</p><ul>{items}</ul></nav>\n'


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


def add_metadata(pdf_file, title, author, subject, keywords, copyright, copyright_url):
    """Set the document properties, in both the PDF's info dictionary and its XMP metadata,
    which is where viewers such as Acrobat look for the copyright. Also open the PDF with
    the bookmarks showing and its title, not its file name, in the window."""
    writer = PdfWriter(clone_from=PdfReader(str(pdf_file)))
    writer.add_metadata({"/Title": title, "/Author": author, "/Subject": subject, "/Keywords": keywords,
                         "/Copyright": copyright, "/Creator": "report_to_pdf.py, agent-ready-docs"})
    esc = lambda s: html.escape(s, quote=False)
    xmp = StreamObject()
    xmp.set_data(XMP.format(title=esc(title), author=esc(author), subject=esc(subject), keywords=esc(keywords),
                            copyright=esc(copyright), url=esc(copyright_url)).encode("utf-8"))
    xmp.update({NameObject("/Type"): NameObject("/Metadata"), NameObject("/Subtype"): NameObject("/XML")})
    root = writer._root_object
    root[NameObject("/Metadata")] = writer._add_object(xmp)
    root[NameObject("/PageMode")] = NameObject("/UseOutlines")
    root[NameObject("/ViewerPreferences")] = DictionaryObject({NameObject("/DisplayDocTitle"): BooleanObject(True)})
    with open(pdf_file, "wb") as f:
        writer.write(f)


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
           "--generate-pdf-document-outline",  # bookmarks, from the headings
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
    parser.add_argument("--release-date", type=release_date, metavar="YYYY-MM-DD",
                        help=f"the report release date for the cover, instead of the one in {COVER_FILE}")
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
    cover_path = case_repo / REVIEW_DIR / COVER_FILE
    cover = read_cover(cover_path, args.release_date)

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
    if cover["title"] != title:
        sys.exit(f"{cover_path}: title {cover['title']!r} doesn't match the report's title, {title!r}.")
    report_md = linker.rewrite(point_to_prompts(report), "", "case", REVIEW_DIR)
    report_html = box_summary(tint_outcomes(render(md, report_md, "")))
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
    copyright_file = case_repo / "COPYRIGHT.md"
    copyright = COPYRIGHT_LINE.search(copyright_file.read_text(encoding="utf-8")) if copyright_file.exists() else None
    if not copyright:
        sys.exit(f"No \"Copyright © ...\" line in {copyright_file}, which the PDF's metadata needs.")

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
        cover_html = work / "cover.html"
        cover_pdf = work / "cover.pdf"
        cover_html.write_text(cover_page(cover, author_name, linkedin, copyright.group(0).removeprefix("Copyright ")),
                              encoding="utf-8")
        print_pdf(browser, cover_html, cover_pdf)
        if len(PdfReader(str(cover_pdf)).pages) != 1:
            sys.exit(f"The cover runs past one page; shorten the text in {cover_path}.")
        add_cover(pdf_file, cover_pdf)
        add_metadata(pdf_file, title, author_name,
                     "An agent task review report, with the method, rubric, task prompts, and findings log as appendices.",
                     "AI coding agents, documentation, agent task review, agent-ready-docs",
                     copyright.group(0), f"{GITHUB}/{case_name}/blob/main/COPYRIGHT.md")
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(pdf_file), output)
        if args.html:
            shutil.copy(html_file, output.with_suffix(".html"))
            shutil.copy(cover_html, output.with_name(output.stem + "-cover.html"))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
