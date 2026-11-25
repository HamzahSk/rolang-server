#!/usr/bin/env python3
"""Validate RoLang static discovery, hashes, lesson JSON, and asset references."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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


def lesson_rows(value: Any, location: str) -> None:
    if not isinstance(value, list) or not value:
        fail(f"Empty rows: {location}")
    for row_index, row in enumerate(value):
        cells = row.get("cells") if isinstance(row, dict) else None
        if not isinstance(cells, list) or not cells:
            fail(f"Empty row: {location}[{row_index}]")
        for cell_index, cell in enumerate(cells):
            lesson_text(cell, f"{location}[{row_index}].cells[{cell_index}]")


def validate_sections(document: dict[str, Any], course_dir: Path, known_assets: set[str], location: str) -> set[str]:
    sections = document.get("sections")
    if not isinstance(sections, list) or not sections:
        fail(f"No sections: {location}")
    used: set[str] = set()
    for section_index, section in enumerate(sections):
        where = f"{location}.sections[{section_index}]"
        section_type = section.get("type")
        if section_type not in {
            "INTRODUCTION", "LEARNING_MATERIAL", "VOCABULARY", "EXAMPLES", "DIALOGUE", "EXERCISES", "SUMMARY",
            "OVERVIEW", "ACTIVITY", "GRAMMAR", "PRACTICE", "CONTENT",
        }:
            fail(f"Invalid section type: {where}")
        lesson_text(section.get("title"), f"{where}.title")
        blocks = section.get("blocks")
        if not isinstance(blocks, list) or not blocks:
            fail(f"Empty section: {where}")
        for block_index, block in enumerate(blocks):
            block_where = f"{where}.blocks[{block_index}]"
            if block_index > 0 and block == blocks[block_index - 1]:
                fail(f"Adjacent duplicate block: {block_where}")
            if "title" in block:
                lesson_text(block["title"], f"{block_where}.title")
            if block.get("type") == "text":
                lesson_text(block.get("text"), block_where)
            elif block.get("type") == "table":
                lesson_rows(block.get("rows"), f"{block_where}.rows")
            elif block.get("type") == "image":
                asset = block.get("path", "")
                safe_relative(asset)
                if asset not in known_assets or not (course_dir / asset).is_file():
                    fail(f"Missing image: {block_where} -> {asset}")
                used.add(asset)
            elif block.get("type") == "list":
                items = block.get("items")
                if not isinstance(items, list) or not items:
                    fail(f"Empty list: {block_where}")
                for item_index, item in enumerate(items):
                    lesson_text(item, f"{block_where}.items[{item_index}]")
            elif block.get("type") == "vocabulary":
                if section_type != "VOCABULARY":
                    fail(f"Vocabulary block outside vocabulary section: {block_where}")
                entries = block.get("entries")
                if not isinstance(entries, list) or not entries:
                    fail(f"Empty vocabulary group: {block_where}")
                for entry_index, entry in enumerate(entries):
                    lesson_text(entry.get("term"), f"{block_where}.entries[{entry_index}].term")
                    lesson_text(entry.get("meaning"), f"{block_where}.entries[{entry_index}].meaning")
            elif block.get("type") == "dialogue":
                if section_type not in {"DIALOGUE", "EXERCISES"}:
                    fail(f"Dialogue block in unrelated section: {block_where}")
                turns = block.get("turns")
                if not isinstance(turns, list) or not turns:
                    fail(f"Empty dialogue: {block_where}")
                for turn_index, turn in enumerate(turns):
                    if not isinstance(turn.get("speaker"), str) or not turn["speaker"].strip():
                        fail(f"Dialogue turn has no speaker: {block_where}.turns[{turn_index}]")
                    lesson_text(turn.get("speakerText"), f"{block_where}.turns[{turn_index}].speakerText")
                    lesson_text(turn.get("text"), f"{block_where}.turns[{turn_index}].text")
            elif block.get("type") == "example":
                if section_type != "EXAMPLES":
                    fail(f"Example block outside examples section: {block_where}")
                items = block.get("items")
                rows = block.get("rows")
                if isinstance(items, list) and items:
                    for item_index, item in enumerate(items):
                        lesson_text(item, f"{block_where}.items[{item_index}]")
                elif rows:
                    lesson_rows(rows, f"{block_where}.rows")
                else:
                    fail(f"Empty example: {block_where}")
            elif block.get("type") == "exercise":
                if section_type != "EXERCISES":
                    fail(f"Exercise block outside exercise section: {block_where}")
                if block.get("role") not in {"instruction", "question", "answer", "content", "worksheet"}:
                    fail(f"Invalid exercise role: {block_where}")
                if block.get("role") == "worksheet":
                    lesson_rows(block.get("rows"), f"{block_where}.rows")
                else:
                    lesson_text(block.get("text"), block_where)
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
    if not isinstance(courses, list) or not courses:
        fail("At least one course is required")
    course_ids = [reference.get("id") for reference in courses]
    if len(set(course_ids)) != len(courses):
        fail("Course ids must be unique")
    if [reference.get("order", index + 1) for index, reference in enumerate(courses)] != list(range(1, len(courses) + 1)):
        fail("Course order must be contiguous")

    total_lessons = 0
    total_assets = 0
    global_lesson_ids: set[str] = set()
    for course_reference in courses:
        course_path = verify_hash(root, lesson_index_path.parent, course_reference)
        course = load(course_path)
        course_dir = course_path.parent
        course_id = course.get("id")
        if course_id != course_reference.get("id"):
            fail(f"Course metadata mismatch: {course_path}")
        if course.get("languagePair") != {"reference": "id", "target": "fil"}:
            fail(f"Course must be Indonesian -> Filipino: {course_path}")

        asset_index_path = verify_hash(root, course_dir, course.get("assetIndex", {}))
        audit_path = verify_hash(root, course_dir, course.get("sourceAudit", {}))
        asset_index = load(asset_index_path)
        inventory = asset_index.get("assets")
        if not isinstance(inventory, list) or asset_index.get("count") != len(inventory):
            fail(f"Invalid asset inventory: {asset_index_path}")
        known_assets: set[str] = set()
        for reference in inventory:
            path = verify_hash(root, course_dir, reference)
            relative = path.relative_to(course_dir).as_posix()
            if relative in known_assets:
                fail(f"Duplicate asset: {relative}")
            known_assets.add(relative)
            if reference.get("bytes") != path.stat().st_size or reference.get("mediaType") != "image/jpeg":
                fail(f"Invalid asset metadata: {relative}")
        cover = course.get("cover")
        if cover and (cover not in known_assets or not (course_dir / safe_relative(cover)).is_file()):
            fail(f"Invalid course cover: {cover}")

        units = course.get("units")
        lessons = course.get("lessons")
        if not isinstance(units, list) or not units:
            fail(f"Course has no units: {course_path}")
        if not isinstance(lessons, list) or not lessons:
            fail(f"Course has no lessons: {course_path}")
        if course_reference.get("lessonCount", len(lessons)) != len(lessons):
            fail(f"Course lesson count mismatch: {course_path}")
        if course_reference.get("unitCount", len(units)) != len(units):
            fail(f"Course unit count mismatch: {course_path}")
        lesson_ids = [reference.get("id") for reference in lessons]
        if len(set(lesson_ids)) != len(lessons) or [reference.get("order") for reference in lessons] != list(range(1, len(lessons) + 1)):
            fail(f"Lesson ids/orders must be unique and contiguous: {course_path}")
        if global_lesson_ids.intersection(lesson_ids):
            fail("Lesson ids must be unique across courses")
        global_lesson_ids.update(lesson_ids)

        unit_ids = [reference.get("id") for reference in units]
        if len(set(unit_ids)) != len(units):
            fail(f"Duplicate unit id: {course_path}")
        unit_lesson_ids: list[str] = []
        referenced_assets: set[str] = set()
        for reference in units:
            members = reference.get("lessons")
            if not isinstance(members, list) or not members:
                fail(f"Unit has no lesson membership: {reference.get('id')}")
            unit_lesson_ids.extend(members)
            unit_path = verify_hash(root, course_dir, reference)
            unit = load(unit_path)
            if unit.get("id") != reference.get("id") or unit.get("courseId") != course_id:
                fail(f"Unit metadata mismatch: {unit_path}")
            referenced_assets |= validate_sections(unit, course_dir, known_assets, unit_path.as_posix())
        if len(unit_lesson_ids) != len(set(unit_lesson_ids)) or set(unit_lesson_ids) != set(lesson_ids):
            fail(f"Unit membership must cover each course lesson exactly once: {course_path}")

        required_types = course.get("requiredSectionTypes", [
            "INTRODUCTION", "VOCABULARY", "LEARNING_MATERIAL", "EXAMPLES", "EXERCISES",
        ])
        if not isinstance(required_types, list) or not required_types:
            fail(f"Invalid required section types: {course_path}")
        for reference in lessons:
            if reference.get("unitId") not in unit_ids:
                fail(f"Lesson references an unknown unit: {reference.get('id')}")
            lesson_path = verify_hash(root, course_dir, reference)
            lesson = load(lesson_path)
            if (lesson.get("id") != reference.get("id") or lesson.get("order") != reference.get("order")
                    or lesson.get("courseId") != course_id or lesson.get("unitId") != reference.get("unitId")):
                fail(f"Lesson metadata mismatch: {lesson_path}")
            if lesson.get("structureVersion") != 2:
                fail(f"Lesson is not semantically structured: {lesson_path}")
            content_audit = lesson.get("contentAudit")
            if not isinstance(content_audit, dict) or content_audit.get("sourceTextItemsAfter", 0) <= 0:
                fail(f"Lesson has no structure audit: {lesson_path}")
            objectives = lesson.get("objectives")
            if not isinstance(objectives, list) or not objectives:
                fail(f"Lesson has no extracted objectives: {lesson_path}")
            for index, objective in enumerate(objectives):
                lesson_text(objective, f"{lesson_path}.objectives[{index}]")
            referenced_assets |= validate_sections(lesson, course_dir, known_assets, lesson_path.as_posix())
            present_types = {section["type"] for section in lesson["sections"]}
            missing_types = set(required_types) - present_types
            if missing_types:
                fail(f"Lesson is missing sections {sorted(missing_types)}: {lesson_path}")

        audit = load(audit_path)
        if (audit.get("lessonCount") != len(lessons) or audit.get("unitCount") != len(units)
                or audit.get("assetCount") != len(known_assets)):
            fail(f"Source audit totals do not match indexes: {audit_path}")
        source = audit.get("source")
        if not isinstance(source, dict):
            fail(f"Source audit has no source metadata: {audit_path}")
        if source.get("epubSha256"):
            documents = audit.get("documents")
            if not isinstance(documents, list) or audit.get("documentCount") != len(documents):
                fail(f"Invalid EPUB document audit: {audit_path}")
            if any(not HEX_HASH.fullmatch(document.get("sha256", "")) for document in documents):
                fail(f"Invalid XHTML source hash in audit: {audit_path}")
            if any(document.get("sourceWordCoverage", 0) < 0.97 for document in documents):
                fail(f"An XHTML source has less than 97% extracted word coverage: {audit_path}")
        elif source.get("type") == "PDF":
            pages = audit.get("pages")
            page_count = source.get("pageCount")
            if not isinstance(pages, list) or page_count != len(pages):
                fail(f"PDF page audit count mismatch: {audit_path}")
            if [page.get("page") for page in pages] != list(range(1, page_count + 1)):
                fail(f"PDF page audit is not contiguous: {audit_path}")
            if audit.get("missingPages") != [] or audit.get("duplicatePhraseLabels") != []:
                fail(f"PDF audit reports missing or duplicate content: {audit_path}")
            phrase_pages = sum(page.get("role") == "phrase" for page in pages)
            if audit.get("phrasePageCount") != phrase_pages:
                fail(f"PDF phrase page count mismatch: {audit_path}")
            if any(not HEX_HASH.fullmatch(page.get("textSha256", "")) for page in pages):
                fail(f"Invalid PDF page text hash: {audit_path}")
            if sum(page.get("role") == "chapter-recap" for page in pages) != len(lessons):
                fail(f"PDF recap coverage mismatch: {audit_path}")
        else:
            fail(f"Unsupported source audit type: {audit_path}")

        total_lessons += len(lessons)
        total_assets += len(known_assets)
    if manifest.get("stories") != {"path": "storie/", "status": "reserved"}:
        fail("Stories must remain reserved")
    if not (root / "storie").is_dir():
        fail("Missing storie/ reservation directory")
    json_count = len(list(root.rglob("*.json")))
    return total_lessons, total_assets, json_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    lessons, assets, json_files = validate(args.root)
    print(f"Validated {lessons} lessons, {assets} images, and {json_files} JSON files.")


if __name__ == "__main__":
    main()
