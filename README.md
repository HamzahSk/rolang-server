# RoLang static content

This branch contains versioned static learning content for the RoLang Android
app. It is deliberately independent of the legacy backend on `main`.

The published content base is:

```text
https://raw.githubusercontent.com/HamzahSk/rolang-server/data/
```

`manifest.json` discovers two courses with 13 unit documents and 44 lessons,
plus all 30 narrative units from *4000 Essential English Words - Book 1*. Each
story is a concise Tagalog retelling with an equivalent Indonesian version,
story-specific vocabulary, expressions, grammar, comprehension questions, and
a separate answer key. All 30 matching EPUB illustrations are published with
their stories. Every JSON and image reference is checked by
`tools/validate_content.py`; indexes contain SHA-256 hashes used by Android
before cached content is replaced.

Each lesson uses semantic sections (`INTRODUCTION`, `LEARNING_MATERIAL`,
`VOCABULARY`, `EXAMPLES`, `DIALOGUE`, `EXERCISES`, and `SUMMARY`) and dedicated
blocks for vocabulary entries, dialogue turns, examples, and exercises. The
original normalized source text remains attached to every localized item for
auditing.

## Validate

```sh
python3 tools/validate_content.py .
```

## Regenerate from the EPUB

The importer uses unpacked Argos `en_id` and `tl_en` CTranslate2 models so source
text is translated locally. It preserves normalized EPUB source text beside the
Indonesian translation and writes `source-audit.json` for traceability.

```sh
python3 tools/import_epub.py \
  "/path/to/Elementary Tagalog  1.epub" \
  --english-indonesian /path/to/translate-en_id-1_9 \
  --tagalog-english /path/to/translate-tl_en-1_9
python3 tools/restructure_lessons.py "/path/to/Elementary Tagalog  1.epub"
python3 tools/validate_content.py .
```

Generated content must be committed and published only from the `data` branch.

## Regenerate Stories

The Book 1 builder inspects the complete EPUB spine, classifies the 30 numbered
unit documents as narratives, excludes the cover and four note/glossary
documents, verifies every preserved title, and extracts the illustration linked
from each narrative. It stores source hashes and concise plot metadata in
`storie/source-audit.json`, but does not publish or translate the complete
copyrighted English story text.

```sh
python3 tools/build_book1_stories.py \
  "/path/to/4000 essential english words - Book 1.epub"
python3 tools/validate_content.py .
```

## Regenerate Course Book 1 from the PDF

The PDF importer requires PyMuPDF. It accounts for every source page, preserves
the source Tagalog and English glosses, caches Indonesian translations locally,
extracts the embedded JPEG illustrations, and rebuilds all discovery hashes.

```sh
python3 -m pip install pymupdf
python3 tools/import_course_book_pdf.py \
  "/path/to/Learning Tagalog - Fluency Made Fast and Easy - Course Book 1.pdf"
python3 tools/validate_content.py .
```
