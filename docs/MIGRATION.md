# PostgreSQL to MongoDB Atlas migration

The importer preserves every entity defined by the retained SQL migrations:
stories, ordered chapters, root metadata/learning JSON, translations, vocabulary,
the full dictionary, users/password hashes/roles, sessions, learning records,
reviews/preferences/tombstones, operation fingerprints, rate limits, corpus
metadata and SQL migration history. It never changes PostgreSQL.

## Existing database cutover

1. Keep a verified PostgreSQL backup and retain the source database. Pause source
   writes during the final import/cutover so changes after the snapshot are not
   omitted. Target a new MongoDB database that is not serving traffic yet.
2. Configure Atlas as described in [Deployment](DEPLOYMENT.md). Put the target
   MONGODB_URI and MONGODB_DB_NAME in a private .env. Retain DATABASE_URL as the
   PostgreSQL source URL and POSTGRES_SCHEMA if the source schema is not public.
   The source account needs SELECT on all inspected tables; use a direct endpoint
   that supports a repeatable-read transaction.
3. Run from rolang-server:

~~~sh
npm ci
node --env-file=.env scripts/migrate.js
node --env-file=.env scripts/import-postgres.js
node --env-file=.env scripts/import-postgres.js --verify
node --env-file=.env scripts/doctor.js
node --env-file=.env src/local.js
~~~

With settings already in the shell, the equivalents are npm run migrate,
npm run import:postgres, npm run import:postgres -- --verify, and npm run doctor.

4. Verify the existing story catalog and filters, detail, manifest, chapters,
   full content, translations and vocabulary. Use retained sessions/login and
   old synchronization cursors for a test learner; verify an editor too.
5. Put only the MongoDB runtime variables in the correct Vercel environment,
   deploy, and verify both health paths and API families before enabling writes.
   See the exact commands in [Deployment](DEPLOYMENT.md).
6. Keep PostgreSQL and its migrations/backups until the live Atlas data, deployed
   backend and Android consumers have all been verified. No script deletes them.

Do not run seed.js or import-corpus.js before transferring an existing database.
Their preserved fixture IDs can conflict with edited production content.
Do not run migrate:postgres during this cutover: that archived command writes SQL
schema and exists only for separately restored rollback/test databases.

## Import behavior and verification

The source transaction is REPEATABLE READ READ ONLY. Counts and cursor scans
share one consistent snapshot. Rows are fetched in batches of 250, and chapters
are read in their original order. JSON content is copied without passing it
through the newer authoring validator or narrowing unknown fields.

Stable natural identifiers produce deterministic MongoDB _id values. Missing
documents use insert-only upserts. Identical reruns do not change IDs, story
versions, dates, learning revisions or operation fingerprints. A differing target
document raises IMPORT_CONFLICT; the importer never overwrites newer Atlas edits
and offers no replacement flag. Use a fresh target or explicitly reconcile a
reviewed conflict before resuming.

The importer compares every copied field after each batch, verifies source counts,
checks each story's vocabulary/chapter counts and paragraph concatenation, checks
all user/story references, and initializes/verifies revision/version counters.
The final report includes sourceCounts, targetCounts, insertedCounts,
derivedChapters, storyVocabulary, exercises, relationships and sourceHash.
Logs include only stages, table names, counts and hashes, never credentials,
connection URLs, password hashes, tokens or raw driver errors.

A failed import may leave an insert-only partial target. Its database_imports
record stays failed/running and health returns DATABASE_NOT_READY. Keep it off
traffic, fix the reported cause, then rerun the same import and verification.
--verify reads both databases without modifying data or import state.

Sources that only completed migration 001 are supported. Missing story versions
start at decimal string 1; missing chapter rows derive exact authored chapters
or main. Optional dictionary/import tables are copied when present. SQL
migration history is retained separately from MongoDB initialization.

Unknown additional columns are retained in postgres_extra_fields. Unknown source
tables fail preflight instead of being silently skipped. Missing required tables,
invalid relationships/chapter text, revisions outside the API integer range,
oversized BSON documents and conflicting target content fail explicitly.
Review/adapt unsupported source data while keeping its backup; never resolve
connectivity errors by discarding or replacing stories.

## New, empty installation and retained corpus

data/corpus.json retains the exact original Android library. For a genuinely new
database, initialize it and import/verify this corpus:

~~~sh
node --env-file=.env scripts/migrate.js
node --env-file=.env scripts/import-corpus.js
node --env-file=.env scripts/import-corpus.js --verify
~~~

Expected report: 20 units, 20 chapters, 1,204 dictionary entries, 92 exercises,
source SHA-256 42cea594c9e5e44402ef812a4dde402961197c2059b51c0a08b21d16a3b925dd.
All course metadata, curriculum order, translated learning fields and dictionary
practice metadata remain intact. Identical imports preserve versions/dates.

Corpus imports are atomic. Different existing story/dictionary content rolls back
the entire import. After reviewing and backing up a deliberate corpus replacement,
--replace-existing is available only on import-corpus.js. It does not exist on
the PostgreSQL transfer tool. Nine optional sample stories are seeded only when
their IDs do not already exist.

The original SQL files in migrations/, the PostgreSQL source configuration under
scripts/postgres/.env.example, the archived schema runner, and both corpus assets
remain unchanged/available for verification and rollback planning.
