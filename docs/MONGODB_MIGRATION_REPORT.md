# Ro-Lang MongoDB migration report

The backend implementation and local verification are complete. All runtime
database operations use MongoDB. No production PostgreSQL data was changed and
no Atlas import or Vercel deployment was performed: live database credentials
and authenticated Vercel access were unavailable in this workspace.

## 1. Previous architecture and identified problems

The inspected server uses Node.js 22, Express 5, ES modules and Zod. The previous
database client was `pg`, with handwritten SQL and no ORM. The retained migrations
define accounts and hashed sessions, JSONB story content and vocabulary, ordered
story chapters, a global dictionary, corpus metadata, learning records,
idempotent sync operations and shared authentication rate limits. SQL sequences
provide story versions and learning revisions; foreign keys and transactions
protect related writes. Translations and exercises are learning fields within
the original story/chapter JSON, rather than separate SQL tables.

The source checkout already included attempts to address Vercel crashes with
an explicit API handler, warm PostgreSQL pooling, an idle-error listener,
timeouts, schema/permission checks and pool lifecycle attachment. The
[historical investigation](VERCEL_INVESTIGATION.md) records the earlier
incompatible Express factory detection and unhandled pool-error crash paths.
Those entrypoint fixes are retained.

The PostgreSQL runtime accepted `DATABASE_URL` but silently fell back to `pg`
environment defaults when it was absent. Its private production connection,
TLS/network access, permissions and migration state could not be verified.
Public observations during this work showed JSON 404 at `/` and 503
`DATABASE_UNAVAILABLE` at the health/catalog paths. They do not establish the
specific private database failure cause or prove a successful deployment.

## 2. MongoDB architecture implemented

The official MongoDB Node.js driver replaces runtime SQL. `src/config.js`
validates one explicit URI/database configuration. `src/db.js` lazily caches
one MongoClient and the initial connection promise across concurrent requests
and warm Vercel invocations. Failed initial connections can retry; existing
pools recover from socket failures. Importing the API opens no connections.

The default pool has five connections, no minimum, bounded connection/selection/
queue waits, a 15-second operation deadline and 60-second idle eviction. Readiness
checks have a ten-second total deadline. Core API transactions use remaining
deadlines, a default 20-second request budget, transient-conflict retries,
uncertain-commit retries without replaying business work, and bounded cleanup.
The driver is pinned to 6.21.0; upgrades must preserve the tested timeout behavior.

There are 14 validated collections and 20 application indexes, plus MongoDB's
automatic `_id` indexes. Stories retain exact root content and localized metadata.
Chapters are independently referenced documents with original positions and
versions. Root vocabulary is stored as ordered documents; bounded chapter
vocabulary stays embedded. The dictionary, sessions and learning histories are
separate collections. BSON size checks reject oversized data without truncation.

Original IDs, password/token hashes, story versions, learning revisions,
tombstones and sync fingerprints are retained. Imported user counters start
above existing revisions. Per-user transactional writes serialize concurrent
device changes. Story replacements/deletions and multi-collection reads are
atomic. Expiration indexes have no TTL so expired source records remain available
for migration verification. See [Database](DATABASE.md) for all collections and
indexes.

Existing v1 endpoints, response shapes, ETags, filters and pagination are
preserved. Indexed `search`/`q` is optional. Both `/health` and `/api/v1/health`
check connectivity and readiness, returning safe 503 responses for unavailable
or uninitialized databases and unfinished imports.

## 3. Files modified or added

All changes are inside `rolang-server/`:

