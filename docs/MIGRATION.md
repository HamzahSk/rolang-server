# Indonesian → Filipino language-pair migration

This upgrade removes English from exposed learning content and changes the former
Tagalog code `tl` to `fil`. It does not delete accounts, learning records, review
history, reading progress, or unrelated legacy documents.

1. Back up the target MongoDB database and stop content editing during the import.
2. From `rolang-server/`, replace the legacy story text-search index:

   ```sh
   node --env-file=.env scripts/migrate-language-pair.js
   ```

   MongoDB allows one text index per collection. The script recognizes only the
   old `stories_search` index, creates `stories_search_id_fil`, restores the old
   index if creation fails, and reports that zero learning records changed.
3. Replace the old bundled story documents with the reviewed `id`/`fil` corpus:

   ```sh
   node --env-file=.env scripts/import-corpus.js --replace-existing
   node --env-file=.env scripts/import-corpus.js --verify
   node --env-file=.env scripts/doctor.js
   ```

   `--replace-existing` is required only when the same story IDs still contain the
   former three-language content. The import transaction updates course content,
   chapters, and Filipino dictionary entries; it does not touch `learning_records`.
4. Deploy the server, verify `/health`, and then distribute the Android build.

Android Room migration 5→6 merges `tl` Indonesian-reference vocabulary, SRS,
reviews, readings, exercises, and pending sync keys into `fil`. Records belonging
to other historical language pairs remain locally stored but hidden, and the sync
client ignores their obsolete queued operations. Downloaded legacy server records
are likewise filtered unless they belong to `tl`/`fil` with Indonesian reference.

The server retains old learning records and accepts legacy dictionary rows at the
database-validator level so upgrades remain non-destructive. New API writes,
course imports, and Android uploads accept only Indonesian → Filipino.
