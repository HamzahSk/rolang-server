# MongoDB Atlas and Vercel deployment

## Environment configuration

Node reads process.env. It does not automatically load .env; use
node --env-file=.env locally. The tracked .env.example contains placeholders.
Never put connection strings in Android config or commit a filled .env.

| Variable | Default / purpose |
| --- | --- |
| MONGODB_URI | Required Atlas mongodb+srv:// connection string, or a MongoDB replica-set URL |
| MONGODB_DB_NAME | Required explicit target database name, e.g. rolang |
| MONGODB_MAX_POOL_SIZE | Optional; 5 connections per warm instance, clamped to 1–20 |
| SESSION_DAYS | Optional; 30, clamped to integer 1–90 |
| CORS_ORIGINS | Optional comma-separated browser origins; Android does not need CORS |
| PORT | Optional standalone HTTP port; 3000 |
| DATABASE_URL | Migration only: retained PostgreSQL source URL; never read by API modules |
| POSTGRES_SCHEMA | Migration only: source schema; public by default |

VERCEL is supplied by Vercel itself and selects the trusted edge IP header for
authentication rate limits. There are no POSTGRES_URL, PGHOST or provider-specific
MongoDB variable fallbacks. Changes to Vercel variables require a new deployment.

## Atlas setup

1. Create an Atlas cluster supporting replica-set or sharded transactions. Choose
   a region close to the Vercel function. A standalone mongod is not supported.
2. Choose a database name and create a database user with readWrite on that database.
   The migration account also needs collection/index creation and dbAdmin when
   repairing validators with collMod. Use a runtime account with readWrite after
   initialization if you separate administrative and runtime credentials.
3. In Atlas Network Access, allow the migration host and Vercel outbound traffic.
   Use fixed Vercel outbound ranges when available. With dynamic Vercel egress,
   Atlas commonly needs the 0.0.0.0/0 access-list entry; keep authenticated database
   access and verified TLS enabled.
4. Copy Atlas's Drivers / Node.js connection string. Percent-encode special
   characters in credentials. Set MONGODB_URI and MONGODB_DB_NAME in a private
   .env; mongodb+srv enables TLS/SRV discovery automatically.
5. From rolang-server run npm ci and initialize the target:

~~~sh
node --env-file=.env scripts/migrate.js
~~~

For an existing PostgreSQL deployment, retain DATABASE_URL and follow the full
[read-only transfer procedure](MIGRATION.md). Do not seed its target first:

~~~sh
node --env-file=.env scripts/import-postgres.js
node --env-file=.env scripts/import-postgres.js --verify
node --env-file=.env scripts/doctor.js
~~~

For a new, empty installation, use import-corpus.js and its --verify option
instead. Both paths preserve identifiers and learning content. Keep PostgreSQL
and backups until the live Atlas import and deployed API are verified.

## Vercel setup and validation

1. Import the server repository. Leave Root Directory unset for a standalone
   rolang-server checkout; select rolang-server only in a parent repository that
   contains that directory.
2. Select Other / framework null and Node.js 22. Retain the committed vercel.json
   and api/index.js handler. Do not select Express automatic detection: app.js
   exports an app factory, while api/index.js exports the actual request handler.
3. Leave Output Directory unset. The committed buildCommand is deliberately empty
   because these JavaScript API functions need no static-site output. Vercel
   installs with npm ci and packages the explicit function. Run npm run build
   separately in CI or locally; it checks syntax, handler imports and Vercel
   configuration without opening database connections. Setting a static-site
   build command can make Vercel require a public output directory.
4. Set MONGODB_URI and MONGODB_DB_NAME in the required Production and Preview
   scopes. Optional pool/session/CORS settings use the names above. Source
   PostgreSQL variables are unnecessary in the running function.
5. Complete the chosen database import and verification before routing traffic.
   Migrations/imports never execute in module imports, builds or requests.
6. Deploy using your linked Vercel project, then run:

