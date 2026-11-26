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


def localized_text(value: Any, location: str) -> None:
    if not isinstance(value, dict):
        fail(f"Localized text must be an object: {location}")
    for language in ("id", "fil"):
        if not isinstance(value.get(language), str) or not value[language].strip():
            fail(f"Missing {language} text: {location}")


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


def validate(root: Path) -> tuple[int, int, int, int]:
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
    story_index_path = verify_hash(root, root, manifest.get("stories", {}))
    story_root = story_index_path.parent
    story_index = load(story_index_path)
    if story_index.get("schemaVersion") != 1 or story_index.get("languagePair") != {"reference": "id", "target": "fil"}:
        fail("Invalid story index metadata")
    collections = story_index.get("collections")
    if not isinstance(collections, list) or not collections:
        fail("Story index must publish at least one book collection")
    collection_ids = [item.get("id") for item in collections]
    if len(collection_ids) != len(set(collection_ids)):
        fail("Story collection ids must be unique")
    if [item.get("order") for item in collections] != list(range(1, len(collections) + 1)):
        fail("Story collection order must be contiguous")

    aggregate_references = story_index.get("stories")
    if not isinstance(aggregate_references, list) or not aggregate_references:
        fail("Aggregate story index must contain stories")
    if story_index.get("storyCount") != len(aggregate_references):
        fail("Aggregate story count does not match its inventory")
    aggregate_ids = [item.get("id") for item in aggregate_references]
    aggregate_paths = [item.get("path") for item in aggregate_references]
    if len(aggregate_ids) != len(set(aggregate_ids)):
        fail("Story ids must be unique across books")
    if len(aggregate_paths) != len(set(aggregate_paths)):
        fail("Story filenames must be unique across books")
    aggregate_by_id = {item["id"]: item for item in aggregate_references}

    root_audit_path = verify_hash(root, story_root, story_index.get("sourceAudit", {}))
    root_audit = load(root_audit_path)
    if root_audit.get("storyCount") != len(aggregate_references) or root_audit.get("bookCount") != len(collections):
        fail("Aggregate story audit totals do not match the published index")

    validated_references: list[dict[str, Any]] = []
    validated_by_id: dict[str, dict[str, Any]] = {}
    total_stories = 0
    for collection_reference in collections:
        collection_index_path = verify_hash(root, story_root, collection_reference)
        collection_index = load(collection_index_path)
        collection_id = collection_reference.get("id")
        if collection_index.get("id") != collection_id:
            fail(f"Story collection metadata mismatch: {collection_index_path}")
        if collection_index.get("languagePair") != {"reference": "id", "target": "fil"}:
            fail(f"Story collection must be Indonesian -> Filipino: {collection_index_path}")
        references = collection_index.get("stories")
        if not isinstance(references, list) or not references:
            fail(f"Story collection has no stories: {collection_index_path}")
        if collection_index.get("storyCount") != len(references):
            fail(f"Story collection count mismatch: {collection_index_path}")
        orders = [reference.get("order") for reference in references]
        source_orders = [reference.get("sourceOrder") for reference in references]
        if orders != list(range(1, len(references) + 1)) or source_orders != list(range(1, len(references) + 1)):
            fail(f"Story order must be contiguous within {collection_id}")
        if any(reference.get("collectionId") != collection_id for reference in references):
            fail(f"Story collection id mismatch: {collection_index_path}")
        audit_path = verify_hash(root, collection_index_path.parent, collection_index.get("sourceAudit", {}))
        story_audit = load(audit_path)
        source = story_audit.get("source", {})
        if source.get("type") != "EPUB" or not HEX_HASH.fullmatch(source.get("epubSha256", "")):
            fail(f"Story source audit must identify its complete EPUB: {audit_path}")
        documents = story_audit.get("documents")
        inspection = story_audit.get("inspection", {})
        if (not isinstance(documents, list) or story_audit.get("documentCount") != len(documents)
                or inspection.get("spineDocumentCount") != len(documents)):
            fail(f"Story source audit must cover every spine document: {audit_path}")
        if any(not HEX_HASH.fullmatch(document.get("sha256", "")) for document in documents):
            fail(f"Story source audit contains an invalid XHTML hash: {audit_path}")
        if sum(document.get("role") == "story" for document in documents) != len(references):
            fail(f"Story source audit story count mismatch: {audit_path}")
        if inspection.get("actualNarrativeCount") != len(references):
            fail(f"Story source audit narrative count mismatch: {audit_path}")
        if inspection.get("excludedDocumentCount") != sum(document.get("role") != "story" for document in documents):
            fail(f"Story source audit exclusion count mismatch: {audit_path}")
        audited_stories = story_audit.get("stories")
        if (not isinstance(audited_stories, list) or story_audit.get("storyCount") != len(references)
                or [item.get("order") for item in audited_stories] != orders):
            fail(f"Story audit inventory is incomplete or out of order: {audit_path}")
        if [item.get("title") for item in audited_stories] != [reference.get("title", {}).get("id") for reference in references]:
            fail(f"Story audit titles do not match the published index: {audit_path}")
        assets_audit = story_audit.get("assets", {})
        asset_items = assets_audit.get("items")
        if (assets_audit.get("availableIllustrations") != len(references)
                or assets_audit.get("extracted") != len(references)
                or not isinstance(asset_items, list) or len(asset_items) != len(references)):
            fail(f"Story illustration audit is incomplete: {audit_path}")
        known_story_assets: set[str] = set()
        for item in asset_items:
            path = story_root / safe_relative(item.get("path", ""))
            if not path.is_file() or digest(path) != item.get("sha256") or path.stat().st_size != item.get("bytes"):
                fail(f"Invalid story illustration audit: {path}")
            suffix_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
            if item.get("mediaType") != suffix_type or item.get("width", 0) <= 0 or item.get("height", 0) <= 0:
                fail(f"Invalid story illustration metadata: {path}")
            known_story_assets.add(path.relative_to(story_root).as_posix())
        exercise_types = {"MULTIPLE_CHOICE", "VOCABULARY_TRANSLATION", "FILL_BLANK", "GRAMMAR", "SENTENCE_CONSTRUCTION", "COMPREHENSION"}
        for reference, audit_item in zip(references, audited_stories):
            story_path = verify_hash(root, story_root, reference)
            story = load(story_path)
            where = story_path.as_posix()
            if story.get("schemaVersion") != 1 or story.get("id") != reference.get("id"):
                fail(f"Story metadata mismatch: {where}")
            if (story.get("collectionId") != collection_id or story.get("sourceOrder") != reference.get("sourceOrder")
                    or story.get("order") != reference.get("order")):
                fail(f"Story collection/order mismatch: {where}")
            for field in ("family", "category", "level"):
                if story.get(field) != reference.get(field):
                    fail(f"Story {field} mismatch: {where}")
            if story.get("level") not in {"BEGINNER", "INTERMEDIATE", "ADVANCED"} or story.get("kind") != "STORY":
                fail(f"Invalid story level or kind: {where}")
            localized_text(story.get("title"), f"{where}.title")
            localized_text(story.get("summary"), f"{where}.summary")
            if (story.get("originalTitle") != audit_item.get("title") or story["title"] != {"id": story["originalTitle"], "fil": story["originalTitle"]}):
                fail(f"Original source title was not preserved: {where}")
            source_document = audit_item.get("sourceDocument", "")
            source_reference = next((item for item in documents if item.get("path") == source_document), None)
            if (not source_document.endswith(f"Unit_{reference.get('sourceOrder', 0):02d}.xhtml")
                    or source_reference is None or source_reference.get("role") != "story"
                    or source_reference.get("sha256") != audit_item.get("sourceSha256")
                    or not isinstance(audit_item.get("characters"), list) or not audit_item["characters"]
                    or not isinstance(audit_item.get("setting"), str) or not audit_item["setting"].strip()
                    or not isinstance(audit_item.get("theme"), str) or not audit_item["theme"].strip()
                    or not isinstance(audit_item.get("mainEvents"), list) or len(audit_item["mainEvents"]) < 3):
                fail(f"Story source audit is incomplete: {where}")
            if (audit_item.get("generatedStory") != story_path.relative_to(story_root).as_posix()
                    or audit_item.get("generatedSha256") != digest(story_path)):
                fail(f"Story generation audit mismatch: {where}")
            sentences = story.get("sentences")
            if not isinstance(sentences, list) or len(sentences) < 6 or len(sentences) > 10:
                fail(f"Story retelling must be concise but complete: {where}")
            if story.get("sentenceCount") != len(sentences) or reference.get("sentenceCount") != len(sentences):
                fail(f"Story paragraph count mismatch: {where}")
            for index, sentence in enumerate(sentences):
                localized_text(sentence, f"{where}.sentences[{index}]")
            objectives = story.get("objectives")
            if not isinstance(objectives, list) or len(objectives) < 2:
                fail(f"Story objectives are missing: {where}")
            for index, objective in enumerate(objectives):
                localized_text(objective, f"{where}.objectives[{index}]")
            notes = story.get("notes")
            if not isinstance(notes, list) or len(notes) < 2:
                fail(f"Story needs learning notes: {where}")
            for index, note in enumerate(notes):
                localized_text(note.get("title"), f"{where}.notes[{index}].title")
                localized_text(note.get("text"), f"{where}.notes[{index}].text")
            vocabulary = story.get("vocabulary")
            if not isinstance(vocabulary, list) or len(vocabulary) < 6:
                fail(f"Story needs a substantial vocabulary list: {where}")
            vocabulary_keys = []
            for index, entry in enumerate(vocabulary):
                entry_where = f"{where}.vocabulary[{index}]"
                if entry.get("language") != "fil" or not isinstance(entry.get("word"), str) or not entry["word"].strip():
                    fail(f"Invalid story vocabulary entry: {entry_where}")
                vocabulary_keys.append(entry["word"].casefold())
                for field in ("translations", "meanings", "notes"):
                    localized_text(entry.get(field), f"{entry_where}.{field}")
                if not isinstance(entry.get("pos"), str) or not entry["pos"].strip():
                    fail(f"Vocabulary part of speech is missing: {entry_where}")
            if len(vocabulary_keys) != len(set(vocabulary_keys)):
                fail(f"Duplicate vocabulary entries: {where}")
            tagalog_text = " ".join(sentence["fil"].casefold() for sentence in sentences)
            if any(key not in tagalog_text for key in vocabulary_keys):
                fail(f"Every vocabulary item must occur in the Tagalog story: {where}")
            focus = story.get("focus")
            if not isinstance(focus, dict) or not all(isinstance(focus.get(language), list) and focus[language] for language in ("id", "fil")):
                fail(f"Invalid story focus list: {where}")
            if any(value.casefold() not in set(vocabulary_keys) for value in focus["fil"]):
                fail(f"A focus expression is missing from vocabulary: {where}")
            questions = story.get("questions")
            answers = story.get("answers")
            if not isinstance(questions, list) or len(questions) < 3 or not isinstance(answers, list):
                fail(f"Story needs reading-comprehension questions and a separate answer key: {where}")
            answer_map = {answer.get("questionId"): answer for answer in answers}
            if len(answer_map) != len(answers) or set(answer_map) != {question.get("id") for question in questions}:
                fail(f"Question and answer ids do not match: {where}")
            for index, question in enumerate(questions):
                question_where = f"{where}.questions[{index}]"
                if question.get("type") not in exercise_types or not question.get("id"):
                    fail(f"Invalid question: {question_where}")
                localized_text(question.get("prompt"), f"{question_where}.prompt")
                answer = answer_map[question["id"]]
                localized_text(answer.get("answer"), f"{question_where}.answerKey.answer")
                localized_text(answer.get("explanation"), f"{question_where}.answerKey.explanation")
                if question["type"] in {"MULTIPLE_CHOICE", "GRAMMAR"}:
                    choices = question.get("choices")
                    if not isinstance(choices, dict):
                        fail(f"Question choices are missing: {question_where}")
                    for language in ("id", "fil"):
                        if (not isinstance(choices.get(language), list) or len(set(choices[language])) < 2
                                or answer["answer"][language] not in choices[language]):
                            fail(f"Invalid {language} choices: {question_where}")
                if question["type"] == "SENTENCE_CONSTRUCTION":
                    tokens = question.get("tokens")
                    if not isinstance(tokens, dict) or any(not tokens.get(language) for language in ("id", "fil")):
                        fail(f"Construction tokens are missing: {question_where}")
            assets = story.get("assets")
            if not isinstance(assets, list) or len(assets) != 1 or assets != reference.get("assets") or story.get("image") != assets[0]:
                fail(f"Story must reference exactly its own illustration: {where}")
            asset_path = story_path.parent / safe_relative(assets[0])
            audit_asset = asset_path.relative_to(story_root).as_posix()
            if not asset_path.is_file() or audit_asset not in known_story_assets or audit_item.get("illustration") != audit_asset:
                fail(f"Missing or unrelated story illustration: {where}")
            if reference["id"] in validated_by_id:
                fail(f"Duplicate story id across collection indexes: {reference['id']}")
            validated_by_id[reference["id"]] = reference
        total_stories += len(references)
        validated_references.extend(references)

    if set(validated_by_id) != set(aggregate_ids):
        fail("Aggregate story inventory differs from the book indexes")
    if {item.get("path") for item in validated_references} != set(aggregate_paths):
        fail("Aggregate story paths differ from the book indexes")
    if len(validated_references) != len(aggregate_references):
        fail("Aggregate story inventory contains duplicates")
    if any(validated_by_id[story_id] != aggregate_by_id[story_id] for story_id in aggregate_by_id):
        fail("Aggregate story references differ from the book indexes")

    indexed_paths = set(aggregate_paths)
    discovered_paths: set[str] = set()
    discovered_ids: set[str] = set()
    for collection_id in collection_ids:
        collection_dir = story_root / safe_relative(collection_id)
        for story_path in collection_dir.glob("*.json"):
            if story_path.name in {"index.json", "source-audit.json"}:
                continue
            relative = story_path.relative_to(story_root).as_posix()
            if relative in discovered_paths:
                fail(f"Duplicate story filename on disk: {relative}")
            discovered_paths.add(relative)
            story = load(story_path)
            story_id = story.get("id")
            if not isinstance(story_id, str) or story_id in discovered_ids:
                fail(f"Duplicate or missing story id on disk: {story_id!r}")
            discovered_ids.add(story_id)
    if discovered_paths != indexed_paths:
        fail("Story files on disk differ from the complete aggregate index")
    if discovered_ids != set(aggregate_ids):
        fail("Story file IDs differ from the complete aggregate index")
    category_counts = Counter(item.get("category") for item in aggregate_references)
    indexed_category_counts = {
        item.get("name"): item.get("storyCount") for item in story_index.get("categories", [])
    }
    if len(indexed_category_counts) != len(story_index.get("categories", [])):
        fail("Story category names must be unique")
    if indexed_category_counts != dict(category_counts):
        fail("Story category inventory differs from the indexed category counts")
    for category in story_index.get("categories", []):
        if category.get("storyCount") != category_counts.get(category.get("name"), 0):
            fail("Story category count does not match the inventory")
    json_count = len(list(root.rglob("*.json")))
    return total_lessons, total_assets, total_stories, json_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    lessons, assets, stories, json_files = validate(args.root)
    print(f"Validated {lessons} lessons, {stories} stories, {assets} lesson images, and {json_files} JSON files.")


if __name__ == "__main__":
    main()
