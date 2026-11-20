# MongoDB Atlas and Vercel deployment

## Environment and Atlas

Only two database variables are required:

| Variable | Meaning |
| --- | --- |
| MONGODB_URI | Atlas SRV connection string or MongoDB replica-set/sharded URL |
| MONGODB_DB_NAME | Explicit target database name, e.g. rolang |

Optional application settings remain: `SESSION_DAYS` (30 by default, 1–90),
`CORS_ORIGINS` (comma-separated permitted browser origins), and `PORT` (local
listener, 3000 by default). Vercel supplies `VERCEL` for trusted forwarded IP
handling. Android does not require CORS. No alternative database variables exist.

1. Use an Atlas cluster supporting transactions, or a MongoDB replica set/sharded
   cluster. A standalone server cannot serve the transactional routes.
2. Give the database user read/write and collection/index management privileges
   on the target database. Atlas `readWrite` plus `dbAdmin` cover initialization
   and validator repair. Scope permissions to the application database.
3. Allow Vercel outbound traffic in Atlas Network Access according to your
   deployment networking configuration. Keep verified TLS enabled.
4. Percent-encode special characters in URI credentials. Keep real credentials
   in Vercel environment settings or a private, ignored local `.env`.

`node --env-file=.env ...` loads local variables. Vercel injects them directly.
Never paste connection strings in logs, tickets or committed configuration.

## Vercel project

1. Set Root Directory to `rolang-server` when deploying from the parent repository
   (or the repository root if this server is deployed as a separate repository).
2. Use Framework Preset **Other** and Node.js **22.x**. `vercel.json` disables
   framework detection and explicitly deploys `api/index.js` with a 30-second limit.
3. Use `npm ci` for installation. The configured empty Build Command skips static
   output generation for this plain JavaScript API. Run `npm run build` in CI/local
   validation; it checks syntax, the handler and Vercel config without DB access.
4. Set `MONGODB_URI` and `MONGODB_DB_NAME` for the required Production/Preview
   environments and redeploy after changing them. Remove obsolete database
   variables and custom release/schema commands from Vercel project settings.
5. Deploy and verify `/health`, `/api/v1/health`, catalog, chapter and authenticated
   routes against the deployed URL. Local checks do not prove live deployment.

The catch-all rewrite forwards paths to `/api`. The handler imports lazily without
opening a database connection. Database requests share one globally cached driver
pool and initialization promise per warm instance. Collections/indexes initialize
on requests and health checks. There is no persistent filesystem, separate
schema command, data import or static-site output requirement for the function.

## Retained story corpus

Existing MongoDB content is served directly and preserved during initialization.
If stories still reside only in `data/corpus.json`, import them from a trusted
machine using the target MongoDB variables:

```sh
node --env-file=.env scripts/migrate-language-pair.js
node --env-file=.env scripts/import-corpus.js --replace-existing
node --env-file=.env scripts/import-corpus.js --verify
npm run verify:production -- https://YOUR-DEPLOYMENT
```

For a database created by an earlier English/`tl` release, first follow
[the language-pair migration](MIGRATION.md). The import stores 21 units, 30 ordered
chapter records, 494 Filipino dictionary entries
and 150 exercises, including all translations and practice fields. It initializes
MongoDB automatically, avoids duplicates, and rolls back on differing existing
content. Review conflicts and take a backup before explicitly considering
`--replace-existing`. `seed.js` imports the same complete corpus idempotently.
Neither script runs during deployment or API requests.
The production verifier is read-only. It compares every live unit, chapter,
dictionary entry and exercise with the canonical corpus through public API calls,
and also requires the live health endpoint to report a connected MongoDB database.

## Diagnose MongoDB connectivity and initialization

```sh
node --env-file=.env scripts/doctor.js
curl --fail-with-body https://YOUR-DEPLOYMENT/health
curl --fail-with-body 'https://YOUR-DEPLOYMENT/api/v1/stories?limit=2'
```

Doctor and both health paths ping MongoDB and initialize/verify collection
validators, indexes and transaction support. Doctor also checks a published
story's catalog/chapter/vocabulary shape and reports `catalog:empty` if none exist.
An empty catalog does not mean the database is unavailable.

Health returns the existing successful shape:

```json
{"status":"ok","apiVersion":"v1","database":"connected"}
```

Failures return 503, `status:unavailable`, `database:connected|unavailable`, and a
safe error. `DATABASE_UNAVAILABLE` identifies invalid configuration, connectivity,
authentication or timeouts. `DATABASE_NOT_READY` identifies genuine initialization,
permissions, transaction-support or index conflicts. Messages identify the
problem without showing credentials. Logs contain only static contexts and
allowlisted error codes. Initialization does not remove conflicting data.

Health actively repairs missing collections/indexes and validators. A verification
failure never becomes a successful response; later requests retry initialization.

## Real database tests

The suite uses only real MongoDB 8. Tests require an explicit disposable URL and
never fall back to production variables. The Docker setup has no persistent volumes:

```sh
docker compose -f compose.test.yml up -d --wait
export TEST_MONGODB_URI='mongodb://127.0.0.1:27027/?replicaSet=rs0&directConnection=true'
export TEST_MONGODB_FAILPOINTS=1
npm ci
npm run build
npm test
docker compose -f compose.test.yml down
```

Tests create/drop only random `rolang_test_` databases. Failpoints require this
local test server with `enableTestCommands=1`; never enable them on production.
Coverage includes automatic and concurrent initialization, index/validator repair,
existing-data preservation, unique index conflicts, permissions, unavailable
connections, transaction rollback/retries/deadlines, API authentication/admin/sync,
all corpus stories/chapters, search, pagination, translations and vocabulary.
`npm run test:unit` needs no database.
