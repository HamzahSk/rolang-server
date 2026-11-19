# Configuration and Vercel deployment

## Server environment

The server reads process environment variables. It does not automatically load
`.env`; use Node's `--env-file=.env` locally. The tracked `.env.example` contains
placeholders only. Production secrets belong in the deployment environment.

| Variable | Default / range | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | Provider connection URL | PostgreSQL connection; use a managed pooled endpoint in Vercel |
| `DATABASE_POOL_SIZE` | 3; clamped to 1–10 | Maximum connections per warm function instance |
| `SESSION_DAYS` | 30; clamped to 1–90 | Bearer session lifetime |
| `CORS_ORIGINS` | Empty | Comma-separated allowed browser origins; Android does not need CORS |
| `PORT` | 3000 | Standalone local server port; Vercel supplies its own routing |

When `DATABASE_URL` is absent, node-postgres accepts standard `PGHOST`, `PGPORT`,
`PGDATABASE`, `PGUSER`, and `PGPASSWORD` settings for local development. Use a
dedicated database. Migrations need permission to create tables/indexes; runtime
needs SELECT on application tables and `schema_migrations`, INSERT/UPDATE/DELETE
as used by the API, and USAGE on application sequences. Follow the provider's verified
TLS configuration. Do not disable certificate checks to fix connectivity.

`VERCEL` is supplied by Vercel itself; the API uses its edge IP header for rate
limiting there and the socket IP locally. Pool timeouts are 5 seconds to connect,
10 seconds idle, and 15 seconds per client query. No extra PostgreSQL startup
parameters are added, preserving compatibility with transaction-mode poolers.
The shared pool handles idle connection failures and uses Vercel's
`attachDatabasePool` so idle connections close before a function is suspended.
Put the database near the function's
region and use provider pooling to limit connections across function instances.

## Deploy

1. Create a PostgreSQL 16+ database with Neon, Supabase, or another provider. Get
   its pooled URL for runtime and, if needed, a direct URL for migrations.
2. Import the repository in Vercel. For the standalone `rolang-server` repository,
   leave **Root Directory** unset (`.`); use `rolang-server` only when importing
   a parent repository that actually contains that directory. Use Node.js 22.
   The committed `vercel.json` selects **Other** (`framework: null`), installs
   with `npm ci`, and explicitly skips the static-site build (`buildCommand: ""`).
   Leave **Output Directory** unset. These plain JavaScript API functions need
   dependency tracing/packaging, which Vercel performs automatically, rather
   than a static output directory. Run `npm run build` separately to validate
   syntax, the handler export, and deployment configuration without database access.
   Do not select Vercel's Express preset: it detects `src/app.js`, an app factory
   with no default request handler, instead of the explicit `api/index.js` function.
3. Set `DATABASE_URL` and any optional settings in the required Vercel environments
   (Preview/Production). The Android config only needs the public server origin.
4. From a trusted database-connected shell, apply migrations before enabling the
   deployment. Import and verify the migrated app library:

   ```sh
   node --env-file=.env scripts/migrate.js
   node --env-file=.env scripts/doctor.js
   node --env-file=.env scripts/import-corpus.js
   node --env-file=.env scripts/import-corpus.js --verify
   ```

   These run separately from build steps and requests. No migration runs on cold
   start. Repeated identical imports preserve IDs and versions; see [Migration](MIGRATION.md) for conflicts.
5. Deploy using the dashboard or CLI. Existing `vercel.json` routes all paths to
   `api/index.js` with a 30-second function budget. Check public readiness and the
   catalog:

   ```sh
   curl --fail-with-body https://YOUR-DEPLOYMENT.vercel.app/health
   curl --fail-with-body https://YOUR-DEPLOYMENT.vercel.app/api/v1/health
   curl --fail-with-body 'https://YOUR-DEPLOYMENT.vercel.app/api/v1/stories?limit=1'
   ```

6. Register the editor account, then promote it using
   `node --env-file=.env scripts/admin.js editor@example.com` against the target
   database. Use its normal login session to publish content. Verify that Vercel
   deployment protection permits the Android app's API requests.

The app and production function never need writable server files. Content and
learning data persist in PostgreSQL; deploys do not reset them. Run the updated
backend before distributing the status-aware Android build. See
[Database](DATABASE.md) for backups and expired-session maintenance.

## Diagnose a failed deployment

`/health` and `/api/v1/health` are equivalent readiness checks. They return 200
with `{"status":"ok","apiVersion":"v1","database":"connected"}` only when
PostgreSQL responds, migrations 001 and 002 are applied, expected tables/columns
resolve, and the runtime role has required permissions. An unreachable database
returns 503 with `database:"unavailable"`; a reachable database with missing
migrations or incompatible schema returns 503 with `database:"connected"` and
`error.code:"DATABASE_NOT_READY"`. No provider, hostname, SQL, or credentials
are exposed. `/` and unknown API paths return JSON 404.

