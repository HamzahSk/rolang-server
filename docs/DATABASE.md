# MongoDB database structure

Database configuration consists of `MONGODB_URI` and `MONGODB_DB_NAME`. The database
name is explicit; the URI path does not override it. Atlas SRV URLs enable TLS.

`src/db.js` creates one MongoClient lazily, cached globally per warm Vercel
instance. Concurrent cold requests share its connection and initialization
promises. Failed initial connections clear the promise so a later request can
retry; the driver reconnects existing pools after socket failures. Requests
never close the client. Optional application settings are separate from MongoDB.

The pool allows five connections, no minimum connections, two simultaneous
connection attempts and 60-second idle eviction. Selection, connection and queue
waits are five seconds. Operations have a 15-second default deadline; initialization
has a ten-second total deadline. API transactions have a 20-second total deadline
and bounded 250ms session cleanup. Administration imports have a longer budget.
The pinned MongoDB driver 6.21.0 supports these client operation deadlines.

## Collections

| Collection | Identity / relationship | Stored data |
| --- | --- | --- |
| users | UUID string; unique email | Password hash, display name, role, creation date, learning revision |
| sessions | Token hash; user_id | Expiration and creation dates |
| stories | Story ID | Exact root JSON, translations, sentences, exercises, metadata, string version, dates and counts |
| story_chapters | Deterministic story/chapter hash | Original chapter ID, positive position, exact learning content, vocabulary, hash version |
| story_vocabulary | Deterministic story/ordinal hash | Ordered full lexemes with translations and practice metadata |
| dictionary | Deterministic language/word hash | Full global lexicon, including words unused in story text |
| learning_records | Deterministic user/kind/key hash | Progress, vocabulary, reviews, preferences, tombstones and revisions |
| sync_operations | Deterministic user/operation hash | Payload fingerprint and creation date |
| auth_attempts | Hashed rate-limit bucket | Shared count and expiration |
| corpus_imports | Corpus content hash | Verified course/import metadata and import date |
| counters | Named counters | BSON Long story version and corpus import serialization |

Identifiers, localized fields and versions retain their API meaning. New public
content uses only `id` and `fil`. The dictionary validator deliberately continues
to tolerate legacy `en`/`tl` rows in place so an upgrade never has to delete them;
API validation and corpus imports accept only the focused pair. Internal
compound hashes are not returned to clients. Existing documents, additional
fields and unused administration records are preserved by initialization.

## Initialization and readiness

`src/schema.js` defines collection validators and indexes. Every database-dependent
route goes through `store.scope()` or a transaction that calls it. Initialization:

1. Pings MongoDB and verifies replica-set/sharded transaction support.
2. Creates missing collections with validators, safely handling concurrent creation.
3. Repairs mismatched validator definitions/enforcement using `collMod`.
4. Creates missing indexes; incompatible definitions or duplicate data fail explicitly.
5. Verifies actual collection validators and index definitions on the server.

Initialization never edits, replaces or deletes existing documents. Unique index
failures require reviewing conflicting records; they never trigger cleanup.
Ordinary requests cache verified readiness for 60 seconds. Health checks force
verification and repair, sharing any in-flight initialization. Failed checks clear
the readiness cache and later requests retry. No administration markers gate readiness.

The database user needs read/write access, collection/index creation, collection
and index listing, and `collMod` privileges to repair validators. Atlas database
roles `readWrite` and `dbAdmin`, scoped to the target database, cover these actions.

Indexes support unique emails, dictionary identities, chapter identities/order,
learning natural keys and sync operation identities; published catalog pagination,
category/difficulty/language filters and Indonesian/Filipino text search; chapter/vocabulary
order; user revision scans; session/rate-limit expiration lookups. Text search
uses `default_language=none` and the name `stories_search_id_fil`. MongoDB permits
only one text index per collection, so existing deployments run the explicit
language-pair migration before normal readiness checks. Session and auth expiration indexes retain existing
behavior without automatic TTL deletion.

## Content and learning consistency

Stories embed bounded learning content and exact authored chapter arrays for
existing client compatibility. Independently fetched chapters and ordered story
vocabulary live in separate collections. The full dictionary and user histories
are separate too. All writers check the 16MiB BSON limit with 64KiB headroom;
API bodies retain the 2MB limit. Oversized content fails explicitly without truncation.
Images remain URL/illustration metadata.

Chapters sort by positive position, preserving gaps. Stories without stored chapters
derive their authored chapters or a `main` chapter. Full content retains paragraph
order, translations, speakers, objectives, notes, focus, pronunciation, exercises,
vocabulary and practice fields. Importing the bundled corpus is a separate,
repeatable administration action; API requests never read local content files.

Multi-collection content reads use snapshot transactions. Story/chapter/vocabulary
writes and version increments commit atomically. Unchanged chapters retain their
content-hash versions. Transient transaction conflicts retry aborted work; uncertain
commit retries do not replay the business callback.

Learning writes touch each user's revision counter within their transaction.
Operation fingerprints deduplicate retries, and changed UUID reuse returns 409.
Completion remains true until deleted. Tombstones and operation IDs have no TTL,
so offline devices cannot resurrect deleted data. Existing revisions are preserved;
values outside the safe integer range fail explicitly.

Story deletion removes chapters and vocabulary transactionally and preserves
learning history. There is no public account deletion endpoint. Administrative
account removal must also remove its sessions, learning records and operations
transactionally. See [Learning system](LEARNING_SYSTEM.md).
