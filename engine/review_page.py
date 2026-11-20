#!/usr/bin/env python3
"""Build the review page for a finished short.

  python3 engine/review_page.py <project dir> [--title "..."] [--approved-by "..."] [--style styles/default.md]

Reads   <project>/work/{edl,verify,cut.words}.json, <project>/out/final.{mp4,json}, the raw recording
Writes  <project>/review/index.html plus copies of final.mp4 and raw.mp4 beside it, so the folder
        opens in any browser as-is and can be published as one unit.
"""
import argparse
import json
import shutil
from pathlib import Path

from common import ENGINE, read_json


def build(project, title=None, approved_by="not yet approved", style="styles/default.md"):
    project = Path(project)
    work, out, review = project / "work", project / "out", project / "review"
    review.mkdir(exist_ok=True)
    edl, verify = read_json(work / "edl.json"), read_json(work / "verify.json")
    cutw = read_json(work / "cut.words.json")
    data = {
        "project": project.name,
        "title": title or project.name.replace("-", " ").title(),
        "approved_by": approved_by, "style": Path(style).name, "backend": cutw["backend"],
        "edl": {k: edl[k] for k in ("duration_src", "duration_out", "keep", "removed")},
        "verify": {"passed": verify["passed"], "checks": verify["checks"]},
        "words": [{"w": w["w"], "start": w["start"]} for w in cutw["words"]],
        "spec": read_json(out / "final.json"),
    }
    page_title = project.name.replace("-", " ").title() + " Review"
    html = (ENGINE / "review_template.html").read_text()
    html = html.replace("__TITLE__", page_title).replace("/*DATA*/", json.dumps(data).replace("</", "<\\/"))
    (review / "index.html").write_text(html)
    shutil.copyfile(out / "final.mp4", review / "final.mp4")
    shutil.copyfile(edl["source"] if Path(edl["source"]).exists() else project / edl["source"], review / "raw.mp4")
    return review / "index.html"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--title")
    ap.add_argument("--approved-by", default="not yet approved")
    ap.add_argument("--style", default="styles/default.md")
    a = ap.parse_args()
    print("review page ->", build(a.project, a.title, a.approved_by, a.style))
