# RoLang static content

This branch contains versioned static learning content for the RoLang Android
app. It is deliberately independent of the legacy backend on `main`.

The published content base is:

```text
https://raw.githubusercontent.com/HamzahSk/rolang-server/data/
```

`manifest.json` discovers two courses with 13 unit documents and 44 lessons,
plus the aggregate Stories index in `storie/index.json`. That index contains
all 60 narrative units from *4000 Essential English Words* Book 1 and Book 2;
each book also has its own index and source audit beneath
`storie/4000-essential-english-words-book-{1,2}/`. Stories retain their source
book in `collectionId`, while broad thematic categories are shared across both
books. Each story is a concise Tagalog retelling with an equivalent Indonesian
version, global vocabulary references, expressions, grammar, comprehension
questions, and a separate answer key. Every matching EPUB illustration is
published with its story. Every JSON and image reference is checked by
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
Both story builders merge their book into the aggregate index, reject duplicate
IDs and paths, and refuse to drop an existing story file when the other book is
updated.

## Global vocabulary

`manifest.json` registers `vocabulary/index.json` by SHA-256. The index includes
an ID/word/Indonesian-meaning search directory and a file registry, so clients
can search and locate words without fetching every shard. Each
`vocabulary-NNN.json` contains up to 100 canonical entries. Entry IDs and shard
assignments are permanent; new words fill the last shard, then append files.
Never delete earlier files or replace the index with only the newest shard.

Entries use `language: "fil"`, Indonesian `meanings`, `partOfSpeech` plus all
`partsOfSpeech`, `pronunciation` plus all `pronunciations`, bilingual `examples`
with `storyId`, and `storyRefs`. `sources` retains the complete original records,
including localized meanings and contextual notes, for a lossless audit.
Normalization only folds case, Unicode NFC, whitespace and curly apostrophes;
accents, hyphens, inflections and separate words remain distinct.

Stories contain `vocabularyIds` instead of embedded definitions. The index also
registers references for bundled Android units. The Android corpus lexicon is
retained solely as a compatible first-install offline fallback; published global
entries take precedence, and all new vocabulary is maintained here.

To import embedded vocabulary from newly generated stories (book builders call
this automatically), optionally including a legacy Android corpus:

```sh
python3 tools/global_vocabulary.py . --corpus ../app/src/main/assets/corpus.json
python3 tools/global_vocabulary.py . --validate-only
python3 tools/validate_content.py .
python3 -m unittest discover -s tools -p 'test_*.py'
```

To add a word, add it to an existing canonical entry if the normalized word is
already present, preserving its ID. Otherwise append it to the last non-full
shard or a new sequential shard, with a new unused ID. Run the publisher above
to rebuild the directory, hashes, story references and manifest. It refuses
duplicate IDs/words and invalid existing hashes; when editing a shard directly,
update that shard's hash in the index before publishing. Validate before pushing
only to `origin/data`. Publish the complete commit so manifest and shards agree.

## Regenerate Stories

The Book 1 and Book 2 builders inspect their complete EPUB spines, classify the
30 numbered unit documents as narratives, exclude cover and reference pages,
verify every preserved title, and extract the
illustration linked from each narrative. It stores source hashes, characters,
settings, themes, and plot events in each book's `source-audit.json`, but does not
publish or translate the complete copyrighted English story text.

```sh
python3 tools/build_book2_stories.py \
  "/path/to/4000 Essential English Words - Book 2.epub"
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
