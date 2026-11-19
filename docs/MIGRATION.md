# Migrate the Android story library

The server owns content after this migration. `data/corpus.json` is an exact
snapshot of the original Android corpus, retained so a standalone server checkout
can initialize its database. The original `app/src/main/assets/corpus.json` and
corpus generator remain in the Android repository as migration/test fixtures;
the application does not seed them or package the corpus in its APK.

## Apply and verify

Set `DATABASE_URL` for the intended PostgreSQL database using the existing
configuration. Back up an existing database before migrating/replacing content.
Apply these commands from the server repository:

```sh
npm ci
npm run migrate
npm run import:corpus
npm run import:corpus -- --verify
npm start
```

With a private `.env`, use `node --env-file=.env scripts/migrate.js` and
`node --env-file=.env scripts/import-corpus.js` instead. Migrations and imports
are transactional and repeatable. Import validates the complete corpus before
writing, rejects duplicate IDs/dictionary keys, and compares complete JSONB
content to avoid duplicate records or revision changes on identical reimports.
It verifies every story, dictionary entry, publication status, chapter ordering,
and paragraph translation before committing. It reports:

- 20 learning units and 20 chapters (each existing unit has chapter `main`).
- 1,204 dictionary entries and 92 exercises.
- Source SHA-256 `42cea594c9e5e44402ef812a4dde402961197c2059b51c0a08b21d16a3b925dd`.

A positional file argument imports another corpus in the same legacy format:
`npm run import:corpus -- /path/to/corpus.json`. It preserves IDs, families,
order, multilingual paragraphs, speaker alignment, objectives, notes, focus
phrases, pronunciation, exercises, and dictionary practice metadata. Complete
original corpus/course metadata is recorded in `corpus_imports`.

## Existing IDs

The old sample library contains `market_beginner`, also used by the Android
curriculum. Different existing content causes the entire import to roll back.
Inspect that record and back it up. If replacing it with the app's preserved
content is intentional, run `npm run import:corpus -- --replace-existing`, then
verify. This updates the record under its original ID, preserving learner
references. Identical content is left unchanged. Never use the replacement flag
to refresh production after editors have changed stories; author future content
through the administrator API.

## Rollout and checks

Deploy migrations and the verified content before releasing the Android build.
Check `/api/v1/stories`, `/stories/:id`, and `/stories/:id/chapters/main` on the
configured server, then run the app's live client test against a disposable
server/database (`-ProlangIntegrationUrl=http://127.0.0.1:3000`). That test compares
all original units with actual API content and checks Room restart/offline reads.
No production deployment or remote database modification is implied by local
verification. Keep the original source assets until your deployed database and
Android clients have also been verified.

Room migration 4→5 copies existing catalog metadata and keeps full existing
content and all user learning records. A fresh installation downloads its catalog;
an existing installation can continue reading its saved library offline. Failed
requests and unpublished content do not delete downloaded reading snapshots.
