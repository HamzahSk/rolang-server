import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { isDeepStrictEqual } from 'node:util';
import { Long } from 'mongodb';
import { database } from '../src/db.js';
import { reportError } from '../src/errors.js';
import { documentId, assertDocumentSize, safeRevision, storyVersion } from '../src/documents.js';
import { chapterDocuments, vocabularyDocuments } from '../src/stories.js';
import { postgresDatabase } from './postgres/db.js';
import { checkSchema } from '../src/schema.js';
import { countExercises } from './import-corpus.js';

// Source identifiers come from this inspected schema, never from API input.
const tableKeys = {
  users: ['id'], sessions: ['token_hash'], stories: ['id'], story_chapters: ['story_id', 'position'],
  learning_records: ['user_id', 'kind', 'key'], sync_operations: ['user_id', 'operation_id'],
  auth_attempts: ['bucket'], dictionary: ['language', 'word'], corpus_imports: ['source_hash'], schema_migrations: ['name'],
};
const requiredTables = ['users', 'sessions', 'stories', 'learning_records', 'sync_operations', 'auth_attempts'];
const knownColumns = {
  users: ['id', 'email', 'password_hash', 'display_name', 'role', 'created_at'],
  sessions: ['token_hash', 'user_id', 'expires_at', 'created_at'],
  stories: ['id', 'family', 'category', 'difficulty', 'status', 'content', 'vocabulary', 'version', 'created_at', 'updated_at'],
  story_chapters: ['story_id', 'id', 'position', 'content', 'vocabulary', 'version'],
  learning_records: ['user_id', 'kind', 'key', 'data', 'deleted', 'revision', 'updated_at'],
  sync_operations: ['user_id', 'operation_id', 'fingerprint', 'created_at'],
  auth_attempts: ['bucket', 'attempts', 'expires_at'],
  dictionary: ['language', 'word', 'content'], corpus_imports: ['source_hash', 'metadata', 'imported_at'],
  schema_migrations: ['name', 'applied_at'],
};
const quote = value => '"' + value.replaceAll('"', '""') + '"';
const sourceTable = (schema, name) => quote(schema) + '.' + quote(name);
const fail = (code, reason) => Object.assign(new Error('PostgreSQL import failed.'), { code, reason });
const canonical = value => {
  if (value instanceof Date) return { $date: value.toISOString() };
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])]));
  return value;
};
const matches = (actual, expected) => actual && Object.entries(expected).every(([key, value]) => isDeepStrictEqual(actual[key], value));
function extraColumns(table, source) {
  const extras = Object.fromEntries(Object.entries(source).filter(([key]) => !knownColumns[table].includes(key)));
  return Object.keys(extras).length ? { postgres_extra_fields: extras } : {};
}
function mapRow(table, row) {
  let document;
  if (table === 'users') {
    const { id, ...fields } = row;
    document = { _id: id, ...Object.fromEntries(knownColumns.users.filter(key => key !== 'id').map(key => [key, fields[key]])) };
  } else if (table === 'sessions') {
    document = { _id: row.token_hash, user_id: row.user_id, expires_at: row.expires_at, created_at: row.created_at };
  } else if (table === 'learning_records') {
    document = { _id: documentId(row.user_id, row.kind, row.key), user_id: row.user_id, kind: row.kind, key: row.key,
      data: row.data, deleted: row.deleted, revision: safeRevision(row.revision), updated_at: row.updated_at };
  } else if (table === 'sync_operations') {
    document = { _id: documentId(row.user_id, row.operation_id), user_id: row.user_id, operation_id: row.operation_id,
      fingerprint: row.fingerprint, created_at: row.created_at };
  } else if (table === 'auth_attempts') {
    document = { _id: row.bucket, attempts: row.attempts, expires_at: row.expires_at };
  } else if (table === 'dictionary') {
    document = { _id: documentId(row.language, row.word), language: row.language, word: row.word, content: row.content };
  } else if (table === 'corpus_imports') {
    document = { _id: row.source_hash, metadata: row.metadata, imported_at: row.imported_at };
  } else if (table === 'schema_migrations') {
    document = { _id: row.name, applied_at: row.applied_at };
  } else if (table === 'story_chapters') {
    document = { _id: documentId(row.story_id, row.id), story_id: row.story_id, id: row.id,
      position: row.position, content: row.content, vocabulary: row.vocabulary, version: row.version,
      sentence_count: row.content.sentences.length };
  }
  return assertDocumentSize({ ...document, ...extraColumns(table, row) });
}
async function inspectSource(client, schema) {
  const { rows } = await client.query(
    "SELECT table_name FROM information_schema.tables WHERE table_schema=$1 AND table_type='BASE TABLE'", [schema]);
  const tables = new Set(rows.map(row => row.table_name));
  if (requiredTables.some(name => !tables.has(name))) throw fail('IMPORT_INVALID_SOURCE', 'missing_tables');
  if ([...tables].some(name => !Object.hasOwn(tableKeys, name))) throw fail('IMPORT_INVALID_SOURCE', 'unsupported_tables');
  const counts = {};
  for (const name of Object.keys(tableKeys)) {
    counts[name] = tables.has(name) ? safeRevision((await client.query('SELECT count(*)::text AS count FROM ' + sourceTable(schema, name))).rows[0].count) : 0;
  }
  return { tables, counts };
}
async function scan(client, schema, table, action) {
  const order = tableKeys[table].map(quote).join(',');
  await client.query('DECLARE source_rows NO SCROLL CURSOR FOR SELECT * FROM ' + sourceTable(schema, table) + ' ORDER BY ' + order);
  try {
    while (true) {
      const { rows } = await client.query('FETCH FORWARD 250 FROM source_rows');
      if (!rows.length) break;
      await action(rows);
    }
  } finally { await client.query('CLOSE source_rows'); }
}
async function ensureDocuments(db, name, documents, verifyOnly) {
  if (!documents.length) return { inserted: 0, matched: 0 };
  for (const document of documents) assertDocumentSize(document);
  const filter = { _id: { $in: documents.map(document => document._id) } };
  const actual = new Map((await db.collection(name).find(filter).toArray()).map(row => [row._id, row]));
  const missing = [];
  for (const document of documents) {
    const previous = actual.get(document._id);
    if (previous && !matches(previous, document))
      throw fail(verifyOnly ? 'IMPORT_VERIFICATION_FAILED' : 'IMPORT_CONFLICT', 'different_target_content');
    if (!previous) {
      if (verifyOnly) throw fail('IMPORT_VERIFICATION_FAILED', 'missing_target_documents');
      missing.push(document);
    }
  }
  let inserted = 0;
  if (missing.length) {
    try {
      const result = await db.collection(name).bulkWrite(missing.map(document => ({
        updateOne: { filter: { _id: document._id }, update: { $setOnInsert: document }, upsert: true },
      })), { ordered: true });
      inserted = result.upsertedCount;
    } catch (error) {
      if (error.code === 11000) throw fail('IMPORT_CONFLICT', 'duplicate_natural_key');
      throw error;
    }
  }
  const verified = new Map((await db.collection(name).find(filter).toArray()).map(row => [row._id, row]));
  if (documents.some(document => !matches(verified.get(document._id), document)))
    throw fail('IMPORT_VERIFICATION_FAILED', 'different_target_content');
  return { inserted, matched: documents.length };
}
export async function verifyRelationships(db) {
  const relationships = [
    ['sessions', 'users', 'user_id'], ['learning_records', 'users', 'user_id'], ['sync_operations', 'users', 'user_id'],
    ['story_chapters', 'stories', 'story_id'], ['story_vocabulary', 'stories', 'story_id'],
  ];
  for (const [child, parent, field] of relationships) {
    const orphan = await db.collection(child).aggregate([
      { $lookup: { from: parent, localField: field, foreignField: '_id', as: 'parent' } },
      { $match: { 'parent.0': { $exists: false } } }, { $limit: 1 }, { $project: { _id: 1 } },
    ]).next();
    if (orphan) throw fail('IMPORT_VERIFICATION_FAILED', 'orphan_relationships');
  }
  return relationships.length;
}
export async function importPostgres(store, source, {
  schema = 'public', verifyOnly = false,
  onProgress = report => console.log(JSON.stringify({ event: 'postgres_import', ...report })),
} = {}) {
  if (!schema || Buffer.byteLength(schema) > 63 || schema.includes('\0'))
    throw fail('IMPORT_INVALID_SOURCE', 'invalid_schema');
  const db = await store.connect();
  await checkSchema(db, { allowImportInProgress: true });
  const client = await source.connect();
  let inSnapshot = false;
  const fingerprint = createHash('sha256');
  const targetCounts = {};
  const insertedCounts = {};
  let sourceCounts, maxVersion = 1n, derivedChapters = 0, vocabularyCount = 0, exercises = 0;
  const add = async (name, documents) => {
    const result = await ensureDocuments(db, name, documents, verifyOnly);
    targetCounts[name] = (targetCounts[name] ?? 0) + result.matched;
    insertedCounts[name] = (insertedCounts[name] ?? 0) + result.inserted;
  };
  const fingerprintRows = (name, rows) => {
    for (const row of rows) fingerprint.update(JSON.stringify([name, canonical(row)]) + '\n');
  };
  try {
    await client.query('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY');
    inSnapshot = true;
    const inspected = await inspectSource(client, schema);
    sourceCounts = inspected.counts;
    await onProgress({ stage: 'snapshot', sourceCounts });
    if (!verifyOnly) await db.collection('database_imports').updateOne({ _id: 'postgresql' }, {
      $set: { state: 'running', started_at: new Date() },
    }, { upsert: true });
    for (const table of Object.keys(tableKeys).filter(name => name !== 'story_chapters')) {
      if (!inspected.tables.has(table)) continue;
      await scan(client, schema, table, async rows => {
        fingerprintRows(table, rows);
        if (table !== 'stories') {
          await add(table === 'schema_migrations' ? 'postgres_schema_migrations' : table, rows.map(row => mapRow(table, row)));
          return;
        }
        for (const row of rows) {
          if (!Array.isArray(row.content?.sentences) || !Array.isArray(row.vocabulary))
            throw fail('IMPORT_INVALID_SOURCE', 'invalid_story_arrays');
          const stored = inspected.tables.has('story_chapters')
            ? (await client.query('SELECT * FROM ' + sourceTable(schema, 'story_chapters') + ' WHERE story_id=$1 ORDER BY position', [row.id])).rows : [];
          fingerprintRows('story_chapters', stored);
          const chapters = stored.length ? stored.map(chapter => mapRow('story_chapters', chapter))
            : chapterDocuments({ ...row.content, id: row.id, vocabulary: row.vocabulary });
          if (!stored.length) derivedChapters += chapters.length;
          if (chapters.some((chapter, index) => !Number.isInteger(chapter.position) || chapter.position < 1 ||
                (index > 0 && chapter.position <= chapters[index - 1].position)) ||
              !isDeepStrictEqual(chapters.flatMap(chapter => chapter.content.sentences), row.content.sentences))
            throw fail('IMPORT_INVALID_SOURCE', 'inconsistent_chapter_order_or_text');
          const version = storyVersion(row.version ?? '1');
          if (BigInt(version) > maxVersion) maxVersion = BigInt(version);
          const document = assertDocumentSize({
            _id: row.id, family: row.family, category: row.category, difficulty: row.difficulty, status: row.status,
            // Preserve the exact root JSON, including optional authored chapters
            // and fields unknown to current Zod. Migration never revalidates it
            // against a newer, potentially narrower authoring contract.
            content: row.content, version, created_at: row.created_at, updated_at: row.updated_at,
            sentence_count: row.content.sentences.length, chapter_count: chapters.length,
            languages: Object.keys(row.content.title ?? {}), ...extraColumns('stories', row),
          });
          const words = vocabularyDocuments(row.id, row.vocabulary);
          await add('stories', [document]);
          await add('story_chapters', chapters);
          await add('story_vocabulary', words);
          if (await db.collection('story_chapters').countDocuments({ story_id: row.id }) !== chapters.length ||
              await db.collection('story_vocabulary').countDocuments({ story_id: row.id }) !== words.length)
            throw fail('IMPORT_VERIFICATION_FAILED', 'different_story_child_counts');
          vocabularyCount += words.length;
          exercises += countExercises(row.content, chapters.map(chapter => chapter.content));
        }
      });
      await onProgress({ stage: 'table_verified', table, matched: sourceCounts[table], inserted: insertedCounts[table === 'schema_migrations' ? 'postgres_schema_migrations' : table] ?? 0 });
    }
    // Per-user cursors retain the original numeric revisions and start above
    // every imported record. $max never resets a counter on an identical retry.
    const revisions = await client.query('SELECT u.id,COALESCE(MAX(r.revision),0)::text AS revision FROM ' +
      sourceTable(schema, 'users') + ' u LEFT JOIN ' + sourceTable(schema, 'learning_records') +
      ' r ON r.user_id=u.id GROUP BY u.id');
    for (let offset = 0; offset < revisions.rows.length; offset += 250) {
      const batch = revisions.rows.slice(offset, offset + 250);
      if (!verifyOnly && batch.length) await db.collection('users').bulkWrite(batch.map(row => ({
        updateOne: { filter: { _id: row.id }, update: { $max: { learning_revision: safeRevision(row.revision) } } },
      })));
      const users = new Map((await db.collection('users').find({ _id: { $in: batch.map(row => row.id) } }).toArray()).map(row => [row._id, row]));
      if (batch.some(row => !users.has(row.id) || safeRevision(users.get(row.id).learning_revision ?? 0) < safeRevision(row.revision)))
        throw fail('IMPORT_VERIFICATION_FAILED', 'revision_counter_mismatch');
    }
    if (!verifyOnly) await db.collection('counters').updateOne({ _id: 'story_version' },
      { $max: { value: Long.fromString(maxVersion.toString()) } }, { upsert: true });
    const counter = await db.collection('counters').findOne({ _id: 'story_version' });
    if (!counter || BigInt(String(counter.value)) < maxVersion) throw fail('IMPORT_VERIFICATION_FAILED', 'story_counter_mismatch');
    for (const [table, count] of Object.entries(sourceCounts)) {
      const target = table === 'schema_migrations' ? 'postgres_schema_migrations' : table;
      const expected = count + (table === 'story_chapters' ? derivedChapters : 0);
      if ((targetCounts[target] ?? 0) !== expected) throw fail('IMPORT_VERIFICATION_FAILED', 'count_mismatch');
    }
    const relationships = await verifyRelationships(db);
    const report = { status: 'verified', sourceCounts, targetCounts, insertedCounts,
      derivedChapters, storyVocabulary: vocabularyCount, exercises, relationships, sourceHash: fingerprint.digest('hex') };
    await client.query('COMMIT');
    inSnapshot = false;
    if (!verifyOnly) await db.collection('database_imports').updateOne({ _id: 'postgresql' }, {
      $set: { state: 'verified', verified_at: new Date(), report },
    });
    await onProgress({ stage: 'complete', ...report });
    return report;
  } catch (error) {
    if (inSnapshot) await client.query('ROLLBACK').catch(rollback => reportError(rollback, 'postgres_snapshot_rollback'));
    if (!verifyOnly) await db.collection('database_imports').updateOne({ _id: 'postgresql' },
      { $set: { state: 'failed', failed_at: new Date() } }, { upsert: true }).catch(() => {});
    throw error;
  } finally { client.release(); }
}
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const store = database();
  let source;
  try {
    const args = process.argv.slice(2);
    if (args.some(arg => arg !== '--verify')) throw fail('IMPORT_INVALID_SOURCE', 'invalid_arguments');
    source = postgresDatabase();
    await importPostgres(store, source, { schema: process.env.POSTGRES_SCHEMA || 'public', verifyOnly: args.includes('--verify') });
  } catch (error) {
    reportError(error, 'postgres_import');
    console.error('PostgreSQL import/verification failed. Keep the source database intact. Check source schema, target conflicts, document sizes, counts, and relationships; see docs/MIGRATION.md.');
    process.exitCode = 1;
  } finally { await source?.end(); await store.close(); }
}