| Area | Files |
| --- | --- |
| Configuration and dependencies | `.env.example`, `package.json`, `package-lock.json`, `compose.test.yml` |
| Runtime | `src/app.js`, `src/auth.js`, `src/config.js`, `src/db.js`, `src/documents.js`, `src/errors.js`, `src/health.js`, `src/learning.js`, `src/local.js`, `src/schema.js`, `src/stories.js`, `src/validation.js` |
| Administration/import/build | `scripts/admin.js`, `scripts/build.js`, `scripts/check.js`, `scripts/doctor.js`, `scripts/import-corpus.js`, `scripts/import-postgres.js`, `scripts/migrate.js`, `scripts/seed.js` |
| Retained source/rollback tools | `scripts/postgres/.env.example`, `scripts/postgres/db.js`, `scripts/postgres/migrate.js` |
| Tests | `test/api.test.js`, `test/content.test.js`, `test/helpers.js`, `test/migration.test.js`, `test/postgres-fixture.js`, `test/runtime.test.js`, `test/unit.test.js` |
| Documentation | `README.md`, `docs/README.md`, `docs/API.md`, `docs/DATABASE.md`, `docs/DEPLOYMENT.md`, `docs/MIGRATION.md`, `docs/STORIES.md`, `docs/VERCEL_INVESTIGATION.md`, this report |

`api/index.js`, `vercel.json`, both SQL migration files, both source corpus files
and the Android application remain unchanged. `@vercel/functions` is removed.
`pg` remains a development dependency solely for source transfer, retained SQL
tools and real PostgreSQL tests; it is absent from the packaged runtime function.
Do not remove source assets or PostgreSQL before live verification.

## 4. Data migration results

The actual PostgreSQL importer CLI was run against PostgreSQL 16 and MongoDB 8
in disposable local Docker databases. The source fixture uses the retained SQL
migrations and complete original corpus, plus accounts, learning state, draft
content and one deliberately split story. This is local migration evidence,
not a transfer of the inaccessible production database.

| Entity | Source rows | Verified target documents |
| --- | ---: | ---: |
| Stories | 20 | 20 |
| Ordered chapters | 21 | 21 |
| Root story vocabulary | Stored in story JSONB arrays | 2,703 |
| Global dictionary | 1,204 | 1,204 |
| Users | 2 | 2 |
| Sessions, including an expired session | 2 | 2 |
| Learning records, including tombstones | 4 | 4 |
| Sync operations | 1 | 1 |
| Authentication buckets | 2 | 2 |
| Corpus import metadata | 1 | 1 |
| Retained SQL migration history | 2 | 2 |

All five reference relationships, imported fields, story text/order and revision
counters were verified. The CLI reported 92 exercises and `status: verified`.
An identical second execution inserted zero documents in every collection.
The read-only `--verify` execution succeeded with the same source hash:
`c5aeb8b8189d2b524d38c950ca82dc4f8350ccb365ff8c87a4ccc3ee8387a96d`.

Separate full-corpus checks verified 20 stories, 20 chapters, 1,204 dictionary
entries and 92 exercises. The original corpus JSON hash remains
`42cea594c9e5e44402ef812a4dde402961197c2059b51c0a08b21d16a3b925dd`.
Regression fixtures also verified chapter positions 103/107, chapter-only
exercises, decimal story version `9007199254740993`, old sync cursors and sessions,
sources lacking migration 002, extra columns, concurrent SQL source edits,
conflicting targets and interrupted imports.

The importer uses a `REPEATABLE READ READ ONLY` source snapshot, batches of 250
and deterministic insert-only upserts. Unknown source tables and invalid or
conflicting data fail explicitly. Logs contain stages/counts/hashes, not secrets.
See [Migration](MIGRATION.md) for reruns, verification and cutover rules.

## 5. Required environment variables

| Variable | Purpose |
| --- | --- |
| `MONGODB_URI` | Required Atlas `mongodb+srv://` driver connection string; keep private and percent-encode credential characters |
| `MONGODB_DB_NAME` | Required explicit database name, for example `rolang`; a URI path does not override it |
| `MONGODB_MAX_POOL_SIZE` | Optional, default 5, clamped to 1–20 per warm instance |
| `SESSION_DAYS`, `CORS_ORIGINS`, `PORT` | Optional session/browser/standalone settings documented in `.env.example` |
| `DATABASE_URL`, `POSTGRES_SCHEMA` | Migration only: PostgreSQL source URL and optional schema; never read by the running API |

