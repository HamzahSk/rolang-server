#!/usr/bin/env python3
"""Extract Elementary Tagalog into RoLang's static Indonesian -> Tagalog schema.

The EPUB remains the source of truth. The generated JSON keeps normalized source
text beside its Indonesian translation so extraction and translation can be
audited independently. Translation is performed locally with Argos/CTranslate2
models; no text is sent to a remote service.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from xml.etree import ElementTree as ET
from zipfile import ZipFile


COURSE_ID = "elementary-tagalog-1"
SCHEMA_VERSION = 1
SOURCE_FILES = ["Introduction", "Guide", "Language", "Greetings"] + [
    f"Unit{number}" for number in range(1, 9)
] + [f"Lesson{number}" for number in range(1, 25)]

UNIT_RANGES = {
    1: range(1, 4),
    2: range(4, 7),
    3: range(7, 10),
    4: range(10, 13),
    5: range(13, 16),
    6: range(16, 19),
    7: range(19, 22),
    8: range(22, 25),
}

UNIT_METADATA = {
    1: ("unit-01-self", "Tungkol sa Sarili", "Tentang Diri", "about-self"),
    2: ("unit-02-family", "Pamilya", "Keluarga", "family"),
    3: ("unit-03-activities", "Mga Gawain", "Kegiatan", "activities"),
    4: ("unit-04-home", "Tahanan", "Rumah", "home"),
    5: ("unit-05-health", "Kalusugan", "Kesehatan", "health"),
    6: ("unit-06-food", "Pagkain", "Makanan", "food"),
    7: ("unit-07-travel", "Paglalakbay", "Perjalanan", "travel"),
    8: (
        "unit-08-popular-culture",
        "Kulturang Popular sa Pilipinas",
        "Budaya Populer di Filipina",
        "popular-culture",
    ),
}

LESSON_METADATA = {
    1: ("Unang Araw ng Klase", "Hari Pertama di Kelas", "first-day-of-class"),
    2: ("Pagpapakilala", "Perkenalan", "introductions"),
    3: ("Mga Gusto at Ayaw", "Hal yang Disukai dan Tidak Disukai", "likes-and-dislikes"),
    4: ("Ang Pamilya Ko", "Keluarga Saya", "my-family"),
    5: (
        "Paglalarawan ng mga Miyembro ng Pamilya",
        "Menggambarkan Anggota Keluarga",
        "describing-family-members",
    ),
    6: ("Pag-uusap Tungkol sa Pamilya", "Berbicara tentang Keluarga", "talking-about-family"),
    7: ("Mga Gawain sa Araw-araw", "Kegiatan Sehari-hari", "daily-activities"),
    8: ("Mga Libangan", "Hobi", "hobbies"),
    9: ("Pamimili", "Berbelanja", "shopping"),
    10: ("Ang Aking Bahay", "Rumah Saya", "my-house"),
    11: ("Ang Paborito Kong Lugar", "Tempat Favorit Saya", "my-favorite-place"),
    12: ("Ang Bayan Ko", "Kampung Halaman Saya", "my-hometown"),
    13: ("Mga Iba’t ibang Sakit", "Berbagai Penyakit", "various-illnesses"),
    14: ("Pagbisita sa Doktor", "Berkunjung ke Dokter", "going-to-the-doctor"),
    15: ("Mga Iba’t ibang Lunas", "Berbagai Pengobatan", "various-remedies"),
    16: ("Sa Palengke", "Di Pasar", "at-the-market"),
    17: ("Pagkain sa Labas", "Makan di Luar", "eating-out"),
    18: ("Pagluluto", "Memasak", "cooking"),
    19: ("Bakasyon", "Liburan", "vacation"),
    20: ("Mga Pista", "Pesta dan Perayaan", "fiestas"),
    21: (
        "Mga Iba’t ibang Lugar sa Pilipinas",
        "Berbagai Tempat di Filipina",
        "places-in-the-philippines",
    ),
    22: ("Mga Alamat", "Legenda", "legends"),
    23: ("Sine at Telebisyon", "Film dan Televisi", "cinema-and-television"),
    24: ("Musika at Sayaw", "Musik dan Tari", "music-and-dance"),
}

FRONT_TITLES = {
    "Introduction": ("Introduction", "Pengantar"),
    "Guide": ("Pronunciation Guide", "Panduan Pelafalan"),
    "Language": ("The Tagalog Language", "Bahasa Tagalog"),
    "Greetings": ("Mga Pagbati", "Sapaan"),
}

SECTION_TYPES = {
    "overview": "OVERVIEW",
    "vocabulary": "VOCABULARY",
    "dialogue": "DIALOGUE",
    "reading": "DIALOGUE",
    "activities": "ACTIVITY",
    "activity": "ACTIVITY",
    "grammar": "GRAMMAR",
    "practice": "PRACTICE",
}

ENGLISH_WORDS = set(
    """a about after again all also am an and another answer any are as ask at be because before
    below between book both but by can class complete construct could day describe dialogue did do
    does each english example exercise express family fill following for form from give grammar had
    has have he help her here him his how i if in into is it its lesson like make many may more must
    my name new no not now of on one or other our out place practice question read respond response
    same sentence should so some speak statement student than that the their them then there these
    they this those through time to true two under understand use used using vocabulary was we what
    when where which who why will with word words would write you your""".split()
)
TAGALOG_WORDS = set(
    """ako akin ang ano araw ay ayaw ba bakit bilang daw dahil din dito doon gusto hindi ikaw inyong
    ito ka kailan kami kanino kapag kasi kay kayo ko kong kung lang lahat mga mag magandang may mayroon
    mo mong muna na nag naman namin nang nasa natin ng niya niyang nila nilang ninyo o oo pa paano para
    pero po rin sa saan sila si sino siya tayong tayo tungkol wala""".split()
)
TAGALOG_CLASSES = {"textStyle20", "textStyle20ud", "textStyle34", "ud"}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def clean_text(value: str) -> str:
    value = value.replace("\u00a0", " ").replace("\u200b", "")
    value = re.sub(r"[ \t\f\v]+", " ", value)
    value = re.sub(r" *\n *", "\n", value)
    return value.strip()


def element_text(element: ET.Element) -> str:
    parts: list[str] = []

    def visit(node: ET.Element) -> None:
        if node.text:
            parts.append(node.text)
        for child in node:
            if tag(child) == "br":
                parts.append("\n")
            else:
                visit(child)
            if child.tail:
                parts.append(child.tail)

    visit(element)
    return clean_text("".join(parts))


def tagalog_fragments(element: ET.Element) -> str:
    fragments: list[str] = []
    for child in element.iter():
        classes = set(child.attrib.get("class", "").split())
        if classes & TAGALOG_CLASSES:
            value = element_text(child)
            if value and value not in fragments:
                fragments.append(value)
    return clean_text(" ".join(fragments))


def words(value: str) -> list[str]:
    return re.findall(r"[^\W\d_]+(?:['’][^\W\d_]+)?", value.lower(), re.UNICODE)


def detect_language(value: str, hint: str = "", fragments: str = "") -> str:
    tokens = words(value)
    if not tokens or re.fullmatch(r"[_\W]+", value):
        return "mixed"
    english = sum(token in ENGLISH_WORDS for token in tokens)
    tagalog = sum(token in TAGALOG_WORDS for token in tokens)
    if hint == "fil" and english <= tagalog + 1:
        return "fil"
    if tagalog >= max(2, english * 2):
        return "fil"
    if english >= max(2, tagalog * 2):
        return "en"
    if fragments and len(words(fragments)) >= max(1, len(tokens) // 2):
        return "fil"
    return "mixed"


def safe_id(value: str, fallback: str) -> str:
    normalized = value.lower().replace("’", "'")
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized[:80] or fallback


def image_path(src: str) -> str:
    return f"assets/{PurePosixPath(src).name}"


class LocalTranslator:
    """Small wrapper around unpacked Argos CTranslate2 models."""

    def __init__(self, english_indonesian: Path, tagalog_english: Path):
        try:
            import ctranslate2  # type: ignore
            from argostranslate.tokenizer import BPETokenizer, SentencePieceTokenizer  # type: ignore
        except ImportError as error:
            raise SystemExit(
                "Translation requires ctranslate2, argostranslate, sacremoses, and sentencepiece."
            ) from error
        self._ctranslate2 = ctranslate2
        self._bpe_tokenizer_type = BPETokenizer
        self._sentencepiece_tokenizer_type = SentencePieceTokenizer
        self.en_id = self._load(english_indonesian, "en", "id")
        self.tl_en = self._load(tagalog_english, "tl", "en")
        self.cache: dict[tuple[str, str], str] = {}

    def _load(self, root: Path, source: str, target: str):
        if not (root / "model").is_dir() or not (
            (root / "bpe.model").is_file() or (root / "sentencepiece.model").is_file()
        ):
            raise SystemExit(f"Invalid unpacked Argos model directory: {root}")
        tokenizer = (
            self._bpe_tokenizer_type(root / "bpe.model", source, target)
            if (root / "bpe.model").is_file()
            else self._sentencepiece_tokenizer_type(root / "sentencepiece.model")
        )
        translator = self._ctranslate2.Translator(str(root / "model"), "cpu")
        return tokenizer, translator

    @staticmethod
    def chunks(value: str, limit: int = 360) -> list[str]:
        lines: list[str] = []
        for paragraph in value.splitlines() or [value]:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            candidates = re.split(r"(?<=[.!?])\s+", paragraph)
            current = ""
            for candidate in candidates:
                if len(candidate) > limit:
                    pieces = re.findall(r".{1,%d}(?:\s+|$)" % limit, candidate)
                else:
                    pieces = [candidate]
                for piece in pieces:
                    piece = piece.strip()
                    if not piece:
                        continue
                    if current and len(current) + len(piece) + 1 > limit:
                        lines.append(current)
                        current = piece
                    else:
                        current = f"{current} {piece}".strip()
            if current:
                lines.append(current)
        return lines or [value]

    @staticmethod
    def translatable(value: str) -> bool:
        return bool(re.search(r"[^\W\d_]", value, re.UNICODE)) and not re.fullmatch(r"[_\W]+", value)

    def _batch(self, model, values: list[str]) -> list[str]:
        tokenizer, translator = model
        results: list[str] = []
        for offset in range(0, len(values), 128):
            batch = values[offset : offset + 128]
            translated = translator.translate_batch(
                [tokenizer.encode(value) for value in batch],
                beam_size=4,
                max_batch_size=32,
                replace_unknowns=True,
            )
            results.extend(clean_text(tokenizer.decode(item.hypotheses[0])) for item in translated)
        return results

    def translate_records(self, records: list[dict[str, Any]]) -> None:
        requests: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for record in records:
            if record.pop("_preserveId", False):
                continue
            source = record.pop("_translationSource", record["sourceText"])
            language = record.pop("_translationLanguage", record["sourceLanguage"])
            if not self.translatable(source):
                record["id"] = source
                continue
            key = (language, source)
            requests.setdefault(key, []).append(record)

        segments_by_language: dict[str, list[str]] = {"en": [], "fil": [], "mixed": []}
        layouts: dict[tuple[str, str], list[str]] = {}
        for language, source in requests:
            chunks = self.chunks(source)
            layouts[(language, source)] = chunks
            segments_by_language.setdefault(language, []).extend(chunks)

        en_segments = list(dict.fromkeys(segments_by_language["en"] + segments_by_language["mixed"]))
        en_output = self._batch(self.en_id, en_segments) if en_segments else []
        for source, translated in zip(en_segments, en_output):
            self.cache[("en", source)] = translated
            self.cache[("mixed", source)] = translated

        fil_segments = list(dict.fromkeys(segments_by_language["fil"]))
        if fil_segments:
            english = self._batch(self.tl_en, fil_segments)
            indonesian = self._batch(self.en_id, english)
            for source, translated in zip(fil_segments, indonesian):
                self.cache[("fil", source)] = translated

        for key, targets in requests.items():
            language, source = key
            translated = " ".join(self.cache[(language, chunk)] for chunk in layouts[key]).strip()
            for target in targets:
                target["id"] = translated or source


def normalize_instructional_headings(records: list[dict[str, Any]]) -> None:
    exact = {
        "Overview": "Gambaran Umum",
        "Vocabulary": "Kosakata",
        "Activities": "Aktivitas",
        "Grammar": "Tata Bahasa",
        "Practice": "Latihan",
        "Definition of Terms": "Definisi Istilah",
        "Examining Form": "Mengkaji Bentuk",
        "Grammar Presentation": "Penyajian Tata Bahasa",
        "Grammar Notes": "Catatan Tata Bahasa",
        "Dialogue Comprehension": "Pemahaman Dialog",
        "Reading Comprehension": "Pemahaman Bacaan",
    }
    practice = {
        "Speaking Practice": "Latihan Berbicara",
        "Reading Practice": "Latihan Membaca",
        "Writing Practice": "Latihan Menulis",
        "Listening Practice": "Latihan Menyimak",
    }
    for record in records:
        source = record["sourceText"].strip()
        if source in exact:
            record["id"] = exact[source]
            continue
        if source.startswith("Vocabulary ("):
            record["id"] = "Kosakata " + source[len("Vocabulary ") :]
            continue
        match = re.fullmatch(r"An Overview of Lesson (\d+)", source)
        if match:
            record["id"] = f"Gambaran Umum Pelajaran {match.group(1)}"
            continue
        match = re.fullmatch(r"([IVX]+\.\s+)(Speaking|Reading|Writing|Listening) Practice", source)
        if match:
            record["id"] = match.group(1) + practice[f"{match.group(2)} Practice"]
            continue
        if source.startswith("Grammar Presentation:"):
            suffix = record["id"].split(":", 1)[-1].strip() if ":" in record["id"] else source.split(":", 1)[1]
            record["id"] = f"Penyajian Tata Bahasa: {suffix}"
        elif source.startswith("Dialogue:") and not record["id"].startswith("Dialog"):
            record["id"] = "Dialog:" + record["id"].split(":", 1)[-1]
        elif source.startswith("Reading Text:") and not record["id"].startswith("Teks Bacaan"):
            record["id"] = "Teks Bacaan:" + record["id"].split(":", 1)[-1]
        elif source.startswith("Activity ") and record["id"].startswith("Kegiatan "):
            record["id"] = "Aktivitas " + record["id"][len("Kegiatan ") :]


class Extractor:
    def __init__(self, archive: ZipFile):
        self.archive = archive
        self.translation_records: list[dict[str, Any]] = []
        self.audit_documents: list[dict[str, Any]] = []

    def lesson_text(
        self,
        value: str,
        language: str,
        *,
        tagalog: str = "",
        translation_source: str = "",
        translation_language: str = "",
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "sourceLanguage": language,
            "sourceText": value,
            "id": "",
        }
        if language == "fil":
            result["tagalog"] = value
        elif tagalog:
            result["tagalog"] = tagalog
        if translation_source:
            result["_translationSource"] = translation_source
        if translation_language:
            result["_translationLanguage"] = translation_language
        self.translation_records.append(result)
        return result

    def walk(self, parent: ET.Element) -> Iterable[tuple[str, ET.Element]]:
        for child in parent:
            child_tag = tag(child)
            if child_tag == "h3" and child.attrib.get("title"):
                yield "section", child
            elif child_tag == "table":
                yield "table", child
            elif child_tag in {"p", "h4", "h5", "h6", "blockquote"}:
                yield "block", child
            elif child_tag == "img":
                yield "image", child
            elif child_tag in {"div", "section", "article", "body"}:
                yield from self.walk(child)

    def section_type(self, title: str, default: str) -> str:
        lowered = title.lower().strip()
        return next((kind for prefix, kind in SECTION_TYPES.items() if lowered.startswith(prefix)), default)

    def element_lesson_text(self, element: ET.Element, section_type: str, hint: str = "") -> dict[str, Any]:
        value = element_text(element)
        fragments = tagalog_fragments(element)
        language = detect_language(value, hint=hint, fragments=fragments)
        return self.lesson_text(value, language, tagalog=fragments if language == "mixed" else "")

    def table_block(self, table: ET.Element, section_type: str) -> dict[str, Any] | None:
        rows: list[dict[str, Any]] = []
        for row in (item for item in table.iter() if tag(item) == "tr"):
            cell_elements = [item for item in row if tag(item) in {"td", "th"}]
            cells: list[dict[str, Any]] = []
            values = [element_text(cell) for cell in cell_elements]
            for index, (cell, value) in enumerate(zip(cell_elements, values)):
                if not value:
                    continue
                hint = ""
                paired = ""
                if section_type == "VOCABULARY" and len(values) == 2 and all(values):
                    if index == 0:
                        hint = "fil"
                        paired = values[1]
                elif section_type == "DIALOGUE" and len(values) == 2 and index == 1:
                    hint = "fil"
                fragments = tagalog_fragments(cell)
                language = detect_language(value, hint=hint, fragments=fragments)
                cells.append(
                    self.lesson_text(
                        value,
                        language,
                        tagalog=fragments if language == "mixed" else "",
                        translation_source=paired,
                        translation_language="en" if paired else "",
                    )
                )
            if cells:
                rows.append({"cells": cells})
        return {"type": "table", "rows": rows} if rows else None

    def parse_document(
        self,
        source_name: str,
        initial_title: tuple[str, str],
        *,
        default_type: str = "CONTENT",
        id_prefix: str = "",
    ) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
        source_path = f"OEBPS/Text/{source_name}.xhtml"
        source_bytes = self.archive.read(source_path)
        root = ET.fromstring(source_bytes)
        body = next(element for element in root.iter() if tag(element) == "body")
        sections: list[dict[str, Any]] = []
        assets: list[str] = []

        def new_section(source_title: str, indonesian_title: str, kind: str) -> dict[str, Any]:
            section = {
                "id": safe_id(f"{id_prefix}-{source_title}", f"{id_prefix}-content"),
                "type": kind,
                "title": self.lesson_text(source_title, detect_language(source_title)),
                "blocks": [],
            }
            section["title"]["id"] = indonesian_title
            if indonesian_title:
                section["title"]["_preserveId"] = True
            sections.append(section)
            return section

        current = new_section(initial_title[0], initial_title[1], default_type)
        for event, element in self.walk(body):
            if event == "section":
                source_title = clean_text(element.attrib.get("title", ""))
                current = new_section(source_title, "", self.section_type(source_title, default_type))
                continue
            if event == "image":
                path = image_path(element.attrib["src"])
                assets.append(path)
                current["blocks"].append({"type": "image", "path": path})
                continue
            if event == "table":
                block = self.table_block(element, current["type"])
                if block:
                    current["blocks"].append(block)
                for image in (item for item in element.iter() if tag(item) == "img"):
                    path = image_path(image.attrib["src"])
                    assets.append(path)
                    current["blocks"].append({"type": "image", "path": path})
                continue

            classes = set(element.attrib.get("class", "").split())
            if classes & {"hh1", "hh2", "hh3"}:
                continue
            value = element_text(element)
            if value:
                style = "heading" if tag(element) in {"h4", "h5", "h6"} else "body"
                hint = "fil" if current["type"] == "DIALOGUE" and not any(
                    token in value.lower() for token in ("dialogue", "reading text", "comprehension")
                ) else ""
                current["blocks"].append(
                    {"type": "text", "style": style, "text": self.element_lesson_text(element, current["type"], hint)}
                )
            for image in (item for item in element.iter() if tag(item) == "img"):
                path = image_path(image.attrib["src"])
                assets.append(path)
                current["blocks"].append({"type": "image", "path": path})

        sections = [section for section in sections if section["blocks"]]
        normalized_source = clean_text(" ".join(body.itertext()))
        emitted = [
            block["text"]["sourceText"]
            for section in sections
            for block in section["blocks"]
            if block["type"] == "text"
        ]
        for section in sections:
            emitted.append(section["title"]["sourceText"])
            for block in section["blocks"]:
                if block["type"] == "table":
                    emitted.extend(cell["sourceText"] for row in block["rows"] for cell in row["cells"])
        source_words = Counter(words(normalized_source))
        extracted_words = Counter(words(" ".join(emitted)))
        matched_words = sum(min(count, extracted_words[token]) for token, count in source_words.items())
        audit = {
            "source": source_path,
            "sha256": sha256_bytes(source_bytes),
            "normalizedSourceCharacters": len(normalized_source),
            "extractedTextBlocks": len(emitted),
            "extractedTextCharacters": sum(len(value) for value in emitted),
            "normalizedSourceWords": sum(source_words.values()),
            "extractedSourceWords": sum(extracted_words.values()),
            "sourceWordCoverage": round(matched_words / max(1, sum(source_words.values())), 6),
            "imageReferences": list(dict.fromkeys(assets)),
        }
        self.audit_documents.append(audit)
        return sections, list(dict.fromkeys(assets)), audit


def objective_texts(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    overview = next((section for section in sections if section["type"] == "OVERVIEW"), None)
    if not overview:
        return []
    objectives: list[dict[str, Any]] = []
    active = False
    for block in overview["blocks"]:
        if block["type"] != "text":
            continue
        text = block["text"]
        source = text["sourceText"].strip()
        lowered = source.lower()
        if lowered == "objectives":
            active = True
            continue
        if active and lowered in {"vocabulary", "activities", "grammar", "practice"}:
            break
        if active and source.lstrip().startswith(("•", "-")):
            objectives.append(text)
    return objectives


def localized(indonesian: str, tagalog: str) -> dict[str, str]:
    return {"id": indonesian, "fil": tagalog}


def build(args: argparse.Namespace) -> None:
    epub = args.epub.resolve()
    output = args.output.resolve()
    course_dir = output / "lesson" / COURSE_ID
    assets_dir = course_dir / "assets"
    units_dir = course_dir / "units"
    assets_dir.mkdir(parents=True, exist_ok=True)
    units_dir.mkdir(parents=True, exist_ok=True)
    (output / "storie").mkdir(parents=True, exist_ok=True)

    translator = LocalTranslator(args.english_indonesian, args.tagalog_english)
    with ZipFile(epub) as archive:
        extractor = Extractor(archive)
        lesson_documents: dict[int, dict[str, Any]] = {}
        lesson_refs: list[dict[str, Any]] = []
        unit_documents: dict[int, dict[str, Any]] = {}

        for number in range(1, 25):
            tagalog_title, indonesian_title, slug = LESSON_METADATA[number]
            unit_number = next(unit for unit, lesson_range in UNIT_RANGES.items() if number in lesson_range)
            unit_id = UNIT_METADATA[unit_number][0]
            sections, assets, _ = extractor.parse_document(
                f"Lesson{number}",
                (tagalog_title, indonesian_title),
                default_type="OVERVIEW",
                id_prefix=f"lesson-{number:02d}",
            )
            objectives = objective_texts(sections)
            document = {
                "schemaVersion": SCHEMA_VERSION,
                "id": f"{COURSE_ID}-lesson-{number:02d}",
                "courseId": COURSE_ID,
                "unitId": unit_id,
                "order": number,
                "level": "BEGINNER",
                "title": localized(indonesian_title, tagalog_title),
                "summary": localized(indonesian_title, tagalog_title),
                "objectives": objectives,
                "source": {
                    "book": "Elementary Tagalog",
                    "file": f"OEBPS/Text/Lesson{number}.xhtml",
                },
                "assets": assets,
                "sections": sections,
            }
            lesson_documents[number] = document
            lesson_refs.append(
                {
                    "id": document["id"],
                    "unitId": unit_id,
                    "order": number,
                    "path": f"{number:02d}-{slug}.json",
                    "title": document["title"],
                    "summary": document["summary"],
                    "objectives": objectives,
                    "assets": assets,
                }
            )

        for unit_number in range(1, 9):
            unit_id, tagalog_title, indonesian_title, slug = UNIT_METADATA[unit_number]
            source_names = (["Introduction", "Guide", "Language", "Greetings"] if unit_number == 1 else []) + [
                f"Unit{unit_number}"
            ]
            sections: list[dict[str, Any]] = []
            assets: list[str] = []
            for source_name in source_names:
                initial = FRONT_TITLES.get(source_name, (tagalog_title, indonesian_title))
                extracted, source_assets, _ = extractor.parse_document(
                    source_name,
                    initial,
                    default_type="CONTENT" if source_name != "Greetings" else "OVERVIEW",
                    id_prefix=f"unit-{unit_number:02d}-{source_name.lower()}",
                )
                sections.extend(extracted)
                assets.extend(source_assets)
            unit_documents[unit_number] = {
                "schemaVersion": SCHEMA_VERSION,
                "id": unit_id,
                "courseId": COURSE_ID,
                "title": localized(indonesian_title, tagalog_title),
                "sourceFiles": [f"OEBPS/Text/{name}.xhtml" for name in source_names],
                "assets": list(dict.fromkeys(assets)),
                "sections": sections,
            }

        translator.translate_records(extractor.translation_records)
        normalize_instructional_headings(extractor.translation_records)

        image_members = sorted(
            name for name in archive.namelist() if name.startswith("OEBPS/Images/") and not name.endswith("/")
        )
        inventory: list[dict[str, Any]] = []
        for member in image_members:
            destination = assets_dir / PurePosixPath(member).name
            with archive.open(member) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)
            inventory.append(
                {
                    "path": f"assets/{destination.name}",
                    "sha256": sha256_file(destination),
                    "bytes": destination.stat().st_size,
                    "mediaType": "image/jpeg",
                }
            )

    asset_index_path = assets_dir / "index.json"
    write_json(
        asset_index_path,
        {
            "schemaVersion": SCHEMA_VERSION,
            "courseId": COURSE_ID,
            "count": len(inventory),
            "assets": inventory,
        },
    )

    audit_path = course_dir / "source-audit.json"
    write_json(
        audit_path,
        {
            "schemaVersion": SCHEMA_VERSION,
            "source": {
                "title": "Elementary Tagalog",
                "authors": ["Jiedson R. Domigpe", "Nenita Pambid Domingo"],
                "publisher": "Tuttle Publishing",
                "isbn": "978-0-8048-4117-7",
                "epubSha256": sha256_file(epub),
            },
            "documents": extractor.audit_documents,
            "documentCount": len(extractor.audit_documents),
            "lessonCount": 24,
            "unitCount": 8,
            "assetCount": len(inventory),
        },
    )

    for number, document in lesson_documents.items():
        write_json(course_dir / lesson_refs[number - 1]["path"], document)
    unit_refs: list[dict[str, Any]] = []
    for unit_number, document in unit_documents.items():
        _, _, _, slug = UNIT_METADATA[unit_number]
        path = f"units/{unit_number:02d}-{slug}.json"
        write_json(course_dir / path, document)
        unit_refs.append(
            {
                "id": document["id"],
                "title": document["title"],
                "path": path,
                "lessons": [f"{COURSE_ID}-lesson-{number:02d}" for number in UNIT_RANGES[unit_number]],
                "assets": document["assets"],
            }
        )

    for reference in lesson_refs:
        reference["sha256"] = sha256_file(course_dir / reference["path"])
    for reference in unit_refs:
        reference["sha256"] = sha256_file(course_dir / reference["path"])

    course_index = {
        "schemaVersion": SCHEMA_VERSION,
        "id": COURSE_ID,
        "level": "BEGINNER",
        "languagePair": {"reference": "id", "target": "fil"},
        "title": localized("Elementary Tagalog 1", "Elementary Tagalog 1"),
        "description": localized(
            "Kursus lengkap bahasa Tagalog tingkat dasar berdasarkan buku Elementary Tagalog.",
            "Kumpletong panimulang kurso sa Tagalog batay sa aklat na Elementary Tagalog.",
        ),
        "source": {
            "title": "Elementary Tagalog",
            "authors": ["Jiedson R. Domigpe", "Nenita Pambid Domingo"],
            "publisher": "Tuttle Publishing",
            "isbn": "978-0-8048-4117-7",
        },
        "cover": "assets/cover.jpg",
        "assetIndex": {"path": "assets/index.json", "sha256": sha256_file(asset_index_path)},
        "sourceAudit": {"path": "source-audit.json", "sha256": sha256_file(audit_path)},
        "units": unit_refs,
        "lessons": lesson_refs,
    }
    course_index_path = course_dir / "index.json"
    write_json(course_index_path, course_index)

    lesson_index_path = output / "lesson" / "index.json"
    write_json(
        lesson_index_path,
        {
            "schemaVersion": SCHEMA_VERSION,
            "courses": [
                {
                    "id": COURSE_ID,
                    "path": f"{COURSE_ID}/index.json",
                    "sha256": sha256_file(course_index_path),
                    "lessonCount": 24,
                    "unitCount": 8,
                    "title": course_index["title"],
                }
            ],
        },
    )
    write_json(
        output / "manifest.json",
        {
            "schemaVersion": SCHEMA_VERSION,
            "contentBase": "https://raw.githubusercontent.com/HamzahSk/rolang-server/data/",
            "lessons": {"index": "lesson/index.json", "sha256": sha256_file(lesson_index_path)},
            "stories": {"path": "storie/", "status": "reserved"},
        },
    )
    (output / "storie" / ".gitkeep").touch()
    print(
        f"Generated 24 lessons, 8 unit documents, {len(inventory)} images, "
        f"and {len(extractor.audit_documents)} audited XHTML sources."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("epub", type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--english-indonesian", type=Path, required=True, help="Unpacked Argos en_id model")
    parser.add_argument("--tagalog-english", type=Path, required=True, help="Unpacked Argos tl_en model")
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
