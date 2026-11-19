# Historical PostgreSQL / Vercel investigation

This report records investigation and verification performed for the previous
PostgreSQL release. Its production observations and test counts are historical.
The current runtime uses MongoDB Atlas; see [the MongoDB migration report](MONGODB_MIGRATION_REPORT.md)
and [current deployment instructions](DEPLOYMENT.md). Existing entrypoint fixes
were retained. This migration has not been deployed to the live Vercel project.

The historical investigation and changes were confined to the standalone
`rolang-server` repository. That release used Express 5, Node.js 22, Zod and PostgreSQL.
The actual managed database provider cannot be identified from this checkout:
there is no production database configuration or private Vercel project link.

## Reproduced causes and production evidence

Public requests to `https://rolang-server.vercel.app` reproduced these responses:

| Request | Observed response before the fix |
| --- | --- |
| `/` | Vercel 500 `FUNCTION_INVOCATION_FAILED` |
| `/health` | Express JSON 404 |
| `/api/v1/health` | Express JSON 503 `SERVICE_UNAVAILABLE` |
| `/api/v1/stories` | Express JSON 503 `SERVICE_UNAVAILABLE` |
| `/api/v1/me` without a token | Express JSON 401 |
| `/api/v1/stories?limit=-1` | Express JSON 400 |

Vercel's Express builder detects `src/app.js` because that filename imports
Express. It exports only the `createApp` factory, with no default request handler
and no listening server. The Vercel Node loader cannot invoke that module:
running it in Vercel's Node development runtime reproduces
`Can't detect way to handle request` followed by an invocation failure.
The original configuration did not explicitly disable framework detection,
allowing this incompatible root function alongside the valid `api/index.js`
handler. This is a reproducible source/configuration defect matching the root
invocation failure. The fixed configuration explicitly selects Other with
`framework: null`, retaining the existing catch-all rewrite and API entrypoint.

The pool also lacked an `error` listener. PostgreSQL emits idle connection errors
outside request promises; Node terminates on an unhandled `error` event. This is
an additional confirmed crash path, now tested with an actual terminated database
connection. Pool lifecycle attachment closes idle connections before Vercel
suspension while preserving reuse during active/warm requests.

The production database-dependent failures are separate from the root entrypoint
failure. The original error middleware suppressed all database causes as the
same unlogged 503. A configured environment variable does not prove that its
URL, TLS, network access, role permissions or schema are correct. Migration 002
is required by all story catalog/detail/chapter queries. Local tests verify both
migrations and correct queries; production migration state and connection
failures remain unknown until runtime diagnostics or database access are available.
No claim that production credentials are missing is supported by these observations.

## Implemented fixes

- Explicit API function deployment, deterministic `npm ci`, Node.js 22, and no
  static-site build/output requirement. `npm run build` checks source syntax,
  handler exports and Vercel configuration without opening a database connection.
- Shared pool with idle error handling, Vercel lifecycle integration, bounded
  connection/query waits, and broken-client removal on failed rollback.
- Equivalent `/health` and `/api/v1/health` readiness checks for connectivity,
  migration history, expected schema and runtime permissions; safe 503 on failure.
- Safe diagnostic codes for connection, TLS, schema and permission failures;
  unexpected programming/query errors correctly return 500. No failed operation
  is converted to HTTP 200. Import and migration errors do not print raw secrets.
- Read-only `npm run doctor`, expanded API and failure regression coverage,
  and deployment/troubleshooting documentation.

Existing stories, accounts, learning records, migrations and API paths are
preserved. No production writes, imports or destructive schema changes were made.

## Verification and remaining checks

`npm ci` and the production dependency audit pass with zero reported
vulnerabilities. `npm run build` passes without database credentials.
All 19 tests pass, including two consecutive full runs after isolating the API
suite's rate-limit fixtures in its own schema. The real PostgreSQL suite covers
all API route families, migration idempotency,
all 20 imported stories/chapters and 1,204 vocabulary entries, authentication,
admin operations, user isolation, synchronization, schema drift, secret redaction,
failed rollback and connection recovery.

An actual local `vercel build --prod --standalone` succeeds using temporary,
local-only project settings. Output contains exactly the `api/index.js` function,
Node.js 22 runtime, a 30-second function limit and the existing catch-all rewrite.
Invoking the packaged handler through Vercel's Node runtime returns 200 for both
health paths and the catalog, 401 for unauthenticated `/api/v1/me`, and JSON 404
for `/`, with a disposable local PostgreSQL database.
This validates packaging and overriding an Express preset, but it does not
validate remote Vercel settings, production credentials or a deployed fix.

Authenticated Vercel CLI access was unavailable; direct CLI access failed login
validation. No deployment was created and private production logs could not be
retrieved. Follow [Deployment](DEPLOYMENT.md#diagnose-connectivity-or-readiness) to link
the real project, run the doctor with production configuration, apply pending
migrations if indicated, redeploy, inspect logs, and verify health/catalog and
authenticated APIs. Do not replace existing story content to diagnose a failure.

## Files changed

- `vercel.json`, `package.json`, `package-lock.json`
- `src/app.js`, `src/db.js`, `src/errors.js`, new `src/health.js`
- New `scripts/build.js`, new `scripts/doctor.js`, `scripts/migrate.js`, `scripts/import-corpus.js`
- `test/api.test.js`, `test/content.test.js`, new `test/runtime.test.js`
- `docs/API.md`, `docs/DATABASE.md`, `docs/DEPLOYMENT.md`, `docs/README.md`, this report
