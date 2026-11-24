#!/usr/bin/env python3
"""Validate RoLang static discovery, hashes, lesson JSON, and asset references."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


HEX_HASH = re.compile(r"[0-9a-f]{64}")
SAFE_PATH = re.compile(r"^[A-Za-z0-9._/-]+$")


def fail(message: str) -> None:
    raise ValueError(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        raise ValueError(f"Invalid JSON: {path}") from error
    if not isinstance(value, dict):
        fail(f"Expected an object: {path}")
    return value


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_relative(value: str) -> Path:
    path = Path(value)
    if not value or not SAFE_PATH.fullmatch(value) or path.is_absolute() or ".." in path.parts:
        fail(f"Unsafe relative path: {value!r}")
    return path


def verify_hash(root: Path, base: Path, reference: dict[str, Any]) -> Path:
    relative = safe_relative(reference.get("path") or reference.get("index", ""))
    path = base / relative
    if not path.is_file() or root not in path.resolve().parents:
        fail(f"Missing referenced file: {path}")
    expected = reference.get("sha256", "")
    if not HEX_HASH.fullmatch(expected) or digest(path) != expected:
        fail(f"Hash mismatch: {path}")
    return path


def lesson_text(value: Any, location: str) -> None:
    if not isinstance(value, dict):
        fail(f"Lesson text must be an object: {location}")
    for field in ("sourceLanguage", "sourceText", "id"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            fail(f"Missing {field}: {location}")
    if value["sourceLanguage"] not in {"en", "fil", "mixed"}:
        fail(f"Invalid sourceLanguage: {location}")
    if value["sourceLanguage"] == "fil" and value.get("tagalog") != value["sourceText"]:
        fail(f"Filipino source must retain TTS text: {location}")


def validate_sections(document: dict[str, Any], course_dir: Path, known_assets: set[str], location: str) -> set[str]:
    sections = document.get("sections")
    if not isinstance(sections, list) or not sections:
        fail(f"No sections: {location}")
    used: set[str] = set()
    for section_index, section in enumerate(sections):
        where = f"{location}.sections[{section_index}]"
        if section.get("type") not in {"OVERVIEW", "VOCABULARY", "DIALOGUE", "ACTIVITY", "GRAMMAR", "PRACTICE", "CONTENT"}:
            fail(f"Invalid section type: {where}")
        lesson_text(section.get("title"), f"{where}.title")
        blocks = section.get("blocks")
        if not isinstance(blocks, list) or not blocks:
            fail(f"Empty section: {where}")
        for block_index, block in enumerate(blocks):
            block_where = f"{where}.blocks[{block_index}]"
            if block.get("type") == "text":
                lesson_text(block.get("text"), block_where)
            elif block.get("type") == "table":
                rows = block.get("rows")
                if not isinstance(rows, list) or not rows:
                    fail(f"Empty table: {block_where}")
                for row_index, row in enumerate(rows):
                    cells = row.get("cells")
                    if not isinstance(cells, list) or not cells:
                        fail(f"Empty row: {block_where}.rows[{row_index}]")
                    for cell_index, cell in enumerate(cells):
                        lesson_text(cell, f"{block_where}.rows[{row_index}].cells[{cell_index}]")
            elif block.get("type") == "image":
                asset = block.get("path", "")
                safe_relative(asset)
                if asset not in known_assets or not (course_dir / asset).is_file():
                    fail(f"Missing image: {block_where} -> {asset}")
                used.add(asset)
            else:
                fail(f"Unknown block type: {block_where}")
    declared = document.get("assets")
    if not isinstance(declared, list) or any(asset not in known_assets for asset in declared):
        fail(f"Invalid asset list: {location}")
    if not used.issubset(set(declared)):
        fail(f"Image blocks are absent from document assets: {location}")
    return used


def validate(root: Path) -> tuple[int, int, int]:
    root = root.resolve()
    manifest = load(root / "manifest.json")
    if manifest.get("schemaVersion") != 1:
        fail("Unsupported manifest schema")
    expected_base = "https://raw.githubusercontent.com/HamzahSk/rolang-server/data/"
    if manifest.get("contentBase") != expected_base:
        fail("Manifest contentBase must use the data branch")
    lesson_index_path = verify_hash(root, root, manifest.get("lessons", {}))
    lesson_index = load(lesson_index_path)
    courses = lesson_index.get("courses")
    if not isinstance(courses, list) or len(courses) != 1:
        fail("Exactly one course is required")
    course_path = verify_hash(root, lesson_index_path.parent, courses[0])
    course = load(course_path)
    course_dir = course_path.parent
    if course.get("languagePair") != {"reference": "id", "target": "fil"}:
        fail("Course must be Indonesian -> Filipino")
    asset_index_path = verify_hash(root, course_dir, course.get("assetIndex", {}))
    audit_path = verify_hash(root, course_dir, course.get("sourceAudit", {}))
    asset_index = load(asset_index_path)
    inventory = asset_index.get("assets")
    if not isinstance(inventory, list) or asset_index.get("count") != len(inventory):
        fail("Invalid asset inventory")
    known_assets: set[str] = set()
    for reference in inventory:
        path = verify_hash(root, course_dir, reference)
        relative = path.relative_to(course_dir).as_posix()
        if relative in known_assets:
            fail(f"Duplicate asset: {relative}")
        known_assets.add(relative)
        if reference.get("bytes") != path.stat().st_size or reference.get("mediaType") != "image/jpeg":
            fail(f"Invalid asset metadata: {relative}")

    units = course.get("units")
    lessons = course.get("lessons")
    if not isinstance(units, list) or len(units) != 8:
        fail("Expected exactly 8 units")
    if not isinstance(lessons, list) or len(lessons) != 24:
        fail("Expected exactly 24 lessons")
    lesson_ids = [reference.get("id") for reference in lessons]
    if len(set(lesson_ids)) != 24 or [reference.get("order") for reference in lessons] != list(range(1, 25)):
        fail("Lesson ids/orders must be unique and contiguous")

    referenced_assets: set[str] = set()
    for reference in units:
        unit_path = verify_hash(root, course_dir, reference)
        unit = load(unit_path)
        if unit.get("id") != reference.get("id") or unit.get("courseId") != course.get("id"):
            fail(f"Unit metadata mismatch: {unit_path}")
        referenced_assets |= validate_sections(unit, course_dir, known_assets, unit_path.as_posix())
    section_types: Counter[str] = Counter()
    for reference in lessons:
        lesson_path = verify_hash(root, course_dir, reference)
        lesson = load(lesson_path)
        if lesson.get("id") != reference.get("id") or lesson.get("order") != reference.get("order"):
            fail(f"Lesson metadata mismatch: {lesson_path}")
        objectives = lesson.get("objectives")
        if not isinstance(objectives, list) or not objectives:
            fail(f"Lesson has no extracted objectives: {lesson_path}")
        for index, objective in enumerate(objectives):
            lesson_text(objective, f"{lesson_path}.objectives[{index}]")
        referenced_assets |= validate_sections(lesson, course_dir, known_assets, lesson_path.as_posix())
        section_types.update(section["type"] for section in lesson["sections"])
    for required in ("VOCABULARY", "DIALOGUE", "ACTIVITY", "GRAMMAR", "PRACTICE"):
        if section_types[required] < 24:
            fail(f"Every lesson must include {required}")

    audit = load(audit_path)
    if audit.get("lessonCount") != 24 or audit.get("unitCount") != 8 or audit.get("assetCount") != len(known_assets):
        fail("Source audit totals do not match indexes")
    documents = audit.get("documents")
    if not isinstance(documents, list) or audit.get("documentCount") != 36 or len(documents) != 36:
        fail("Expected audit entries for 4 front-matter, 8 unit, and 24 lesson XHTML files")
    if any(not HEX_HASH.fullmatch(document.get("sha256", "")) for document in documents):
        fail("Invalid XHTML source hash in audit")
    if any(document.get("sourceWordCoverage", 0) < 0.97 for document in documents):
        fail("An XHTML source has less than 97% extracted word coverage")
    if manifest.get("stories") != {"path": "storie/", "status": "reserved"}:
        fail("Stories must remain reserved")
    if not (root / "storie").is_dir():
        fail("Missing storie/ reservation directory")
    json_count = len(list(root.rglob("*.json")))
    return len(lessons), len(known_assets), json_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    lessons, assets, json_files = validate(args.root)
    print(f"Validated {lessons} lessons, {assets} images, and {json_files} JSON files.")


if __name__ == "__main__":
    main()
