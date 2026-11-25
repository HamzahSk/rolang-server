#!/usr/bin/env python3
"""Turn the extracted Elementary Tagalog lessons into semantic lesson content.

The EPUB importer intentionally keeps a lossless, fairly literal representation.
This second pass keeps that source text while separating vocabulary, dialogues,
examples, explanations, and exercises for the Android lesson reader.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET
from zipfile import ZipFile


COURSE_ID = "elementary-tagalog-1"
LESSON_GLOB = "[0-9][0-9]-*.json"
HEADING_CLASSES = {
    "textStyle38",
    "textStyle40",
    "textStyle41",
    "textStyle43",
    "textStyle45",
    "textStyle52",
    "bc",
    "bc1",
}
TAGALOG_CLASSES = {"textStyle20", "textStyle20ud", "textStyle34", "ud"}
REMOVABLE_STRUCTURAL_LABELS = {
    "overview",
    "objectives",
    "vocabulary",
    "dialogue",
    "activities",
    "grammar",
    "practice",
}


OBJECTIVE_TRANSLATIONS = {
    "• Ask questions using the interrogative pronouns sino (who) and ano (what)":
        "• Mengajukan pertanyaan dengan kata ganti tanya sino (siapa) dan ano (apa)",
    "• Respond to inquiries using short and long responses":
        "• Menjawab pertanyaan dengan jawaban pendek maupun lengkap",
    "• Construct identificational and predicational statements":
        "• Menyusun kalimat identifikasi dan kalimat predikatif",
    "• Introduce yourself and others": "• Memperkenalkan diri sendiri dan orang lain",
    "• Ask and respond to questions eliciting basic biographical information":
        "• Bertanya dan menjawab informasi biografis dasar",
    "• Ask and respond to yes-no questions": "• Mengajukan dan menjawab pertanyaan ya/tidak",
    "• Ask and respond to questions about your likes and dislikes":
        "• Bertanya dan menjawab tentang hal yang disukai dan tidak disukai",
    "• Talk about your favorite sports and people":
        "• Berbicara tentang olahraga dan orang favorit",
    "• Ask and answer questions about one’s age": "• Bertanya dan menjawab tentang usia seseorang",
    "• Describe family relationships using kinship terms":
        "• Menjelaskan hubungan keluarga dengan istilah kekerabatan",
    "• Introduce or talk about family members": "• Memperkenalkan atau membicarakan anggota keluarga",
    "• Describe people using ma-adjectives": "• Mendeskripsikan orang dengan kata sifat berawalan ma-",
    "• Describe people using the naka- prefix": "• Mendeskripsikan orang dengan awalan naka-",
    "• Read and write short biographical texts": "• Membaca dan menulis teks biografi singkat",
    "• Ask and answer basic biographical questions about people":
        "• Mengajukan dan menjawab pertanyaan biografis dasar tentang seseorang",
    "• Be able to talk about daily activities": "• Berbicara tentang kegiatan sehari-hari",
    "• Be able to talk about past and future activities":
        "• Berbicara tentang kegiatan masa lalu dan masa depan",
    "• Be able to talk about one’s hobbies and leisure-time activities":
        "• Berbicara tentang hobi dan kegiatan waktu luang",
    "• Be able to express preferences regarding activities":
        "• Menyatakan pilihan atau kesukaan terhadap suatu kegiatan",
    "• Use appropriate expressions in the context of shopping":
        "• Menggunakan ungkapan yang sesuai saat berbelanja",
    "• Engage in small talk about shopping": "• Melakukan percakapan ringan tentang belanja",
    "• Describe specific location of an object": "• Menjelaskan letak spesifik suatu benda",
    "• List the different objects in the house": "• Menyebutkan berbagai benda di rumah",
    "• Express preference about various places": "• Menyatakan tempat yang disukai",
    "• Describe and provide basic information about different locations":
        "• Mendeskripsikan dan memberi informasi dasar tentang berbagai tempat",
    "• Give and ask for directions": "• Memberi dan menanyakan arah",
    "• Express simple requests and commands": "• Menyampaikan permintaan dan perintah sederhana",
    "• Talk about the physical symptoms of common ailments":
        "• Membicarakan gejala fisik penyakit yang umum",
    "• Develop the language skills to suggest possible remedies":
        "• Mengembangkan kemampuan untuk menyarankan pengobatan",
    "• Use helping verbs and negative commands in a sentence":
        "• Menggunakan kata kerja bantu dan perintah negatif dalam kalimat",
    "• Use appropriate expressions in the context of a doctor’s consultation":
        "• Menggunakan ungkapan yang sesuai saat berkonsultasi dengan dokter",
    "• Describe minor aches and pains": "• Menjelaskan rasa sakit dan keluhan ringan",
    "• Talk about medicinal plants and other non-traditional form of medication":
        "• Membicarakan tanaman obat dan bentuk pengobatan nontradisional lainnya",
    "• Express different things that one wants, needs, or does not want to do":
        "• Menyatakan hal yang ingin, perlu, atau tidak ingin dilakukan",
    "• Order food at a restaurant": "• Memesan makanan di restoran",
    "• Express preferences regarding food and drink": "• Menyatakan pilihan makanan dan minuman",
    "• Make requests": "• Menyampaikan permintaan",
    "• Give and follow instructions": "• Memberi dan mengikuti petunjuk",
    "• Talk about common food preparation techniques in Filipino cooking":
        "• Membicarakan teknik umum menyiapkan makanan dalam masakan Filipina",
    "• Talk about a previous vacation": "• Menceritakan liburan yang telah berlalu",
    "• Describe places": "• Mendeskripsikan tempat",
    "• Reserve a plane ticket": "• Memesan tiket pesawat",
    "• Discuss some specific holidays and festivities":
        "• Membahas hari raya dan perayaan tertentu",
    "• Say dates": "• Menyebutkan tanggal",
    "• Give detailed description of events": "• Mendeskripsikan peristiwa secara terperinci",
    "• Express reaction/feeling about events": "• Menyatakan reaksi atau perasaan terhadap peristiwa",
    "• Narrate events in detail": "• Menceritakan peristiwa secara terperinci",
    "• Familiarize yourself with some popular Filipino legends":
        "• Mengenal beberapa legenda Filipina yang populer",
    "• Use locative verbs": "• Menggunakan kata kerja lokatif",
    "• Narrate a story": "• Menceritakan sebuah kisah",
    "• Give and understand a summary of a movie": "• Menyampaikan dan memahami ringkasan film",
    "• Express your response to a movie": "• Menyatakan tanggapan terhadap film",
    "• Understand a Filipino song": "• Memahami sebuah lagu Filipina",
    "• Express your abilities or what you can or cannot do":
        "• Menyatakan kemampuan atau hal yang dapat dan tidak dapat dilakukan",
}


def clean_text(value: str) -> str:
    value = value.replace("\u00a0", " ").replace("\u200b", "")
    value = re.sub(r"[ \t\f\v]+", " ", value)
    value = re.sub(r" *\n *", "\n", value)
    return value.strip()


def tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


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
        if set(child.attrib.get("class", "").split()) & TAGALOG_CLASSES:
            value = element_text(child)
            if value and value not in fragments:
                fragments.append(value)
    return clean_text(" ".join(fragments))


def words(value: str) -> list[str]:
    return re.findall(r"[^\W\d_]+(?:['’][^\W\d_]+)?", value, re.UNICODE)


def lesson_source_metadata(epub: Path) -> dict[int, dict[str, dict[str, Any]]]:
    result: dict[int, dict[str, dict[str, Any]]] = {}
    with ZipFile(epub) as archive:
        for number in range(1, 25):
            root = ET.fromstring(archive.read(f"OEBPS/Text/Lesson{number}.xhtml"))
            metadata: dict[str, dict[str, Any]] = defaultdict(lambda: {"heading": False, "tagalog": ""})
            for element in root.iter():
                if tag(element) not in {"p", "h4", "h5", "h6", "blockquote", "td", "th"}:
                    continue
                value = element_text(element)
                if not value:
                    continue
                classes = set(element.attrib.get("class", "").split())
                for child in element.iter():
                    classes.update(child.attrib.get("class", "").split())
                item = metadata[value]
                item["heading"] = item["heading"] or bool(classes & HEADING_CLASSES) or tag(element) in {"h4", "h5", "h6"}
                fragment = tagalog_fragments(element)
                if len(words(fragment)) > len(words(item["tagalog"])):
                    item["tagalog"] = fragment
            result[number] = dict(metadata)
    return result


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clone(value: Any) -> Any:
    return copy.deepcopy(value)


def source(block: dict[str, Any]) -> str:
    return block.get("text", {}).get("sourceText", "").strip()


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold().rstrip(":")


def text_object(source_text: str, indonesian: str, language: str = "en") -> dict[str, str]:
    return {"sourceLanguage": language, "sourceText": source_text, "id": indonesian}


def heading_translation(source_text: str, current: str) -> str:
    plain = re.sub(r"\s+", " ", source_text.strip()).rstrip(":")
    exact = {
        "Overview": "Pengantar",
        "Objectives": "Tujuan Pembelajaran",
        "Vocabulary": "Kosakata",
        "Activities": "Latihan",
        "Grammar": "Materi Tata Bahasa",
        "Practice": "Latihan",
        "Definition of Terms": "Definisi Istilah",
        "Examining Form": "Menganalisis Bentuk",
        "Grammar Presentation": "Penyajian Tata Bahasa",
        "Grammar Notes": "Catatan Tata Bahasa",
        "Dialogue Comprehension": "Pemahaman Dialog",
        "Reading Comprehension": "Pemahaman Bacaan",
        "Supplemental Vocabulary": "Kosakata Tambahan",
        "EXAMPLE": "Contoh",
        "EXAMPLES": "Contoh",
        "Summary": "Ringkasan",
    }
    if plain in exact:
        return exact[plain]
    match = re.fullmatch(r"An Overview of Lesson (\d+)", plain, re.I)
    if match:
        return f"Pengantar Pelajaran {match.group(1)}"
    match = re.match(r"^(Activity)\s+(\d+)(.*)$", plain, re.I)
    if match:
        suffix = match.group(3).strip()
        return f"Aktivitas {match.group(2)}" + (f": {suffix.lstrip(':').strip()}" if suffix else "")
    replacements = (
        ("Speaking Practice", "Latihan Berbicara"),
        ("Reading Practice", "Latihan Membaca"),
        ("Writing Practice", "Latihan Menulis"),
        ("Listening Practice", "Latihan Menyimak"),
        ("Writing and Speaking Practice", "Latihan Menulis dan Berbicara"),
        ("Writing and Reading Practice", "Latihan Menulis dan Membaca"),
        ("Interrogative Pronoun", "Kata Ganti Tanya"),
        ("Grammar Presentation", "Penyajian Tata Bahasa"),
        ("Grammar Notes", "Catatan Tata Bahasa"),
        ("Dialogue", "Dialog"),
        ("Reading Text", "Teks Bacaan"),
        ("Definition of Terms", "Definisi Istilah"),
    )
    translated = current.strip()
    if not translated or translated == source_text:
        translated = plain
    for english, indonesian in replacements:
        translated = re.sub(re.escape(english), indonesian, translated, flags=re.I)
    translated = translated.replace("Objeksi", "Tujuan").replace("Pronouns", "Kata ganti")
    translated = translated.replace("Markers", "Penanda").replace("Adverbs", "Kata keterangan")
    return translated.rstrip(":")


def enrich_text(value: Any, metadata: dict[str, dict[str, Any]]) -> None:
    if isinstance(value, dict):
        if isinstance(value.get("sourceText"), str) and isinstance(value.get("id"), str):
            source_text = value["sourceText"]
            if source_text in OBJECTIVE_TRANSLATIONS:
                value["id"] = OBJECTIVE_TRANSLATIONS[source_text]
            item = metadata.get(source_text, {})
            fragment = item.get("tagalog", "")
            source_words = words(source_text)
            fragment_words = words(fragment)
            if (
                fragment
                and value.get("sourceLanguage") != "fil"
                and len(fragment_words) >= max(2, len(source_words) // 4)
                and fragment != source_text
            ):
                value["tagalog"] = fragment
        for child in value.values():
            enrich_text(child, metadata)
    elif isinstance(value, list):
        for child in value:
            enrich_text(child, metadata)


def annotate_blocks(document: dict[str, Any], metadata: dict[str, dict[str, Any]]) -> None:
    for section in document["sections"]:
        for block in section["blocks"]:
            if block.get("type") != "text":
                continue
            source_text = source(block)
            meta = metadata.get(source_text, {})
            if meta.get("heading") and len(source_text) <= 240:
                block["style"] = "heading"


def title_from(text: dict[str, Any], fallback: str = "Bagian") -> dict[str, Any]:
    result = clone(text)
    result["id"] = heading_translation(result.get("sourceText", fallback), result.get("id", fallback))
    return result


def generic_title(source_text: str, indonesian: str) -> dict[str, Any]:
    return text_object(source_text, indonesian)


def is_duplicate_title(block: dict[str, Any], section: dict[str, Any]) -> bool:
    if block.get("type") != "text":
        return False
    candidates = {normalized(section["title"].get("sourceText", "")), normalized(section["title"].get("id", ""))}
    return normalized(source(block)) in candidates


def make_section(section_type: str, title: dict[str, Any], blocks: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": section_type, "title": title_from(title), "blocks": blocks}


def introduction_section(document: dict[str, Any], section: dict[str, Any]) -> dict[str, Any]:
    blocks = section["blocks"]
    overview_title = next(
        (block["text"] for block in blocks if block.get("type") == "text" and source(block).lower().startswith("an overview")),
        section["title"],
    )
    objective_sources = {item["sourceText"] for item in document["objectives"]}
    outline: list[dict[str, Any]] = []
    outline_layouts: list[dict[str, Any]] = []
    for block in blocks:
        if block.get("type") != "text":
            item = clone(block)
            if item.get("type") == "table":
                item["role"] = "outline"
            outline_layouts.append(item)
            continue
        value = source(block)
        if value == overview_title.get("sourceText") or normalized(value) == "objectives" or value in objective_sources:
            continue
        outline.append(clone(block["text"]))
    result_blocks = [{"type": "list", "style": "objectives", "items": clone(document["objectives"])}]
    if outline:
        result_blocks.append({"type": "list", "style": "outline", "items": outline})
    result_blocks.extend(outline_layouts)
    return make_section("INTRODUCTION", overview_title, result_blocks)


def vocabulary_table(block: dict[str, Any]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    entries: list[dict[str, Any]] = []
    group_title: dict[str, Any] | None = None

    def flush(preserve_orphan_title: bool = False) -> None:
        nonlocal entries, group_title
        if entries:
            item: dict[str, Any] = {"type": "vocabulary", "entries": entries}
            if group_title:
                item["title"] = title_from(group_title)
            output.append(item)
            entries = []
            group_title = None
        elif preserve_orphan_title and group_title:
            output.append({"type": "text", "style": "heading", "text": title_from(group_title)})
            group_title = None

    for row in block["rows"]:
        cells = row["cells"]
        if len(cells) == 1:
            flush(preserve_orphan_title=True)
            group_title = clone(cells[0])
        elif len(cells) == 2:
            entries.append({"term": clone(cells[0]), "meaning": clone(cells[1])})
        else:
            flush(preserve_orphan_title=True)
            output.append({"type": "table", "role": "vocabulary-reference", "rows": [clone(row)]})
    flush(preserve_orphan_title=True)
    return output or [{"type": "table", "role": "vocabulary-reference", "rows": clone(block["rows"])}]


def vocabulary_sections(section: dict[str, Any]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for block in section["blocks"]:
        if is_duplicate_title(block, section):
            continue
        if block.get("type") == "table":
            blocks.extend(vocabulary_table(block))
        elif block.get("type") == "text":
            item = clone(block)
            if normalized(source(item)).startswith("supplemental vocabulary"):
                item["style"] = "heading"
                item["text"]["id"] = "Kosakata Tambahan"
            blocks.append(item)
        else:
            blocks.append(clone(block))
    return [make_section("VOCABULARY", section["title"], blocks)]


def speaker_name(cell: dict[str, Any]) -> str | None:
    value = cell.get("sourceText", "").strip()
    if not value.endswith(":"):
        return None
    name = value[:-1].strip()
    if not name or len(name) > 40 or len(words(name)) > 5:
        return None
    return name


def is_dialogue_table(block: dict[str, Any]) -> bool:
    if block.get("type") != "table" or len(block.get("rows", [])) < 2:
        return False
    rows = block["rows"]
    dialogue_rows = sum(1 for row in rows if len(row["cells"]) == 2 and speaker_name(row["cells"][0]))
    return dialogue_rows >= 2 and dialogue_rows / len(rows) >= 0.6


def dialogue_blocks(block: dict[str, Any]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    turns: list[dict[str, Any]] = []

    def flush() -> None:
        nonlocal turns
        if turns:
            output.append({"type": "dialogue", "turns": turns})
            turns = []

    for row in block["rows"]:
        cells = row["cells"]
        name = speaker_name(cells[0]) if len(cells) == 2 else None
        if name:
            turns.append({"speaker": name, "speakerText": clone(cells[0]), "text": clone(cells[1])})
        else:
            flush()
            output.append({"type": "table", "role": "dialogue-context", "rows": [clone(row)]})
    flush()
    return output


def looks_blank(value: str) -> bool:
    return bool(value) and not re.search(r"[^\W_]", value, re.UNICODE)


def exercise_role(value: str) -> str:
    lowered = value.strip().lower()
    if re.match(r"^(answer|response|a:)\b", lowered):
        return "answer"
    if re.match(r"^\d+[.)]\s*", value) or "?" in value:
        return "question"
    if re.match(
        r"^(work|read|write|complete|using|listen|interview|answer|fill|choose|match|identify|"
        r"underline|circle|discuss|look|refer|ask|take|practice|give|name|describe|translate|form)\b",
        lowered,
    ):
        return "instruction"
    return "content"


def exercise_block(block: dict[str, Any], removed: Counter[str]) -> list[dict[str, Any]]:
    if block.get("type") == "image":
        return [clone(block)]
    if block.get("type") == "table":
        if is_dialogue_table(block):
            return dialogue_blocks(block)
        return [{"type": "exercise", "role": "worksheet", "rows": clone(block["rows"])}]
    value = source(block)
    if looks_blank(value):
        removed["blankFragments"] += 1
        return []
    item = {"type": "exercise", "role": exercise_role(value), "text": clone(block["text"])}
    return [item]


def exercise_heading(block: dict[str, Any], family: str) -> bool:
    if block.get("type") != "text":
        return False
    value = source(block)
    if family == "activity":
        return bool(re.match(r"^Activity\s+\d+\b", value, re.I))
    return bool(
        re.match(r"^[IVX]+\.\s+.*Practice\b", value, re.I)
        or normalized(value) in {"dialogue comprehension", "reading comprehension"}
    )


def split_exercises(
    section: dict[str, Any], family: str, removed: Counter[str], initial_blocks: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    current_title = section["title"]
    current_blocks: list[dict[str, Any]] = list(initial_blocks or [])

    def flush() -> None:
        nonlocal current_blocks
        if current_blocks:
            output.append(make_section("EXERCISES", current_title, current_blocks))
            current_blocks = []

    for block in section["blocks"]:
        if is_duplicate_title(block, section) or normalized(source(block)) in {"activities", "practice"}:
            removed["duplicateHeadings"] += 1
            continue
        if exercise_heading(block, family):
            flush()
            current_title = block["text"]
            continue
        current_blocks.extend(exercise_block(block, removed))
    flush()
    return output


def split_dialogue(section: dict[str, Any], removed: Counter[str]) -> list[dict[str, Any]]:
    main_blocks: list[dict[str, Any]] = []
    exercise_blocks: list[dict[str, Any]] = []
    comprehension_title: dict[str, Any] | None = None
    in_comprehension = False
    for block in section["blocks"]:
        value = normalized(source(block))
        if value in {"dialogue comprehension", "reading comprehension"}:
            in_comprehension = True
            comprehension_title = block["text"]
            continue
        if not in_comprehension and is_duplicate_title(block, section):
            removed["duplicateHeadings"] += 1
            continue
        target = exercise_blocks if in_comprehension else main_blocks
        if in_comprehension:
            target.extend(exercise_block(block, removed))
        elif is_dialogue_table(block):
            target.extend(dialogue_blocks(block))
        else:
            target.append(clone(block))
    is_reading = normalized(section["title"].get("sourceText", "")).startswith("reading")
    output = [make_section("LEARNING_MATERIAL" if is_reading else "DIALOGUE", section["title"], main_blocks)]
    if exercise_blocks:
        output.append(
            make_section(
                "EXERCISES",
                comprehension_title or generic_title("Comprehension", "Pemahaman"),
                exercise_blocks,
            )
        )
    return output


def is_examples_heading(value: str) -> bool:
    return normalized(value) in {"example", "examples"}


def is_summary(value: str) -> bool:
    return bool(re.match(r"^[→\-–— ]*(to summarize|in summary|summary)\b", value.strip(), re.I))


def grammar_heading(block: dict[str, Any]) -> bool:
    if block.get("type") != "text":
        return False
    value = source(block)
    plain = normalized(value)
    if is_examples_heading(value):
        return True
    if plain in {"grammar", "definition of terms", "examining form", "grammar presentation", "grammar notes"}:
        return True
    if block.get("style") == "heading":
        return True
    return bool(re.match(r"^[IVX]+\.\s+[^?]{2,180}$", value))


def likely_explanation(block: dict[str, Any]) -> bool:
    if block.get("type") != "text":
        return False
    text = block["text"]
    return (
        not text.get("tagalog")
        and text.get("sourceLanguage") == "en"
        and len(source(block)) > 65
    )


def semantic_reference(block: dict[str, Any], role: str = "reference") -> dict[str, Any]:
    result = clone(block)
    if result.get("type") == "table":
        result["role"] = role
    return result


def split_grammar(section: dict[str, Any], removed: Counter[str]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    current_type = "LEARNING_MATERIAL"
    current_title = section["title"]
    context_title = section["title"]
    current_blocks: list[dict[str, Any]] = []

    def flush() -> None:
        nonlocal current_blocks
        if current_blocks:
            output.append(make_section(current_type, current_title, current_blocks))
            current_blocks = []

    for block in section["blocks"]:
        value = source(block)
        if is_duplicate_title(block, section) or normalized(value) == "grammar":
            removed["duplicateHeadings"] += 1
            continue
        if is_summary(value):
            flush()
            output.append(make_section("SUMMARY", generic_title("Summary", "Ringkasan"), [clone(block)]))
            current_type = "LEARNING_MATERIAL"
            current_title = context_title
            continue
        if grammar_heading(block):
            previous_title = current_title
            had_content = bool(current_blocks)
            flush()
            if is_examples_heading(value):
                current_type = "EXAMPLES"
                current_title = block["text"]
            else:
                current_type = "LEARNING_MATERIAL"
                current_title = block["text"]
                context_title = block["text"]
            if (
                not had_content
                and previous_title is not section["title"]
                and previous_title.get("sourceText") != current_title.get("sourceText")
            ):
                current_blocks.append({"type": "text", "style": "heading", "text": clone(previous_title)})
            continue
        if current_type == "EXAMPLES" and likely_explanation(block):
            flush()
            current_type = "LEARNING_MATERIAL"
            current_title = context_title
        if current_type == "EXAMPLES":
            if block.get("type") == "text":
                current_blocks.append({"type": "example", "items": [clone(block["text"])]})
            elif block.get("type") == "table":
                current_blocks.append({"type": "example", "rows": clone(block["rows"])})
            else:
                current_blocks.append(clone(block))
        else:
            current_blocks.append(semantic_reference(block))
    flush()
    return output


def text_inventory(value: Any) -> Counter[str]:
    result: Counter[str] = Counter()
    if isinstance(value, dict):
        if isinstance(value.get("sourceText"), str):
            result[value["sourceText"]] += 1
        for child in value.values():
            result.update(text_inventory(child))
    elif isinstance(value, list):
        for child in value:
            result.update(text_inventory(child))
    return result


def assign_section_ids(document: dict[str, Any]) -> None:
    seen: Counter[str] = Counter()
    for index, section in enumerate(document["sections"], start=1):
        title = section["title"].get("sourceText", section["type"])
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower().replace("’", "'")).strip("-")[:48]
        slug = slug or section["type"].lower()
        seen[slug] += 1
        suffix = f"-{seen[slug]}" if seen[slug] > 1 else ""
        section["id"] = f"lesson-{document['order']:02d}-{index:02d}-{slug}{suffix}"


def structure_lesson(document: dict[str, Any], metadata: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if document.get("structureVersion") == 2:
        return document
    before = text_inventory(document["sections"])
    enrich_text(document, metadata)
    annotate_blocks(document, metadata)
    removed: Counter[str] = Counter()
    output: list[dict[str, Any]] = []
    for section in document["sections"]:
        kind = section["type"]
        if kind == "OVERVIEW":
            output.append(introduction_section(document, section))
        elif kind == "VOCABULARY":
            output.extend(vocabulary_sections(section))
        elif kind == "DIALOGUE":
            output.extend(split_dialogue(section, removed))
        elif kind == "ACTIVITY":
            output.extend(split_exercises(section, "activity", removed))
        elif kind == "GRAMMAR":
            output.extend(split_grammar(section, removed))
        elif kind == "PRACTICE":
            output.extend(split_exercises(section, "practice", removed))
        else:
            output.append(clone(section))
    document["sections"] = [section for section in output if section["blocks"]]
    assign_section_ids(document)
    after = text_inventory(document["sections"])
    document_titles = {normalized(value) for value in document.get("title", {}).values() if isinstance(value, str)}
    missing = sorted(
        text
        for text in before
        if text.strip()
        and text not in after
        and not looks_blank(text)
        and normalized(text) not in REMOVABLE_STRUCTURAL_LABELS
        and normalized(text) not in document_titles
    )
    if missing:
        raise ValueError(f"{document['id']}: source items were lost: {missing[:5]}")
    section_counts = Counter(section["type"] for section in document["sections"])
    block_counts = Counter(block["type"] for section in document["sections"] for block in section["blocks"])
    document["structureVersion"] = 2
    document["contentAudit"] = {
        "sourceTextItemsBefore": sum(before.values()),
        "sourceTextItemsAfter": sum(after.values()),
        "uniqueSourceItemsPreserved": len(set(before) & set(after)),
        "duplicateHeadingsRemoved": removed["duplicateHeadings"],
        "blankFragmentsRemoved": removed["blankFragments"],
        "sectionTypes": dict(sorted(section_counts.items())),
        "blockTypes": dict(sorted(block_counts.items())),
    }
    return document


def update_indexes(root: Path, lessons: Iterable[Path]) -> None:
    course_path = root / "lesson" / COURSE_ID / "index.json"
    course = read_json(course_path)
    lesson_by_path = {path.name: read_json(path) for path in lessons}
    for reference in course["lessons"]:
        document = lesson_by_path[reference["path"]]
        reference["title"] = document["title"]
        reference["summary"] = document["summary"]
        reference["objectives"] = document["objectives"]
        reference["assets"] = document["assets"]
        reference["sha256"] = digest(root / "lesson" / COURSE_ID / reference["path"])
    write_json(course_path, course)

    lesson_index_path = root / "lesson" / "index.json"
    lesson_index = read_json(lesson_index_path)
    course_reference = lesson_index["courses"][0]
    course_reference["sha256"] = digest(course_path)
    write_json(lesson_index_path, lesson_index)

    manifest_path = root / "manifest.json"
    manifest = read_json(manifest_path)
    manifest["lessons"]["sha256"] = digest(lesson_index_path)
    write_json(manifest_path, manifest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("epub", type=Path, help="Original Elementary Tagalog 1 EPUB")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    epub = args.epub.resolve()
    metadata = lesson_source_metadata(epub)
    lessons = sorted((root / "lesson" / COURSE_ID).glob(LESSON_GLOB))
    if len(lessons) != 24:
        raise SystemExit(f"Expected 24 lesson files, found {len(lessons)}")
    changed = 0
    for path in lessons:
        document = read_json(path)
        previous = json.dumps(document, ensure_ascii=False, sort_keys=True)
        structured = structure_lesson(document, metadata[document["order"]])
        if json.dumps(structured, ensure_ascii=False, sort_keys=True) != previous:
            write_json(path, structured)
            changed += 1
    update_indexes(root, lessons)
    print(f"Structured {len(lessons)} lessons; changed {changed} lesson files.")


if __name__ == "__main__":
    main()
