#!/usr/bin/env python3
"""Audit EPUB structure without retaining copyrighted story prose."""

from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import statistics
import sys
from zipfile import ZipFile


class AuditParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.heading = ""
        self._heading_parts: list[str] = []
        self._in_heading = False
        self.words = 0
        self.paragraphs = 0
        self.emphasized_phrases = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "h1":
            self._in_heading = True
            self._heading_parts = []
        elif tag == "p":
            self.paragraphs += 1
        elif tag in {"b", "strong"}:
            self.emphasized_phrases += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1" and self._in_heading:
            candidate = " ".join("".join(self._heading_parts).split())
            if candidate:
                self.heading = candidate
            self._in_heading = False

    def handle_data(self, data: str) -> None:
        if self._in_heading:
            self._heading_parts.append(data)
        self.words += len(re.findall(r"[A-Za-zÀ-ÿ]+(?:['’][A-Za-zÀ-ÿ]+)?", data))


def topic(title: str) -> str:
    value = title.lower()
    groups = [
        ("food-and-health", ("food", "chef", "restaurant", "salad", "doctor", "headache", "bakery", "recipe", "spa")),
        ("travel-and-transport", ("travel", "airport", "bicycle", "driver", "parking", "bus", "train", "taxi", "cruise", "hotel")),
        ("work-money-and-services", ("invoice", "contract", "office", "unemployed", "credit", "lottery", "application", "lender", "merchant")),
        ("family-and-relationships", ("friend", "marriage", "divorced", "neighbor", "siblings", "family", "maid")),
        ("home-and-community", ("house", "break in", "clean", "move", "park", "allotment", "funeral", "evacuation")),
    ]
    return next((name for name, needles in groups if any(needle in value for needle in needles)), "everyday-life-and-culture")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: analyze_story_epub.py /path/to/book.epub")
    epub = Path(sys.argv[1]).resolve()
    records = []
    image_count = 0
    with ZipFile(epub) as archive:
        image_count = sum(name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")) for name in archive.namelist())
        for name in archive.namelist():
            if not re.fullmatch(r"index_split_\d+\.html", name):
                continue
            parser = AuditParser()
            parser.feed(archive.read(name).decode("utf-8", "ignore"))
            match = re.match(r"(\d+)\.\s*(.+)", parser.heading)
            if not match:
                continue
            number = int(match.group(1))
            records.append({
                "number": number, "title": match.group(2), "sourceFile": name,
                "wordCount": parser.words, "paragraphCount": max(1, parser.paragraphs - 1),
                "emphasizedPhraseCount": parser.emphasized_phrases,
                "dialogueFocused": "dialogue" in parser.heading.lower(), "broadTopic": topic(match.group(2)),
                "difficultyBand": "short" if parser.words < 150 else "medium" if parser.words < 250 else "extended",
            })
    records.sort(key=lambda item: item["number"])
    numbers = {item["number"] for item in records}
    audit = {
        "schemaVersion": 1,
        "source": {"filename": epub.name, "epubSha256": hashlib.sha256(epub.read_bytes()).hexdigest(),
                   "declaredTitleCount": 100, "actualNumberedStoryCount": len(records), "embeddedImageCount": image_count},
        "copyrightUse": "Structural analysis only. No source story prose, translations, characters, plots, or dialogue are published.",
        "numberingAnomalies": {"missingWithin1To100": [n for n in range(1, 101) if n not in numbers],
                               "additionalAfter100": [n for n in sorted(numbers) if n > 100]},
        "analysis": {"minimumWords": min(item["wordCount"] for item in records),
                     "medianWords": statistics.median(item["wordCount"] for item in records),
                     "maximumWords": max(item["wordCount"] for item in records),
                     "dialogueFocusedCount": sum(item["dialogueFocused"] for item in records),
                     "progression": "Later entries are generally longer and structurally more complex; highlighted phrases serve as contextual vocabulary."},
        "assets": {"extractedOrReused": 0, "reason": "The EPUB contains a cover image but no story-specific illustrations."},
        "stories": records,
    }
    output = Path(__file__).resolve().parents[1] / "storie" / "source-audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Audited {len(records)} numbered story entries into {output}.")


if __name__ == "__main__":
    main()