~~~sh
curl --fail-with-body https://YOUR-DEPLOYMENT.vercel.app/health
curl --fail-with-body https://YOUR-DEPLOYMENT.vercel.app/api/v1/health
curl --fail-with-body 'https://YOUR-DEPLOYMENT.vercel.app/api/v1/stories?limit=1'
curl --fail-with-body https://YOUR-DEPLOYMENT.vercel.app/api/v1/stories/EXISTING_STORY_ID
curl --fail-with-body https://YOUR-DEPLOYMENT.vercel.app/api/v1/stories/EXISTING_STORY_ID/chapters
curl --fail-with-body https://YOUR-DEPLOYMENT.vercel.app/api/v1/stories/EXISTING_STORY_ID/content
~~~

Check filter/search pagination, translations and vocabulary too. Using a test
learner/editor, verify login, retained bearer sessions, /me, sync with an old
cursor, and content administration. Keep the existing public origin to avoid
any Android configuration change. Vercel deployment protection must permit the
Android API requests.

For a real authenticated Vercel project:

~~~sh
vercel link
vercel pull --yes --environment=production
npm run build
vercel build --prod --standalone
vercel inspect https://YOUR-DEPLOYMENT.vercel.app --logs
vercel logs https://YOUR-DEPLOYMENT.vercel.app
~~~

Local packaging checks do not prove Atlas reachability, private project settings
or a successful live deployment. Do not run the test suite against production.

## Diagnose connectivity or readiness

Both health paths preserve the existing 200 response:

~~~json
{"status":"ok","apiVersion":"v1","database":"connected"}
~~~

Unreachable/misconfigured MongoDB returns 503 DATABASE_UNAVAILABLE. A connected
database with missing collections, validators, indexes, transaction support or
an unfinished PostgreSQL import returns 503 DATABASE_NOT_READY. Unknown routes
and / return JSON 404. No health response exposes credentials, hostnames or data.

doctor.js performs read-only connectivity/readiness/index and catalog checks
using the configured account. It exits nonzero on failure. Safe logs contain
only a static context and allowlisted driver codes/names.

| Diagnostic | Action |
| --- | --- |
| MONGODB_CONFIGURATION | Check the exact required variable names and URI/database-name syntax |
| MongoServerSelectionError, ENOTFOUND, EAI_AGAIN | Check Atlas availability, SRV DNS, region and network access list |
| Code 18 | Verify Atlas database-user credentials and authSource |
| Code 13 / DATABASE_NOT_READY | Check account permissions and initialized collections/validators/indexes |
| Codes 85 / 86 | Review conflicting index definitions before changing existing indexes |
| MongoOperationTimeoutError / network or TLS code | Check database/network availability and verified TLS settings |
| Incomplete import | Keep the target off traffic, resolve the import failure and rerun transfer/verification |

Never log raw driver errors or disable certificate checks to diagnose a failure.

## Real database tests

The full suite uses real MongoDB 8 and PostgreSQL 16. It creates only random
rolang_test_ databases and rolang_source_ schemas on explicitly supplied
disposable test servers; it never reads production variables as a fallback.

From rolang-server:

~~~sh
docker compose -f compose.test.yml up -d --wait
export TEST_MONGODB_URI='mongodb://127.0.0.1:27027/?replicaSet=rs0&directConnection=true'
export TEST_POSTGRES_URL='postgresql://rolang_test:local-test-password@127.0.0.1:54329/rolang_test'
export TEST_MONGODB_FAILPOINTS=1
npm test
npm run build
npm audit --omit=dev
docker compose -f compose.test.yml down
~~~

The password above belongs only to the disposable local Docker fixture.
TEST_MONGODB_FAILPOINTS=1 enables real server fault/deadline tests on this local
test server. Leave it unset for an external test replica set without test commands.
The API suite, corpus comparisons, PostgreSQL imports and ordinary outage tests
still run there. npm run test:unit needs no database credentials.

## Android configuration

The existing config.json contract is unchanged: serverBaseUrl is the public HTTPS
origin and apiVersion is v1. No database settings belong in the app. Existing
catalog, manifest, chapter, full-content and sync clients need no code changes
when the server keeps the same origin and v1 routes.
