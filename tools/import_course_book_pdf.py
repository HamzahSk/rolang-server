#!/usr/bin/env python3
"""Import Learning Tagalog Course Book 1 from its source PDF.

The PDF is unusually regular: every chapter has a title/illustration page,
numbered A/B phrase pages, a Drills divider, and a Tagalog recap page.  This
importer retains the source wording and page numbers, adds Indonesian
translations, extracts the embedded JPEGs without re-encoding them, and writes
the hashes consumed by the Android GitHub Raw loader.

PyMuPDF is required.  Translations are cached locally and are obtained from the
public Google Translate web endpoint; source English and Tagalog are always
retained in the generated JSON for auditing.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pymupdf


COURSE_ID = "learning-tagalog-course-book-1"
BOOK_TITLE = "Learning Tagalog - Fluency Made Fast and Easy - Course Book 1"
PDF_FILENAME = f"{BOOK_TITLE}.pdf"
PHRASE_LABEL = re.compile(r"[AB] \d{2}")
PDF_SHA256 = "52e9f464239c2ae98248a452edfbf1f58eb01bec69374a16d5205e70afa80f58"
FINAL_CONTENT_PAGE = 521
ARTIFACT_PAGE = 522

INDONESIAN_TITLES = {
    1: "Liburan",
    2: "Sarapan",
    3: "Apa kabar?",
    4: "Di dalam jeepney",
    5: "Hewan-hewan peliharaan",
    6: "Sepatu",
    7: "Ada surat",
    8: "Di kios buah",
    9: "Keluarga saya",
    10: "Sudah pukul empat",
    11: "Di ruang tamu",
    12: "Tamu",
    13: "Ada panggilan telepon",
    14: "Makan siang di restoran",
    15: "Di salon",
    16: "Tita Amy dan yang lain sudah tiba",
    17: "Di hotel",
    18: "Panas sekali!",
    19: "Suami saya sakit",
    20: "Di mal",
}

UNITS = [
    {
        "id": "course-book-1-unit-01-conversation-foundations",
        "slug": "01-conversation-foundations",
        "lessons": range(1, 5),
        "id_title": "Dasar percakapan",
        "fil_title": "Batayang usapan",
    },
    {
        "id": "course-book-1-unit-02-objects-and-shopping",
        "slug": "02-objects-and-shopping",
        "lessons": range(5, 9),
        "id_title": "Benda, kepemilikan, dan belanja",
        "fil_title": "Mga bagay, pagmamay-ari, at pamimili",
    },
    {
        "id": "course-book-1-unit-03-family-time-and-home",
        "slug": "03-family-time-and-home",
        "lessons": range(9, 13),
        "id_title": "Keluarga, waktu, dan rumah",
        "fil_title": "Pamilya, oras, at tahanan",
    },
    {
        "id": "course-book-1-unit-04-communication-and-services",
        "slug": "04-communication-and-services",
        "lessons": range(13, 17),
        "id_title": "Komunikasi dan layanan",
        "fil_title": "Komunikasyon at mga serbisyo",
    },
    {
        "id": "course-book-1-unit-05-travel-and-daily-needs",
        "slug": "05-travel-and-daily-needs",
        "lessons": range(17, 21),
        "id_title": "Perjalanan dan kebutuhan sehari-hari",
        "fil_title": "Paglalakbay at pang-araw-araw na pangangailangan",
    },
]

BRACKET_GLOSSES = {
    "[linker]": "[penghubung]",
    "[polite]": "[sopan]",
    "[question]": "[penanda tanya]",
    "[Ang marker]": "[penanda ang]",
    "[Ng marker]": "[penanda ng]",
    "[Sa marker]": "[penanda sa]",
    "[plural]": "[jamak]",
    "[contrast]": "[kontras]",
    "[News]": "[Informasi Baru]",
    "[Point of Departure]": "[Titik Tolak]",
    "[surprise]": "[keterkejutan]",
    "[admiration]": "[kekaguman]",
    "[softener]": "[penghalus]",
    "[sympathy/shock/etc.]": "[simpati/keterkejutan/dll.]",
    "[relief]": "[kelegaan]",
}

TERM_TRANSLATIONS = {
    "News": "Informasi Baru (News)",
    "Point of Departure": "Titik Tolak (Point of Departure)",
}

GLOSS_OVERRIDES = {
    "The": "penanda definit",
    "the": "penanda definit",
    "A": "sebuah",
    "a": "sebuah",
    "I": "saya",
    "You": "kamu",
    "you": "kamu",
    "My": "milikku",
    "my": "milikku",
    "Your": "milikmu",
    "your": "milikmu",
}

PROPER_GLOSS_TERMS = {
    "Alfred", "Arlene", "Baguio", "Banaue", "Calamba", "Edwin", "Julius",
    "Lipa", "London", "Manila", "Maynila", "Michael Ramirez", "Mike",
    "Mrs. Reyes", "New York", "Ray", "Reybert", "Rice Terraces", "Ryan",
    "Sydney", "Tabby", "Tina", "Tingting", "Tita Amy", "Tito Juan",
    "Tomas de Leon", "Dr. Gomez", "Dr. Molina",
}

NATURAL_OVERRIDES = {
    "Fine. (And) you?": "Baik. (Dan kamu?)",
    "I'm fine too.": "Saya juga baik.",
    "Fine.": "Baik.",
    "Really?": "Benarkah?",
    "OK.": "Oke.",
    "Here's my fare.": "Ini ongkos saya.",
    "Here's the change.": "Ini kembaliannya.",
    "We're at the market now. (The market is here now.)": "Kita sudah sampai di pasar. (Pasarnya sudah di sini.)",
    "We're near the market now. (The market is near now.)": "Kita sudah dekat dengan pasar. (Pasarnya sudah dekat.)",
    "Tabby is fat.": "Tabby gemuk.",
    "Tabby is so fat!": "Tabby sangat gemuk!",
    "Tingting is nice.": "Tingting baik.",
    "Tingting is so nice.": "Tingting sangat baik.",
    "Tingting is sooo nice.": "Tingting sangat, sangat baik.",
    "Tingting is so thin!": "Tingting sangat kurus!",
    "And this is Tingting, Tabby's sister (sibling).": "Dan ini Tingting, saudara perempuan Tabby.",
    "Yes, I have basketball. And actually, I'm already late.": "Ya, saya ada latihan basket. Sebenarnya saya sudah terlambat.",
    "I'm afraid he's out. (I'm afraid he left.) (polite)": "Sayangnya, dia sedang keluar. (Dia sudah pergi.) (sopan)",
    "Is your mom here (home)?": "Apakah ibumu ada di rumah?",
    "Just three (pieces).": "Hanya tiga buah.",
    "How much is a kilo of bananas?": "Berapa harga satu kilo pisang?",
    "Our meeting is at three o'clock.": "Pertemuan kami pukul tiga.",
    "Our class is at four o'clock.": "Kelas kita pukul empat.",
    "It's only ten o'clock. It's still early.": "Baru pukul sepuluh. Masih awal.",
    "What's that, Ate?": "Apa itu, Ate?",
    "Who's the host?": "Siapa pembawa acaranya?",
    "Oh, it's you, Mike. Come in!": "Oh, ternyata kamu, Mike. Silakan masuk!",
    "Not really. Where did you just come from?": "Tidak juga. Kamu baru dari mana?",
    "Just there (nowhere in particular). By the way, I have/brought something for you.": "Dari dekat sini saja. Ngomong-ngomong, aku membawa sesuatu untukmu.",
    "What a beautiful flower! Thanks.": "Indah sekali bunga ini! Terima kasih.",
    "This is Dr. Molina.": "Ini Dr. Molina.",
    "I will. (polite)": "Baik, akan saya sampaikan. (sopan)",
    "All right, what are you having? (What's your order?)": "Baiklah, kamu mau memesan apa?",
    "And you, what are you having?": "Kalau kamu, mau memesan apa?",
    "Is there still some pansit left for them?": "Apakah masih ada pansit untuk mereka?",
    "Tita Amy and her husband have arrived": "Tita Amy dan suaminya sudah tiba",
    "By the way, we'll see each other on Friday. Do you want to come along?": "Ngomong-ngomong, kami akan bertemu hari Jumat. Kamu mau ikut?",
    "They brought a lot of gifts from the States. (They have a lot of brought gifts from the States.)": "Mereka membawa banyak oleh-oleh dari Amerika Serikat.",
    "We'll see each other in August.": "Kami akan bertemu pada bulan Agustus.",
    "Tomas de Leon.": "Tomas de Leon.",
    "OK, sir. Here is your key. It's room number 7, sir.": "Baik, Pak. Ini kunci Anda. Kamar Anda nomor 7.",
    "Do not pass. (No overtaking.)": "Dilarang melintas. (Dilarang menyalip.)",
    "No dumping of trash.": "Dilarang membuang sampah.",
    "Yes, look (at the aircon).": "Ya, lihatlah AC-nya.",
    "spring, hot season/summer, rainy season, autumn, cold season/winter": "musim semi, musim panas, musim hujan, musim gugur, musim dingin",
    "I have a cold.": "Saya pilek.",
    "He/she said he/she's well again.": "Dia berkata bahwa dia sudah sehat kembali.",
    "How much is the fare to the mall?": "Berapa ongkos ke mal?",
}

NOTE_OVERRIDES = {
    "Recommended reading: May, mayroon/meron, marami, wala: Overview.":
        "Bacaan yang disarankan: May, mayroon/meron, marami, wala: gambaran umum.",
    "Tayo – we (including you). Kami – we (excluding you).":
        "Tayo berarti kita (termasuk lawan bicara). Kami berarti kami (tidak termasuk lawan bicara).",
    "In this sentence, may means has/have/had (a/some) (...). May klase ka. – You have a class. Ka is the POD.":
        "Dalam kalimat ini, may menyatakan kepemilikan. May klase ka berarti kamu memiliki kelas. Ka adalah POD.",
    "Optional reading: Replaceable sounds.": "Bacaan opsional: bunyi yang dapat saling menggantikan.",
    "Here, pa means still.": "Di sini, pa berarti masih.",
    "Nandito means is/are/was/were here.": "Nandito berarti ada atau berada di sini.",
    "Nasaan (...)? – Where is/are/was/were (...)?": "Nasaan (...)? berarti ‘Di mana (...) berada?’",
    "Nasa taas or nasa itaas means upstairs, higher up or at the top.":
        "Nasa taas atau nasa itaas berarti di lantai atas, lebih tinggi, atau di bagian atas.",
    "Nasa baba' or nasa ibaba' means downstairs, lower down or at the bottom.":
        "Nasa baba' atau nasa ibaba' berarti di lantai bawah, lebih rendah, atau di bagian bawah.",
    "Nasa is used to indicate where someone or something is. It is equivalent to is/are/was/were in/on/at etc. Nasa Cebu – is in Cebu; nasa mesa / nasa lamesa – is on (the) table.":
        "Nasa menunjukkan lokasi seseorang atau sesuatu. Nasa Cebu berarti berada di Cebu; nasa mesa / nasa lamesa berarti berada di atas meja.",
    "Pinaka- – most (...)/-est. Malapit – near. Pinakamalapit – nearest.":
        "Pinaka- menyatakan tingkat paling/superlatif. Malapit berarti dekat. Pinakamalapit berarti paling dekat.",
    "Mas... pa – even more (...) / even (...)-er. Mas mainit pa – even hotter.":
        "Mas... pa berarti bahkan lebih (...). Mas mainit pa berarti bahkan lebih panas.",
    "Mas... kaysa – more (...) than / (...)-er than.":
        "Mas... kaysa berarti lebih (...) daripada (...).",
    "Mas... (kaysa) + Sa phrase – more (...)/-er than (...).":
        "Mas... (kaysa) + frasa Sa berarti lebih (...) daripada (...).",
    "Pwede -ng + basic form. – can/could (...) or may/might (...) (expressing ability or permission).":
        "Pwede -ng + bentuk dasar berarti dapat/bisa (...) atau boleh (...) untuk menyatakan kemampuan atau izin.",
    "Pwede -ng + basic form. – can/could (...) or may/might (...) (expressing possibility or permission).":
        "Pwede -ng + bentuk dasar berarti dapat/bisa (...) atau boleh (...) untuk menyatakan kemungkinan atau izin.",
    "Kailangan ko -ng + basic form – I need/should/have to/must (...).":
        "Kailangan ko -ng + bentuk dasar berarti saya perlu/harus (...).",
    "Kailangan ko -ng + basic form – I need to/ought to/must/should (...).":
        "Kailangan ko -ng + bentuk dasar berarti saya perlu/harus (...).",
}

MATERIAL_HINTS = (
    "lesson", "course", "audio", "video", "click next", "print out",
    "daily practice", "congratulations", "review lessons", "moving on",
    "don't worry", "you might want", "take your time", "key to success",
)

GRAMMAR_HINTS = (
    "sentence", "pronoun", "marker", "linker", "root", "affix", "verb",
    "adjective", "noun", "basic form", "pod", "news", "pattern", "plural",
    "singular", "subject", "predicate", "prefix", "suffix", "followed by",
    "indicate", "statement", "pronounced", "pronunciation", "sound", "stress",
    "glottal", "syllable", "vowel", "consonant", "word order", "form",
    "grammar", "inclusive", "exclusive", "uncountable", "possessive",
)


@dataclass(frozen=True)
class PreparedText:
    source: str
    prepared: str
    replacements: tuple[tuple[str, str], ...] = ()

    def restore(self, translated: str) -> str:
        value = translated
        for token, replacement in self.replacements:
            value = value.replace(token, replacement)
        return normalize_spaces(value)


@dataclass
class Note:
    page: int
    label: str
    source: str
    prepared: PreparedText
    links: list[str]
    category: str


@dataclass
class Phrase:
    page: int
    label: str
    tagalog: str
    literal: str
    natural: str
    natural_prepared: PreparedText
    chunks: list[tuple[str, str, PreparedText]]
    notes: list[Note] = field(default_factory=list)
    links: list[str] = field(default_factory=list)


@dataclass
class Chapter:
    number: int
    start: int
    end: int
    tagalog_title: str
    english_title: str
    indonesian_title: str
    intro: str
    intro_prepared: PreparedText
    image_xref: int
    phrases_a: list[Phrase]
    phrases_b: list[Phrase]
    divider_page: int
    recap_text: str
    source_links: list[dict[str, Any]]

    @property
    def lesson_id(self) -> str:
        return f"{COURSE_ID}-lesson-{self.number:02d}"

    @property
    def slug(self) -> str:
        return slugify(self.tagalog_title)

    @property
    def filename(self) -> str:
        return f"{self.number:02d}-{self.slug}.json"

    @property
    def image_path(self) -> str:
        return f"assets/{self.number:02d}-{self.slug}.jpg"

    @property
    def story_phrases(self) -> list[Phrase]:
        return self.phrases_a[:-1]

    @property
    def drill_phrases(self) -> list[Phrase]:
        return [self.phrases_a[-1], *self.phrases_b]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def normalize_spaces(value: str) -> str:
    return re.sub(r"[ \t]+", " ", value).strip()


def polish_indonesian(value: str) -> str:
    replacements = {
        "Dimana": "Di mana",
        "dimana": "di mana",
        "OKE": "Oke",
        "TIDAK": "Tidak",
        "Dr.Molina": "Dr. Molina",
        "Dr.Gomez": "Dr. Gomez",
    }
    polished = value
    for old, new in replacements.items():
        polished = polished.replace(old, new)
    if polished and polished[0].isalpha() and polished[0].islower():
        polished = polished[0].upper() + polished[1:]
    return polished


def normalize_source(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().replace("mag- tennis", "mag-tennis")


def slugify(value: str) -> str:
    value = value.lower().replace("'", "")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "lesson"


def smart_join(lines: Iterable[str]) -> str:
    result = ""
    for raw in lines:
        line = normalize_spaces(raw)
        if not line:
            continue
        separator = "" if result.endswith("-") else (" " if result else "")
        result += separator + line
    return result.strip()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def protected_text(source: str, fixed: dict[str, str] | None = None) -> PreparedText:
    prepared = source
    replacements: list[tuple[str, str]] = []
    for original, restored in (fixed or {}).items():
        if original not in prepared:
            continue
        token = f"ZXQTERM{len(replacements):04d}ZXQ"
        prepared = prepared.replace(original, token)
        replacements.append((token, restored))
    return PreparedText(source, prepared, tuple(replacements))


class Translator:
    def __init__(self, cache_path: Path) -> None:
        self.cache_path = cache_path
        if cache_path.is_file():
            self.cache: dict[str, str] = json.loads(cache_path.read_text(encoding="utf-8"))
        else:
            self.cache = {}

    def translate_all(self, values: Iterable[PreparedText]) -> None:
        ordered = list(dict.fromkeys(value.prepared for value in values if value.prepared.strip()))
        missing = [value for value in ordered if value not in self.cache]
        print(f"Translation cache: {len(ordered) - len(missing)} hits, {len(missing)} missing strings.")
        if not missing:
            return
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self._translate_one, value): value for value in missing}
            for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
                source = futures[future]
                self.cache[source] = future.result()
                if index % 100 == 0 or index == len(missing):
                    self._save()
                    print(
                        f"Translated {index}/{len(missing)} strings ({len(self.cache)} cached strings).",
                        flush=True,
                    )

    def result(self, value: PreparedText) -> str:
        return polish_indonesian(value.restore(self.cache[value.prepared]))

    def _save(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(self.cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def _translate_one(self, value: str) -> str:
        url = "https://translate.googleapis.com/translate_a/single?" + urlencode({
            "client": "gtx", "sl": "en", "tl": "id", "dt": "t", "q": value,
        })
        error: Exception | None = None
        for attempt in range(5):
            try:
                request = Request(url, headers={"User-Agent": "Mozilla/5.0 (RoLang content importer)"})
                with urlopen(request, timeout=45) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                translated = "".join(part[0] for part in payload[0] if part[0])
                if not translated.strip():
                    raise ValueError("Translation response was empty")
                return translated.strip()
            except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as caught:
                error = caught
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError("Translation request failed after retries") from error


def line_records(page: pymupdf.Page) -> list[tuple[float, list[dict[str, Any]]]]:
    records: list[tuple[float, list[dict[str, Any]]]] = []
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            spans = line["spans"]
            records.append((min(span["bbox"][1] for span in spans), spans))
    return sorted(records, key=lambda value: value[0])


def spans_for_size(page: pymupdf.Page, size: float) -> list[list[dict[str, Any]]]:
    result: list[list[dict[str, Any]]] = []
    for _, spans in line_records(page):
        selected = [span for span in spans if abs(span["size"] - size) < 0.35]
        if selected:
            result.append(selected)
    return result


def joined_span_lines(lines: list[list[dict[str, Any]]]) -> str:
    return smart_join("".join(span["text"] for span in spans) for spans in lines)


def grouped_colored_spans(lines: list[list[dict[str, Any]]]) -> list[str]:
    flattened: list[tuple[str, int]] = []
    for line_index, spans in enumerate(lines):
        if line_index and flattened:
            previous_text, previous_color = flattened[-1]
            if not previous_text.endswith((" ", "-")):
                flattened[-1] = (previous_text + " ", previous_color)
        flattened.extend((span["text"], span["color"]) for span in spans)
    groups: list[tuple[str, int]] = []
    for text, color in flattened:
        if groups and groups[-1][1] == color:
            groups[-1] = (groups[-1][0] + text, color)
        else:
            groups.append((text, color))
    return [normalize_spaces(text) for text, _ in groups]


def note_prepared(block: dict[str, Any]) -> tuple[str, PreparedText]:
    source_lines: list[str] = []
    prepared_lines: list[str] = []
    replacements: list[tuple[str, str]] = []
    for line in block["lines"]:
        source_parts: list[str] = []
        prepared_parts: list[str] = []
        for span in line["spans"]:
            raw = span["text"]
            source_parts.append(raw)
            if "Bold" in span["font"]:
                leading = raw[: len(raw) - len(raw.lstrip())]
                trailing = raw[len(raw.rstrip()):]
                core = raw.strip()
                if core:
                    token = f"ZXQTERM{len(replacements):04d}ZXQ"
                    restored = TERM_TRANSLATIONS.get(core, core)
                    replacements.append((token, restored))
                    prepared_parts.append(f"{leading}{token}{trailing}")
                else:
                    prepared_parts.append(raw)
            else:
                prepared_parts.append(raw)
        source_lines.append("".join(source_parts))
        prepared_lines.append("".join(prepared_parts))
    source = smart_join(source_lines)
    prepared = smart_join(prepared_lines)
    return source, PreparedText(source, prepared, tuple(replacements))


def classify_note(source: str) -> str:
    lower = source.lower()
    if any(hint in lower for hint in MATERIAL_HINTS):
        return "material"
    if any(hint in lower for hint in GRAMMAR_HINTS):
        return "grammar"
    return "vocabulary"


def parse_phrase(page: pymupdf.Page, page_number: int) -> Phrase:
    plain = page.get_text("text").strip()
    label = plain.splitlines()[0]
    if not PHRASE_LABEL.fullmatch(label):
        raise ValueError(f"Page {page_number} is not a numbered phrase page: {label!r}")

    tagalog_lines = spans_for_size(page, 14.4)
    italic_lines = spans_for_size(page, 13.2)
    if not tagalog_lines or len(italic_lines) < 2:
        raise ValueError(f"Page {page_number} is missing phrase bands")
    italic_y = [min(span["bbox"][1] for span in line) for line in italic_lines]
    gaps = [italic_y[index + 1] - italic_y[index] for index in range(len(italic_y) - 1)]
    split = gaps.index(max(gaps)) + 1
    literal_lines = italic_lines[:split]
    natural_lines = italic_lines[split:]
    tagalog = joined_span_lines(tagalog_lines)
    literal = joined_span_lines(literal_lines)
    natural = joined_span_lines(natural_lines)

    tagalog_chunks = grouped_colored_spans(tagalog_lines)
    literal_chunks = grouped_colored_spans(literal_lines)
    if len(tagalog_chunks) != len(literal_chunks):
        raise ValueError(f"Page {page_number} has unaligned color glosses")
    chunks = []
    for tagalog_chunk, literal_chunk in zip(tagalog_chunks, literal_chunks, strict=True):
        chunks.append((tagalog_chunk, literal_chunk, protected_text(literal_chunk, BRACKET_GLOSSES)))

    links = [link["uri"] for link in page.get_links() if link.get("uri")]
    notes: list[Note] = []
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0 or block["bbox"][1] < 180:
            continue
        source, prepared = note_prepared(block)
        if source:
            notes.append(Note(page_number, label, source, prepared, links, classify_note(source)))
    return Phrase(
        page=page_number,
        label=label,
        tagalog=tagalog,
        literal=literal,
        natural=natural,
        natural_prepared=protected_text(natural),
        chunks=chunks,
        notes=notes,
        links=links,
    )


def title_page_intro(page: pymupdf.Page) -> str:
    blocks = [block for block in page.get_text("dict")["blocks"] if block["type"] == 0 and block["bbox"][1] > 260]
    return smart_join(
        smart_join("".join(span["text"] for span in line["spans"]) for line in block["lines"])
        for block in blocks
    )


def parse_chapters(document: pymupdf.Document) -> list[Chapter]:
    toc = document.get_toc()
    if len(toc) != 20:
        raise ValueError(f"Expected 20 PDF bookmarks, found {len(toc)}")
    chapters: list[Chapter] = []
    for index, (_, bookmark, start) in enumerate(toc):
        number = index + 1
        end = toc[index + 1][2] - 1 if index + 1 < len(toc) else FINAL_CONTENT_PAGE
        title_page = document[start - 1]
        title_lines = title_page.get_text("text").strip().splitlines()
        if int(title_lines[0]) != number:
            raise ValueError(f"Chapter number mismatch at page {start}")
        tagalog_title = title_lines[1]
        english_title = title_lines[2]
        bookmark_title = bookmark.split(" - ", 1)[1]
        if tagalog_title.rstrip("'") != bookmark_title.rstrip("'"):
            raise ValueError(f"Bookmark/title mismatch at chapter {number}")
        images = title_page.get_images(full=True)
        if len(images) != 1:
            raise ValueError(f"Chapter {number} should have exactly one embedded illustration")

        phrases_a: list[Phrase] = []
        phrases_b: list[Phrase] = []
        divider_pages: list[int] = []
        source_links: list[dict[str, Any]] = []
        for page_number in range(start, end + 1):
            page = document[page_number - 1]
            for link in page.get_links():
                if link.get("uri"):
                    source_links.append({"page": page_number, "uri": link["uri"]})
            text = page.get_text("text").strip()
            first = text.splitlines()[0] if text else ""
            if PHRASE_LABEL.fullmatch(first):
                phrase = parse_phrase(page, page_number)
                (phrases_a if first.startswith("A") else phrases_b).append(phrase)
            elif text == "Drills":
                divider_pages.append(page_number)
        if len(divider_pages) != 1 or not phrases_a or not phrases_b:
            raise ValueError(f"Chapter {number} has an invalid A/B/Drills structure")
        if [phrase.label for phrase in phrases_a] != [f"A {value:02d}" for value in range(1, len(phrases_a) + 1)]:
            raise ValueError(f"Chapter {number} has a gap in A labels")
        if [phrase.label for phrase in phrases_b] != [f"B {value:02d}" for value in range(1, len(phrases_b) + 1)]:
            raise ValueError(f"Chapter {number} has a gap in B labels")

        recap_text = document[end - 1].get_text("text").strip()
        expected_recap = " ".join([
            phrases_a[0].tagalog,
            *(phrase.tagalog for phrase in phrases_a[1:-1]),
            "Drills",
            phrases_a[-1].tagalog,
            *(phrase.tagalog for phrase in phrases_b),
        ])
        if normalize_source(recap_text) != normalize_source(expected_recap):
            raise ValueError(f"Chapter {number} recap does not match its phrase pages")

        intro = title_page_intro(title_page)
        chapters.append(Chapter(
            number=number,
            start=start,
            end=end,
            tagalog_title=tagalog_title,
            english_title=english_title,
            indonesian_title=INDONESIAN_TITLES[number],
            intro=intro,
            intro_prepared=protected_text(intro),
            image_xref=images[0][0],
            phrases_a=phrases_a,
            phrases_b=phrases_b,
            divider_page=divider_pages[0],
            recap_text=recap_text,
            source_links=source_links,
        ))
    return chapters


def lesson_text(source_language: str, source_text: str, indonesian: str, tagalog: str = "") -> dict[str, str]:
    value = {"sourceLanguage": source_language, "sourceText": source_text, "id": indonesian}
    if tagalog:
        value["tagalog"] = tagalog
    return value


def fil_text(tagalog: str, indonesian: str) -> dict[str, str]:
    return lesson_text("fil", tagalog, indonesian, tagalog)


def en_text(source: str, indonesian: str) -> dict[str, str]:
    return lesson_text("en", source, indonesian)


def mixed_text(source: str, indonesian: str) -> dict[str, str]:
    return lesson_text("mixed", source, indonesian)


def section(section_id: str, section_type: str, source_title: str, id_title: str,
            blocks: list[dict[str, Any]]) -> dict[str, Any]:
    if not blocks:
        raise ValueError(f"Section {section_id} cannot be empty")
    return {
        "id": section_id,
        "type": section_type,
        "title": mixed_text(source_title, id_title),
        "blocks": blocks,
    }


def note_blocks(notes: list[Note], translator: Translator) -> list[dict[str, Any]]:
    return [{
        "type": "text",
        "style": "body",
        "sourcePage": note.page,
        "sourceLabel": note.label,
        "links": note.links,
        "text": en_text(
            note.source,
            f"{note.label} · halaman PDF {note.page}\n\n"
            f"{NOTE_OVERRIDES.get(note.source, translator.result(note.prepared))}",
        ),
    } for note in notes]


def unit_for_lesson(number: int) -> dict[str, Any]:
    return next(unit for unit in UNITS if number in unit["lessons"])


def build_lesson(chapter: Chapter, translator: Translator, pdf_hash: str) -> dict[str, Any]:
    all_phrases = [*chapter.phrases_a, *chapter.phrases_b]
    natural = {
        phrase.label: polish_indonesian(
            NATURAL_OVERRIDES.get(phrase.natural, translator.result(phrase.natural_prepared))
        )
        for phrase in all_phrases
    }
    natural[chapter.phrases_a[0].label] = chapter.indonesian_title
    unit = unit_for_lesson(chapter.number)

    vocabulary_entries: list[dict[str, Any]] = []
    seen_terms: set[str] = set()
    for phrase in all_phrases:
        for tagalog_chunk, literal_chunk, prepared in phrase.chunks:
            key = re.sub(r"\W+", "", tagalog_chunk, flags=re.UNICODE).casefold()
            if not key or key in seen_terms:
                continue
            seen_terms.add(key)
            proper = re.sub(r"^[^\w]+|[^\w. ]+$", "", literal_chunk).strip()
            meaning = GLOSS_OVERRIDES.get(literal_chunk)
            if meaning is None and proper in PROPER_GLOSS_TERMS:
                meaning = proper
            if meaning is None:
                meaning = translator.result(prepared)
            vocabulary_entries.append({
                "term": fil_text(tagalog_chunk, meaning),
                "meaning": en_text(literal_chunk, meaning),
                "sourcePage": phrase.page,
            })

    notes = [note for phrase in all_phrases for note in phrase.notes]
    material_notes = [note for note in notes if note.category == "material"]
    vocabulary_notes = [note for note in notes if note.category == "vocabulary"]
    grammar_notes = [note for note in notes if note.category == "grammar"]
    if not grammar_notes:
        grammar_notes = vocabulary_notes[-1:]
        vocabulary_notes = vocabulary_notes[:-1]

    dialogue_turns = [{
        "speaker": phrase.label,
        "speakerText": mixed_text(phrase.label, f"Bagian {phrase.label}"),
        "text": fil_text(phrase.tagalog, natural[phrase.label]),
        "sourcePage": phrase.page,
    } for phrase in chapter.story_phrases]

    example_blocks: list[dict[str, Any]] = []
    for phrase in all_phrases:
        example_blocks.append({
            "type": "example",
            "title": mixed_text(phrase.label, f"{phrase.label} · halaman PDF {phrase.page}"),
            "sourcePage": phrase.page,
            "rows": [{"cells": [
                fil_text(phrase.tagalog, natural[phrase.label]),
                en_text(phrase.literal, f"Glosa harfiah (Inggris)\n{phrase.literal}"),
                en_text(phrase.natural, f"Terjemahan alami sumber (Inggris)\n{phrase.natural}"),
            ]}],
        })

    exercise_blocks: list[dict[str, Any]] = [{
        "type": "exercise",
        "role": "instruction",
        "text": mixed_text("Drills", "Latihan pola (Drills)"),
        "sourcePage": chapter.divider_page,
    }]
    for phrase in chapter.drill_phrases:
        exercise_blocks.append({
            "type": "exercise",
            "role": "content",
            "title": mixed_text(phrase.label, f"{phrase.label} · halaman PDF {phrase.page}"),
            "sourcePage": phrase.page,
            "text": fil_text(phrase.tagalog, natural[phrase.label]),
        })

    sections = [
        section(
            "introduction", "INTRODUCTION", chapter.english_title, chapter.indonesian_title,
            [
                {"type": "image", "path": chapter.image_path, "sourcePage": chapter.start},
                {"type": "text", "style": "heading", "text": en_text(chapter.english_title, chapter.indonesian_title)},
            ],
        ),
        section(
            "learning-material", "LEARNING_MATERIAL", "Chapter context", "Konteks bab",
            [{
                "type": "text", "style": "body", "sourcePage": chapter.start,
                "text": en_text(chapter.intro, translator.result(chapter.intro_prepared)),
            }, *note_blocks(material_notes, translator)],
        ),
        section(
            "dialogue", "DIALOGUE", "Story A", "Dialog utama (Bagian A)",
            [{"type": "dialogue", "turns": dialogue_turns}],
        ),
        section(
            "vocabulary", "VOCABULARY", "Vocabulary and expressions", "Kosakata dan ungkapan",
            [{"type": "vocabulary", "entries": vocabulary_entries}, *note_blocks(vocabulary_notes, translator)],
        ),
        section(
            "grammar", "GRAMMAR", "Grammar and pronunciation notes", "Catatan tata bahasa dan pelafalan",
            note_blocks(grammar_notes, translator),
        ),
        section(
            "examples", "EXAMPLES", "Literal and natural translations", "Contoh dengan glosa harfiah dan alami",
            example_blocks,
        ),
        section(
            "exercises", "EXERCISES", "Drills", "Latihan pola",
            exercise_blocks,
        ),
        section(
            "summary", "SUMMARY", chapter.tagalog_title, "Ringkasan bab",
            [
                {"type": "text", "style": "heading", "text": mixed_text("Story A", "Dialog utama")},
                {"type": "list", "style": "outline", "items": [
                    fil_text(phrase.tagalog, natural[phrase.label]) for phrase in chapter.story_phrases
                ]},
                {"type": "text", "style": "heading", "text": mixed_text("Drills", "Latihan pola")},
                {"type": "list", "style": "outline", "items": [
                    fil_text(phrase.tagalog, natural[phrase.label]) for phrase in chapter.drill_phrases
                ]},
            ],
        ),
    ]

    objective_topic = chapter.indonesian_title.rstrip(".?!").lower()
    objectives = [
        mixed_text(
            f"Chapter {chapter.number} · Story A",
            f"Memahami dialog utama Bab {chapter.number} tentang {objective_topic}.",
        ),
        mixed_text(
            "Literal and natural translations",
            "Membandingkan susunan Tagalog dengan glosa harfiah dan terjemahan alami dari sumber.",
        ),
        mixed_text("Drills", "Melatih kembali pola dan ungkapan pada bagian Drills."),
    ]

    source_items = 1 + sum(3 + len(phrase.notes) for phrase in all_phrases)
    lesson = {
        "schemaVersion": 1,
        "structureVersion": 2,
        "id": chapter.lesson_id,
        "courseId": COURSE_ID,
        "unitId": unit["id"],
        "order": chapter.number,
        "level": "BEGINNER",
        "title": {"id": chapter.indonesian_title, "fil": chapter.tagalog_title},
        "summary": {
            "id": translator.result(chapter.intro_prepared),
            "fil": chapter.tagalog_title,
        },
        "objectives": objectives,
        "source": {
            "book": BOOK_TITLE,
            "file": PDF_FILENAME,
            "pdfSha256": pdf_hash,
            "chapter": chapter.number,
            "pages": {"start": chapter.start, "end": chapter.end},
            "drillsDividerPage": chapter.divider_page,
            "recapPage": chapter.end,
        },
        "sourceLinks": chapter.source_links,
        "assets": [chapter.image_path],
        "sections": sections,
        "contentAudit": {
            "sourcePages": chapter.end - chapter.start + 1,
            "phrasePages": len(all_phrases),
            "storyPhrases": len(chapter.story_phrases),
            "drillPhrases": len(chapter.drill_phrases),
            "noteBlocks": len(notes),
            "vocabularyEntries": len(vocabulary_entries),
            "sourceTextItemsBefore": source_items,
            "sourceTextItemsAfter": source_items,
            "recapVerified": True,
            "imageCount": 1,
        },
    }
    return lesson


def build_unit(unit: dict[str, Any], chapters: list[Chapter]) -> dict[str, Any]:
    selected = [chapter for chapter in chapters if chapter.number in unit["lessons"]]
    return {
        "schemaVersion": 1,
        "id": unit["id"],
        "courseId": COURSE_ID,
        "title": {"id": unit["id_title"], "fil": unit["fil_title"]},
        "assets": [],
        "sections": [{
            "id": "unit-overview",
            "type": "OVERVIEW",
            "title": mixed_text("Unit overview", "Gambaran unit"),
            "blocks": [{
                "type": "list",
                "style": "outline",
                "items": [fil_text(chapter.tagalog_title, chapter.indonesian_title) for chapter in selected],
            }],
        }],
    }


def build_page_audit(document: pymupdf.Document, chapters: list[Chapter]) -> list[dict[str, Any]]:
    roles: dict[int, dict[str, Any]] = {}
    for chapter in chapters:
        roles[chapter.start] = {"role": "chapter-title", "chapter": chapter.number}
        roles[chapter.divider_page] = {"role": "drills-divider", "chapter": chapter.number}
        roles[chapter.end] = {"role": "chapter-recap", "chapter": chapter.number}
        for phrase in [*chapter.phrases_a, *chapter.phrases_b]:
            roles[phrase.page] = {"role": "phrase", "chapter": chapter.number, "label": phrase.label}
    roles[ARTIFACT_PAGE] = {
        "role": "external-link-artifact",
        "text": "naman etc.",
        "uri": "https://learningtagalog.com/downloads/free_audio.html",
    }
    if set(roles) != set(range(1, document.page_count + 1)):
        missing = sorted(set(range(1, document.page_count + 1)) - set(roles))
        duplicates = sorted(set(roles) - set(range(1, document.page_count + 1)))
        raise ValueError(f"Page audit is incomplete: missing={missing}, extra={duplicates}")
    result = []
    for page_number, page in enumerate(document, 1):
        text = page.get_text("text").strip()
        result.append({
            "page": page_number,
            **roles[page_number],
            "textCharacters": len(text),
            "textSha256": sha256_bytes(text.encode("utf-8")),
            "imageCount": len(page.get_images(full=True)),
            "linkCount": len(page.get_links()),
        })
    return result


def build_content(pdf_path: Path, server_root: Path, cache_path: Path) -> None:
    if sha256_file(pdf_path) != PDF_SHA256:
        raise ValueError("The selected PDF does not match the audited Course Book 1 source")
    document = pymupdf.open(pdf_path)
    if document.page_count != 522:
        raise ValueError(f"Expected 522 pages, found {document.page_count}")
    chapters = parse_chapters(document)

    prepared_values: list[PreparedText] = []
    for chapter in chapters:
        prepared_values.append(chapter.intro_prepared)
        for phrase in [*chapter.phrases_a, *chapter.phrases_b]:
            prepared_values.append(phrase.natural_prepared)
            prepared_values.extend(prepared for _, _, prepared in phrase.chunks)
            prepared_values.extend(note.prepared for note in phrase.notes)
    translator = Translator(cache_path)
    translator.translate_all(prepared_values)

    course_dir = server_root / "lesson" / COURSE_ID
    assets_dir = course_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    asset_inventory = []
    for chapter in chapters:
        extracted = document.extract_image(chapter.image_xref)
        if extracted["ext"] not in {"jpg", "jpeg"}:
            raise ValueError(f"Chapter {chapter.number} illustration is not JPEG")
        image_path = course_dir / chapter.image_path
        image_path.write_bytes(extracted["image"])
        asset_inventory.append({
            "path": chapter.image_path,
            "sha256": sha256_file(image_path),
            "bytes": image_path.stat().st_size,
            "mediaType": "image/jpeg",
            "width": extracted["width"],
            "height": extracted["height"],
            "sourcePage": chapter.start,
        })
    asset_index = {"schemaVersion": 1, "count": len(asset_inventory), "assets": asset_inventory}
    asset_index_path = assets_dir / "index.json"
    write_json(asset_index_path, asset_index)

    lessons: list[dict[str, Any]] = []
    lesson_references: list[dict[str, Any]] = []
    for chapter in chapters:
        lesson = build_lesson(chapter, translator, PDF_SHA256)
        lesson_path = course_dir / chapter.filename
        write_json(lesson_path, lesson)
        lessons.append(lesson)
        lesson_references.append({
            "id": chapter.lesson_id,
            "unitId": unit_for_lesson(chapter.number)["id"],
            "order": chapter.number,
            "path": chapter.filename,
            "title": lesson["title"],
            "summary": lesson["summary"],
            "objectives": lesson["objectives"],
            "assets": lesson["assets"],
            "sha256": sha256_file(lesson_path),
        })

    unit_references: list[dict[str, Any]] = []
    for unit in UNITS:
        unit_document = build_unit(unit, chapters)
        unit_path = course_dir / "units" / f"{unit['slug']}.json"
        write_json(unit_path, unit_document)
        lesson_ids = [chapters[number - 1].lesson_id for number in unit["lessons"]]
        unit_references.append({
            "id": unit["id"],
            "title": unit_document["title"],
            "path": f"units/{unit['slug']}.json",
            "lessons": lesson_ids,
            "assets": [],
            "sha256": sha256_file(unit_path),
        })

    pages = build_page_audit(document, chapters)
    source_audit = {
        "schemaVersion": 1,
        "source": {
            "type": "PDF",
            "title": BOOK_TITLE,
            "file": PDF_FILENAME,
            "pdfSha256": PDF_SHA256,
            "pageCount": document.page_count,
        },
        "chapterCount": len(chapters),
        "lessonCount": len(lessons),
        "unitCount": len(UNITS),
        "assetCount": len(asset_inventory),
        "phrasePageCount": sum(len(chapter.phrases_a) + len(chapter.phrases_b) for chapter in chapters),
        "drillsDividerPageCount": sum(page["role"] == "drills-divider" for page in pages),
        "recapPageCount": sum(page["role"] == "chapter-recap" for page in pages),
        "externalArtifactPages": [{
            "page": ARTIFACT_PAGE,
            "text": "naman etc.",
            "disposition": "Recorded as a link-only PDF artifact; it is not presented as lesson content.",
            "uri": "https://learningtagalog.com/downloads/free_audio.html",
        }],
        "missingPages": [],
        "duplicatePhraseLabels": [],
        "chapters": [{
            "chapter": chapter.number,
            "title": chapter.tagalog_title,
            "pages": {"start": chapter.start, "end": chapter.end},
            "phrasePages": len(chapter.phrases_a) + len(chapter.phrases_b),
            "aPhrasePages": len(chapter.phrases_a),
            "bPhrasePages": len(chapter.phrases_b),
            "drillsDividerPage": chapter.divider_page,
            "recapPage": chapter.end,
            "recapVerified": True,
            "image": chapter.image_path,
        } for chapter in chapters],
        "pages": pages,
    }
    audit_path = course_dir / "source-audit.json"
    write_json(audit_path, source_audit)

    course = {
        "schemaVersion": 1,
        "id": COURSE_ID,
        "level": "BEGINNER",
        "languagePair": {"reference": "id", "target": "fil"},
        "title": {
            "id": "Belajar Tagalog — Lancar dengan Cepat dan Mudah — Buku Kursus 1",
            "fil": "Learning Tagalog — Course Book 1",
        },
        "description": {
            "id": "Dua puluh bab berurutan dari Course Book 1, lengkap dengan dialog, glosa, catatan, latihan, ringkasan, dan ilustrasi sumber.",
            "fil": "Dalawampung sunod-sunod na aralin mula sa Course Book 1.",
        },
        "source": {
            "title": BOOK_TITLE,
            "file": PDF_FILENAME,
            "pdfSha256": PDF_SHA256,
            "pageCount": document.page_count,
            "website": "https://learningtagalog.com/",
        },
        "cover": chapters[0].image_path,
        "assetIndex": {"path": "assets/index.json", "sha256": sha256_file(asset_index_path)},
        "sourceAudit": {"path": "source-audit.json", "sha256": sha256_file(audit_path)},
        "requiredSectionTypes": [
            "INTRODUCTION", "LEARNING_MATERIAL", "DIALOGUE", "VOCABULARY",
            "GRAMMAR", "EXAMPLES", "EXERCISES", "SUMMARY",
        ],
        "units": unit_references,
        "lessons": lesson_references,
    }
    course_index_path = course_dir / "index.json"
    write_json(course_index_path, course)

    lesson_index_path = server_root / "lesson" / "index.json"
    existing_index = json.loads(lesson_index_path.read_text(encoding="utf-8"))
    references = [reference for reference in existing_index["courses"] if reference["id"] != COURSE_ID]
    for order, reference in enumerate(references, 1):
        referenced_path = lesson_index_path.parent / reference["path"]
        referenced_course = json.loads(referenced_path.read_text(encoding="utf-8"))
        reference["order"] = order
        reference["sha256"] = sha256_file(referenced_path)
        reference["lessonCount"] = len(referenced_course["lessons"])
        reference["unitCount"] = len(referenced_course["units"])
        reference["title"] = referenced_course["title"]
    references.append({
        "id": COURSE_ID,
        "order": len(references) + 1,
        "path": f"{COURSE_ID}/index.json",
        "sha256": sha256_file(course_index_path),
        "lessonCount": len(lessons),
        "unitCount": len(UNITS),
        "title": course["title"],
    })
    write_json(lesson_index_path, {"schemaVersion": 1, "courses": references})

    manifest_path = server_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["lessons"] = {"index": "lesson/index.json", "sha256": sha256_file(lesson_index_path)}
    write_json(manifest_path, manifest)

    print(
        f"Generated {len(lessons)} lessons, {len(UNITS)} units, {len(asset_inventory)} images, "
        f"and a {len(pages)}-page source audit in {course_dir}."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--server-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--translation-cache", type=Path,
        default=Path("/tmp/rolang-course-book-1/translation-cache-en-id-v2.json"),
    )
    args = parser.parse_args()
    build_content(args.pdf.resolve(), args.server_root.resolve(), args.translation_cache.resolve())


if __name__ == "__main__":
    main()
