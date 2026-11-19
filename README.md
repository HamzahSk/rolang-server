# Ro-Lang server

The Node.js 22 / Express 5 backend now uses MongoDB Atlas through the official
MongoDB driver. Existing v1 API routes and Android response shapes are preserved,
including multilingual stories, ordered chapters, offline synchronization,
vocabulary statuses, reviews, preferences, and revocable sessions.

Start with [local setup](docs/README.md), then use:

- [Migration](docs/MIGRATION.md): transfer existing PostgreSQL data without changing it.
- [Database](docs/DATABASE.md): MongoDB collections, indexes, and transaction rules.
- [API](docs/API.md): endpoint contracts, pagination, search, and examples.
- [Stories](docs/STORIES.md): authoring, publishing, and complete JSON examples.
- [Learning system](docs/LEARNING_SYSTEM.md): learner records and offline behavior.
- [Deployment](docs/DEPLOYMENT.md): Atlas configuration, Vercel, and real database tests.
- [Migration report](docs/MONGODB_MIGRATION_REPORT.md): implementation and verification results.

Runtime requires MONGODB_URI and MONGODB_DB_NAME. Node does not load .env
automatically; use --env-file=.env locally. Initialization and imports are explicit
administration commands and never run during a build, module import, or request.

The original SQL migrations, PostgreSQL configuration example, and source assets
remain available. pg is a development dependency used only by migration/rollback
tools; no API module imports it. Keep the source database and backups until the
Atlas import and deployed API have been verified.
