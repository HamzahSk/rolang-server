# Ro-Lang server

The Express/PostgreSQL backend for [Ro-Lang Android](../rolang-app/README.md).
It serves multilingual stories and synchronizes accounts, vocabulary statuses,
reading progress, spaced repetition schedules, review history, and preferences.
The Android app caches opened stories and supports durable offline downloads without an account.
See [Migration](docs/MIGRATION.md) to import the Android library before rollout.

Start with the [overview and local setup](docs/README.md), then use:

- [Stories](docs/STORIES.md): create, edit, and publish content, with a complete JSON example.
- [API](docs/API.md): every endpoint, request shapes, responses, and curl examples.
- [Database](docs/DATABASE.md): tables, relationships, migrations, and maintenance.
- [Learning system](docs/LEARNING_SYSTEM.md): colors, mastery, reviews, and synchronization.
- [Deployment](docs/DEPLOYMENT.md): environment settings, Android config, and Vercel.

+