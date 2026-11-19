# Ro-Lang backend guide

The backend uses Node.js 22, Express 5, Zod and the official MongoDB driver.
MongoDB stores content, accounts, sessions and learning records. English (`en`),
Indonesian (`id`) and Filipino/Tagalog (`tl`) maps are preserved. Android downloads
catalogs and ordered chapters, caches reading content and exchanges offline
changes through `POST /api/v1/me/sync`.

| Component | Responsibility |
| --- | --- |
| src/config.js | Validated MongoDB configuration and bounded connection settings |
| src/db.js | Lazy shared MongoClient, automatic readiness, transactions and retries |
| src/schema.js | Automatic collection/index initialization and verification |
| src/app.js | Existing REST routes, authorization and safe HTTP errors |
| src/auth.js | Scrypt hashes, token hashes, roles and shared rate limits |
| src/stories.js | Ordered vocabulary/chapters and API serialization |
| src/learning.js | Revisions, completion merging, tombstones and sync deduplication |
| scripts/import-corpus.js | Import/verify the entire retained original corpus |
| api/index.js / src/local.js | Vercel handler / standalone HTTP listener |

## Start locally

Use Atlas or the disposable replica set in `compose.test.yml`. This API requires
MongoDB transactions, so a standalone MongoDB server is insufficient.

From `rolang-server/`:

```sh
npm ci
cp .env.example .env
# Fill MONGODB_URI and MONGODB_DB_NAME in the private .env.
node --env-file=.env src/local.js
```

The first database request creates and verifies the required MongoDB collections
and indexes. No separate initialization command is needed.

If content exists only in the bundled corpus, import it from a separate shell:

```sh
node --env-file=.env scripts/import-corpus.js
node --env-file=.env scripts/import-corpus.js --verify
node --env-file=.env scripts/doctor.js
curl --fail-with-body http://localhost:3000/health
curl --fail-with-body 'http://localhost:3000/api/v1/stories?limit=2'
```

The complete corpus contains 20 stories, 20 chapters, 1,204 dictionary entries
and 92 exercises. `seed.js` optionally adds nine sample variants, skipping
existing IDs. Corpus import is atomic and repeatable. If content differs, it
fails without changing the database. Review and back up content before explicitly
choosing `--replace-existing`; initialization never chooses that option.

Node reads `process.env`. Use `--env-file=.env` locally, or set variables in the
shell and run `npm start`, `npm run import:corpus` and `npm run doctor`.

## Editors and checks

Register an account through the API, then promote the intended editor:

```sh
node --env-file=.env scripts/admin.js editor@example.com
npm run build
npm run test:unit
```

[Deployment](DEPLOYMENT.md) documents the full real MongoDB test setup. Tests
create and remove only randomly named disposable databases using explicit test
variables; they never fall back to production settings.