Run `npm run doctor` with the same environment as the production function (or
`node --env-file=.env scripts/doctor.js`). This is read-only: it checks readiness
and executes a catalog query without printing records or changing data. It exits
nonzero on failure. Use `npm run migrate` only when migrations are pending; do
not run imports with `--replace-existing` to resolve connectivity errors.

Server logs contain `backend_error`, a static context, and allowlisted error
codes. They never log error messages, stacks, query parameters, URLs or secrets.

| Logged code | Check |
| --- | --- |
| `42P01`, `42703`, `DATABASE_NOT_READY` | Run pending migrations against the intended database; confirm runtime search path |
| `42501` | Grant required table/sequence permissions to the runtime role |
| `28P01`, `28000` | Verify the configured database credentials with the provider |
| `ENOTFOUND`, `EAI_AGAIN` | Verify the connection URL hostname and DNS resolution |
| `ECONNREFUSED`, `ETIMEDOUT`, `DATABASE_TIMEOUT_OR_DISCONNECT` | Verify provider availability, port/network access and the pooled endpoint |
| Certificate/TLS code | Use the provider's trusted CA/verified TLS settings; do not disable certificate verification |
| `53300` | Use the provider's pooled endpoint and check connection limits |
| `ERR_INVALID_URL` | Correct the existing `DATABASE_URL` format; encode special characters in credentials |
| `DATABASE_TLS_OR_AUTH_CONFIGURATION` | Check the provider's TLS requirement and password configuration |
| `UNKNOWN` | Inspect startup/build configuration or reproduce locally; raw database errors are intentionally not logged |

Environment changes apply to new deployments. Confirm settings in the correct
Preview/Production scope and redeploy; configuring variables does not initialize
the schema. Vercel integrations may provide other URL names, but this backend
reads only its documented `DATABASE_URL` or node-postgres `PG*` configuration.

From an authenticated Vercel CLI in the server directory:

```sh
vercel link
vercel pull --yes --environment=production
vercel build --prod
vercel inspect https://YOUR-DEPLOYMENT.vercel.app --logs
vercel logs https://YOUR-DEPLOYMENT.vercel.app
```

`inspect --logs` checks build logs; `logs` checks runtime failures. Inspect logs
privately and redact provider URLs, secrets and personal data before sharing.
After publishing the fix, verify both health paths, catalog, a returned story's
detail and chapter paths, login, `/api/v1/me`, and learner synchronization using
a test account. Do not run the backend test suite against production.

See [the investigation report](VERCEL_INVESTIGATION.md) for reproduced failures
and the limits of local verification.

## Android config.json

Edit `rolang-app/config.json`, the source Gradle copies into generated app assets:

```json
{
  "serverBaseUrl": "https://YOUR-DEPLOYMENT.vercel.app",
  "apiVersion": "v1",
  "connectionTimeoutMs": 10000,
  "requestTimeoutMs": 30000,
  "onlineEnabled": true,
  "automaticSyncEnabled": true,
  "syncIntervalMinutes": 15,
  "storyPageSize": 30
}
```

| Setting | Rule |
| --- | --- |
| `serverBaseUrl` | HTTPS origin only; no `/api/v1`, credentials, query, or fragment |
| `apiVersion` | `v1` for this server; appended as `/api/v1/` |
| `connectionTimeoutMs`, `requestTimeoutMs` | 1000–120000 ms each; defaults 10000 and 30000 |
| `onlineEnabled` | Defaults true; enables public catalogs, downloads, and account actions |
| `automaticSyncEnabled` | Defaults true; false still permits manual sync and launch-time public refresh |
| `syncIntervalMinutes` | 15–1440; defaults 15; Android battery policies can delay jobs |
| `storyPageSize` | 1–100; defaults 30 |

A complete private app `files/config.json` override takes precedence and is read
at runtime, including worker runs. Invalid settings disable networking while
keeping offline data. Configuration never includes passwords or bearer tokens.
In Android Profile, sign in and use **Sync now**, or use **Refresh stories** while
signed out. Offline mode supports previously cached/downloaded stories, word details,
reviews, and local progress.

For an emulator, the development origin is `http://10.0.2.2:3000`.
Configuration accepts HTTP only for `localhost`, `127.0.0.1`, and `10.0.2.2`;
the shipped manifest disables cleartext traffic. Use trusted HTTPS or a
debug-only manifest override for local device testing. Robolectric contract tests
can call a loopback HTTP server without changing the shipping manifest.

Build with JDK 17, SDK platform 35, and Build Tools 35.0.0:

```sh
cd ../rolang-app
bash gradlew :app:testDebugUnitTest :app:lintDebug :app:assembleDebug :app:assembleDebugAndroidTest
# With the local API pointing to a disposable test database:
bash gradlew :app:testDebugUnitTest -ProlangIntegrationUrl=http://127.0.0.1:3000
```

The optional contract test creates a fixture learner and exchanges data between
two Android Room databases using the actual API. Device tests use
`bash gradlew :app:connectedDebugAndroidTest` with an emulator or USB-connected
device. Local tests do not deploy to Vercel.
