# Create, edit, and publish stories

Use the administrator API to manage content. It validates all translations and
word coverage before saving, including drafts. Direct database writes bypass those
checks; the API is the recommended authoring route.

## Story format

[examples/story.json](examples/story.json) is a complete, uploadable story: one
paragraph in Indonesian and Filipino with all required Filipino dictionary entries. The
larger [sample library](../data/sample-stories.json) shows longer stories and
multiple difficulty variants. A request has this structure:

```json
{
  "id": "reader_a1",
  "family": "reader",
  "category": "Kehidupan sehari-hari",
  "difficulty": "A1",
  "title": {"id": "Pembaca", "fil": "Ang mambabasa"},
  "summary": {
    "id": "Maya suka membaca.",
    "fil": "Mahilig magbasa si Maya."
  },
  "sentences": [{"id": "Maya membaca.", "fil": "Nagbabasa si Maya."}],
  "vocabulary": []
}
```

The empty vocabulary above only illustrates the outer shape; upload the complete
example file, which includes coverage. `sentences` is the existing API name for
paragraphs: each entry can contain several sentences and must be translated as a
whole. Android displays the entries in order as continuous, scrollable text.

| Field | Authoring rule |
| --- | --- |
| `id` | Stable ID, 1–80 ASCII letters, digits, `_`, or `-`; cannot change on update |
| `family` | Same ID format; groups level variants of the same story |
| `category` | Free-text genre, 1–100 characters, e.g. `Mystery` or `Nature & adventure` |
| `difficulty` | Exact `A1`, `A2`, `B1`, `B2`, `C1`, or `C2` |
| `title`, `summary` | Nonempty `id` and `fil` strings; summary is the description |
| `sentences` | 1–300 ordered paragraph objects; every object has Indonesian and Filipino text |
| `vocabulary` | 1–5000 unique Filipino dictionary entries covering every Filipino paragraph word |

Translated strings are trimmed, nonempty, and at most 10,000 characters each.
Request bodies are limited to 2 MB. Android maps A1/A2 to Beginner, B1/B2 to
Intermediate, and C1/C2 to Advanced. Use separate IDs with the same `family` to
offer several versions. `status`, `version`, and `updatedAt` are response fields; do not include them
in authoring bodies. Optional `level` is accepted for legacy corpus imports.

## Dictionary and learning information

Every distinct word in each Filipino paragraph needs an entry, including names
and grammar markers. For example, `nagbabasa` needs:

```json
{
  "language": "fil",
  "word": "nagbabasa",
  "translations": {"id": "membaca", "fil": "nagbabasa"},
  "meanings": {
    "id": "Sedang membaca dan memahami kata-kata tertulis.",
    "fil": "Kasalukuyang bumabasa at umuunawa sa mga nakasulat na salita."
  },
  "pos": "verba",
  "notes": {
    "id": "Bentuk aspek sedang: Maya sedang membaca.",
    "fil": "Kasalukuyang kilos: nagbabasa si Maya."
  }
}
```

`language` is `fil` for exposed course vocabulary. Indonesian and Filipino are
required in `translations`, `meanings`, and `notes`. `pos` is a nonempty part-of-speech
label. `notes` explain grammar or context. Android uses the tapped paragraph and
its reference-language translation as the example sentence; there is no separate
`examples` field in the story contract. Put curated examples in paragraphs or
notes. Vocabulary statuses belong to learners, not to story content.

Words must already be lowercase; replace curly apostrophes with straight `'`.
Tokenization keeps Unicode letters, accents, internal apostrophes, and hyphens.
Do not include surrounding punctuation or spaces in `word`. Entries are unique
by `language:word`; inflected Filipino forms are separate words. Only Filipino
paragraph text requires coverage; titles and summaries do not.

## Publish and update

The commands below run from `rolang-server`. `ROLANG_TOKEN` represents an editor
session already available in your private shell. Authentication is documented in
[API](API.md); do not save real tokens in this repository.

```sh
# Create a draft in the database.
curl -X POST http://localhost:3000/api/v1/stories \
  -H "Authorization: Bearer $ROLANG_TOKEN" -H 'Content-Type: application/json' \
  --data-binary @docs/examples/story.json

# Make it available to Android and the public catalog.
curl -X POST http://localhost:3000/api/v1/stories/reader_a1/publish \
  -H "Authorization: Bearer $ROLANG_TOKEN" -H 'Content-Type: application/json' \
  --data '{"published":true}'

# Replace the entire authoring body after editing the JSON file.
curl -X PUT http://localhost:3000/api/v1/stories/reader_a1 \
  -H "Authorization: Bearer $ROLANG_TOKEN" -H 'Content-Type: application/json' \
  --data-binary @docs/examples/story.json
```

Create returns 201; update and publish return 200 with the full story. A duplicate
ID returns 409. Updates retain the current publication status and change
`updatedAt`, prompting Android to refresh its cached content. To hide a story,
publish with `{"published":false}`; inspect drafts with `GET /api/v1/admin/stories`.
To remove it permanently, send `DELETE /api/v1/stories/reader_a1` (204).

Unpublished stories return 404 through public detail endpoints. Offline devices
keep previously cached stories until a complete catalog refresh; successful
refreshes hide removed remote stories while preserving learning history.
Bundled stories remain available. Shortening a story clamps old Android reading
positions to the remaining paragraphs.

## Lessons, chapters, and covers

The API also accepts `order` (positive curriculum order), `kind` (`LESSON`,
`DIALOGUE`, `STORY`), `image` (existing Android illustration key), and optional
`cover` (URL metadata). Android currently uses the existing vector illustrations.
Optional learning fields are `objectives`, `notes` (`title`/`text` translations),
`focus` (language-to-expression arrays), `pronunciation` (translated guides,
which may be empty), aligned `speakers`, and `exercises`. Exercises require an ID,
type, translated `prompt`, `answer`, `explanation`, and choices/tokens as appropriate.
Choice questions must include the answer in both languages, and every exercise
includes a Filipino `speech` string for pronunciation practice. See [the migrated
corpus](../data/corpus.json) for every supported exercise type. Dictionary entries
may include `pronunciation` and `practice` (`prompt` translations and `choices`).
Normalized focus phrases with spaces are supported.

Optional `chapters` is an ordered array (1–100) with unique IDs within a story.
Each chapter has `id`, translated `title`, optional `summary`, `sentences`, and
optional learning fields above. The root dictionary covers all chapters; root
`sentences` must exactly concatenate chapter paragraphs in chapter order (at most
300 total). Root learning fields can contain story-wide notes and final exercises;
the app combines them with chapter learning fields without duplicating exercise IDs.
If chapters are absent, the server exposes the original content as chapter `main`.
Updating a story replaces its chapters atomically. The story gets a new revision,
while hashes for unchanged chapters remain stable. Use the API rather than direct
database writes so revisions and dictionaries remain consistent.
