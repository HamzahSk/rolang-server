# Ro-Lang server

Node.js 22, Express 5 and the official MongoDB driver serve the focused Indonesian
(`id`) → Filipino/Tagalog (`fil`) course,
ordered chapters, translations, vocabulary, exercises, accounts and offline
learning synchronization. Existing v1 routes and Android response shapes remain
compatible. MongoDB is the only database.

Set `MONGODB_URI` and `MONGODB_DB_NAME` from [.env.example](.env.example), then run:

```sh
npm ci
node --env-file=.env src/local.js
```

Every database-dependent route initializes MongoDB through the shared connection
manager. Missing collections and indexes are created automatically and their
actual definitions are verified. Existing documents are preserved. Health checks
at `/health` and `/api/v1/health` verify connectivity and initialization; genuine
connection, permission, index or transaction-support failures return safe 503s.
No release marker or separate schema initialization command is required.

For an existing deployment, migrate the search index and replace the old course
documents with the focused corpus. On an empty database, the migration is a no-op:

```sh
node --env-file=.env scripts/migrate-language-pair.js
node --env-file=.env scripts/import-corpus.js --replace-existing
node --env-file=.env scripts/import-corpus.js --verify
```

This imports 21 ordered A1 units, 30 chapter records, 494 Filipino dictionary entries,
and 150 exercises. Repeating the import avoids duplicates; differing existing content stops the
import for review. The API reads content directly from MongoDB and requires no
persistent local files. The bundled JSON files contain only `id`/`fil` learning
content. The language-pair migration changes only the text-search index; learner
records are retained.

- [Local setup](docs/README.md)
- [Database](docs/DATABASE.md): connections, collections, indexes and transactions
- [API](docs/API.md): existing contracts, pagination and search
- [Stories](docs/STORIES.md): authoring and publishing
- [Learning system](docs/LEARNING_SYSTEM.md): offline synchronization
- [Deployment](docs/DEPLOYMENT.md): Atlas, Vercel, diagnostics and real database tests
- [Language-pair migration](docs/MIGRATION.md): safe production upgrade order
