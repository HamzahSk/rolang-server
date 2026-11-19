# MongoDB database structure

Runtime reads only MONGODB_URI and MONGODB_DB_NAME through src/config.js.
Atlas mongodb+srv:// URLs are supported, including verified TLS and SRV discovery.
There is no PostgreSQL fallback and no implicit database name from a URI path.

src/db.js creates one MongoClient lazily. Concurrent first requests share its
connection promise; warm Vercel invocations share the driver's pool. Failed
initial connections clear the promise so a later request can retry. The driver
reconnects existing pools after socket failures. Requests never close the client.

The default pool has at most five connections, no minimum connections, two
simultaneous connection attempts, and 60-second idle eviction. Selection,
connection and queue waits are five seconds. Client operations have a 15-second
default deadline; readiness checks have a ten-second total deadline. API
transactions have a 20-second total deadline and bounded 250ms session cleanup.
Scripts may request a longer transaction budget. The Core transaction helper
passes the remaining deadline to cursor reads, writes and commit attempts,
retries transient conflicts, and retries uncertain commits without replaying
their callback.

The official driver is pinned to 6.21.0 because it implements client-side
timeoutMS. Newer available releases currently ignore that option. Upgrade it
only with the real cursor, transaction, socket and deadline tests passing.

## Collections

| Collection | Identity / relationship | Stored data |
| --- | --- | --- |
| users | Original UUID string as _id; unique email | Original scrypt password hash, display name, role, creation date, per-user learning_revision |
| sessions | Original token hash as _id; user_id references users | Expiration and creation dates; original bearer tokens continue working |
| stories | Original text ID as _id | Family/category/difficulty/status, exact root content JSON, decimal-string version, dates, counts, supported languages |
| story_chapters | Deterministic SHA-256 of story ID and chapter ID | story_id, original chapter ID/position/content/vocabulary/version, sentence count |
| story_vocabulary | Deterministic SHA-256 of story ID and ordinal | Ordered story-owned lexeme documents, including all translations/practice metadata |
| dictionary | Deterministic SHA-256 of language and word | Complete global lexicon, including entries unused by story text |
| learning_records | SHA-256 of user ID, kind and natural key | Exact progress/vocabulary/review/preferences data, tombstones, numeric revision and update date |
| sync_operations | SHA-256 of user ID and operation UUID | Original payload fingerprint and creation date |
| auth_attempts | Original hashed bucket as _id | Shared attempt count and expiration |
| corpus_imports | Original corpus source hash as _id | Complete course/import metadata and original import date |
| counters | Named counters | BSON Long story-version counter and corpus import serialization |
| schema_migrations | MongoDB schema version | Completed MongoDB initialization marker |
| postgres_schema_migrations | Original SQL migration name as _id | Retained PostgreSQL migration history |
| database_imports | postgresql | Import state, source fingerprint, counts, and last verification report |

Original UUIDs, story/chapter IDs, natural keys, operation IDs, fingerprints and
versions retain their API meaning. MongoDB-only compound _id values are never
returned to clients. Dates retain the millisecond precision exposed by the old
Node/PostgreSQL API. Additional source SQL columns are retained under
postgres_extra_fields rather than discarded.

## Content size and access

Stories embed bounded root learning content and localized text. Exact authored
chapter arrays remain in root content for legacy/admin compatibility; independently
fetched chapters are referenced through story_chapters. The full root dictionary
is stored as ordered story_vocabulary documents, keeping dictionary growth out
of a single story document. Each chapter embeds its own bounded dictionary for
one-query reading. User histories and the global dictionary are separate
collections and never grow an account/story document.

API authoring retains the existing 2MB request limit and Zod limits. All content
writers/importers preflight BSON document size below MongoDB's 16MiB limit with
64KiB headroom. Oversized legacy content fails explicitly and leaves PostgreSQL
intact; it is never truncated. Images remain URL/illustration metadata.

Chapter ordering uses original positive positions, including gaps. Legacy stories
without stored chapters derive their authored chapters or chapter main. Full
content retains paragraph order, all three translations, speakers, objectives,
notes, focus, pronunciation, exercises, vocabulary and dictionary practice data.

Content reads spanning collections use snapshot transactions. Story content,
chapter replacements, dictionary replacements and version increments commit
atomically. A chapter response cannot carry an older story version with new text.
Unchanged chapter content retains its SHA-256 version.

## Indexes and validation

src/schema.js is the single definition of validators/indexes. Indexes cover:

- Unique email, dictionary (language,word), chapter identities/positions, learning
  natural keys and sync operation identities.
- Published catalog pagination plus category, difficulty, language and family filters.
- MongoDB text search over localized titles/summaries, category and family with
  default_language=none for the multilingual corpus.
- Chapter/vocabulary ordering and vocabulary language filtering.
- Per-user revision scans and kind/deleted/key pagination.
- Session owner/expiration and authentication bucket expiration.

The learning revision index preserves PostgreSQL's non-unique index contract;
normal API writes allocate strictly increasing revisions with the user counter.
Source vocabulary ordinals preserve legacy arrays even if they contain duplicates.

migrate.js creates collections, validators and indexes without deleting data.
It repairs incompatible validators using collMod when the migration role permits
it; incompatible index definitions fail explicitly for operator review.
Health checks verify the migration marker, collection validators, index definitions,
replica-set/sharded transaction support and data-import state. They are read-only.

## Learning consistency and maintenance

All learning writes touch the user's document in their transaction. Concurrent
devices must retry before publishing revisions. Revisions are now allocated per
user; original imported revisions and their gaps remain unchanged. Each user's
counter starts at or above their maximum imported revision, preserving old sync
cursors. Revisions outside JavaScript's safe integer range abort migration.

Operation fingerprints deduplicate retries. Changed reuse returns 409.
Progress preserves completed=true until deleted. Tombstones and operation IDs
are retained without TTL so offline devices cannot resurrect deleted data.

MongoDB has no SQL foreign-key cascades. API story deletion removes its chapters
and vocabulary in one transaction and preserves learner history. There is no
public account-delete endpoint. Administrative account removal must transactionally
delete owned sessions, records and operations. The importer verifies all five
user/story reference relationships.

Expiration indexes intentionally have no automatic TTL: expired PostgreSQL
sessions and rate-limit records are preserved and verified during transfer.
After live verification, administrators may remove expired sessions/auth_attempts
using expires_at filters. Keep learning tombstones and operation IDs until an
explicit device-retention policy exists. Back up Atlas and keep the PostgreSQL
source/backups until the deployed API and Android consumers are verified.
