# Ro-Lang backend guide

The backend uses Node.js 22, Express 5, Zod, and the official MongoDB driver.
MongoDB Atlas stores published content, accounts, sessions, and learning records.
English (en), Indonesian (id), and Filipino/Tagalog (tl) translations are retained
in the original localized maps; no translation service is needed.

Android downloads catalog metadata and ordered chapters, caches complete reading
content, and exchanges offline changes through POST /api/v1/me/sync. The v1
endpoint paths and response shapes remain compatible.

| Component | Responsibility |
| --- | --- |
| src/config.js | Validated environment names and bounded connection settings |
| src/db.js | Lazy shared MongoClient, pooling, bounded transactions and retries |
| src/schema.js | Collection validators, indexes, and read-only readiness checks |
| src/app.js | Existing REST routes, authorization, and safe HTTP errors |
| src/auth.js | Existing scrypt hashes, token hashes, roles, and shared rate limits |
| src/stories.js | Ordered vocabulary/chapter documents and API serialization |
| src/learning.js | Per-user revisions, completion merging, tombstones and sync deduplication |
| scripts/migrate.js | Explicit MongoDB collection/index initialization |
| scripts/import-postgres.js | Read-only PostgreSQL snapshot transfer and verification |
| scripts/import-corpus.js | Import/verify the entire retained original corpus |
| api/index.js / src/local.js | Vercel handler / standalone HTTP listener |
| migrations/ / scripts/postgres/ | Retained PostgreSQL migration and rollback assets |

## Start locally

Use an Atlas database, or the disposable replica set in compose.test.yml. A
standalone mongod cannot run the transactions required by this API.

From rolang-server:

~~~sh
npm ci
cp .env.example .env
# Fill MONGODB_URI and MONGODB_DB_NAME in the private .env.
node --env-file=.env scripts/migrate.js
~~~

For an existing PostgreSQL installation, follow [Migration](MIGRATION.md) and
transfer its database before starting the API. Do not seed or import the bundled
corpus into that target first: existing story IDs can have different content.

For a new, empty installation:

~~~sh
node --env-file=.env scripts/import-corpus.js
node --env-file=.env scripts/import-corpus.js --verify
node --env-file=.env scripts/doctor.js
node --env-file=.env src/local.js
curl --fail-with-body http://localhost:3000/health
curl --fail-with-body 'http://localhost:3000/api/v1/stories?limit=2'
~~~

The complete corpus contains 20 units, 20 chapters, 1,204 dictionary entries and
92 exercises. Optional seed.js adds nine sample variants and skips existing IDs.
Neither import silently replaces changed content; see the migration conflict rules.

Node reads process.env. Use --env-file=.env, or supply settings in the shell and
run npm run migrate, npm run import:corpus, npm start, and npm run doctor.

## Editors and checks

Register an account through the API, then promote the intended editor:

~~~sh
node --env-file=.env scripts/admin.js editor@example.com
npm run build
npm run test:unit
npm audit --omit=dev
~~~

[Deployment](DEPLOYMENT.md#real-database-tests) provides the exact setup for the
full suite using real PostgreSQL and MongoDB databases. Tests create and remove
only randomly named disposable databases/schemas and require explicit TEST_
variables; they never fall back to production settings.