No live MongoDB/PostgreSQL credential variables were present during verification.
Node does not automatically load `.env`; local commands use `--env-file=.env`,
or variables explicitly supplied by the shell. Vercel must receive the exact
runtime names in the intended Production/Preview environment and be redeployed
after changes.

## 6. Build and test results

| Verification | Result |
| --- | --- |
| `npm ci` | Passed; lockfile installation completed |
| Full `npm test` with explicit disposable database URLs and failpoints enabled | 33 passed, 0 failed, 0 skipped; approximately 26 seconds |
| `npm run build` | Passed after the final initialization fix; syntax, handler import and Vercel configuration checked without database credentials |
| `npm audit --omit=dev` | 0 vulnerabilities; installation audit also reported 0 |
| `npm run doctor` against the local CLI import target | Connected, catalog accessible, all 20 application indexes verified |
| `git diff --check` | Passed |
| Original SQL/corpus/API entrypoint/Vercel configuration comparisons and parent Git status | Unchanged; no Android edits |
| `npx --yes vercel@66.2.0 build --prod --standalone` | Actual local production packaging succeeded |

The suite uses real database servers. It covers all API families, every original
story/chapter, translations/vocabulary/exercises, search/filter/list/sync
pagination, authentication/admin operations, migration idempotency and conflicts,
concurrent learning writes, validators/indexes, connection reuse/recovery,
redacted errors, unavailable MongoDB, transaction rollback/deadlines and real
transient/uncertain-commit retries. Initialization also repairs disabled validator
enforcement when the validator schema itself is unchanged.

The generated Vercel output contains exactly one function: `api/index.js`,
`nodejs22.x`, 30-second maximum duration, approximately 6.3MiB. It includes
MongoDB and excludes `pg`. The generated handler was served through an actual
local Node HTTP server against real MongoDB; 17 requests verified health,
catalog pagination/filter/search, detail/manifest/chapters/full content,
translations/vocabulary, ETag 304, unauthenticated 401, validation 400 and root 404.
Temporary local project settings were used only for packaging and are removed
before handoff. This does not verify a remote deployment.

## 7. Remaining Atlas configuration and deployment

Follow [Deployment](DEPLOYMENT.md) and [Migration](MIGRATION.md):

1. Create an Atlas replica-set/sharded cluster and database user. Configure
   network access for the migration host and Vercel, and keep verified TLS enabled.
2. Set `MONGODB_URI`, `MONGODB_DB_NAME` and the PostgreSQL source `DATABASE_URL`
   in a private local environment. Keep a verified source backup and pause source
   writes for the final cutover. Use a fresh target; do not seed it first.
3. From `rolang-server/`, run:

   ```sh
   npm ci
   node --env-file=.env scripts/migrate.js
   node --env-file=.env scripts/import-postgres.js
   node --env-file=.env scripts/import-postgres.js --verify
   node --env-file=.env scripts/doctor.js
   ```

4. Link the actual Vercel project, select Other/Node.js 22 and the correct server
   root. Keep the committed explicit function/rewrite and leave Output Directory
   unset. Set the two MongoDB runtime variables in the required environment scopes.
5. Deploy and verify both health paths, catalog/search/pagination, every required
   story/chapter/content endpoint, retained login/sessions and old sync cursors
   using the commands in the deployment guide. Verify Android against the same
   public API origin before enabling normal writes.
6. Keep PostgreSQL, SQL migrations and backups until live Atlas data and deployed
   API behavior are verified. The remaining `pg` development/source tooling can
   be retired separately after that verification.

Live Atlas reachability, the production data transfer, private Vercel settings
and the deployed Android flow remain unverified. Disposable local test containers
are stopped after verification; production resources are untouched.
