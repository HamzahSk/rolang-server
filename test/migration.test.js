import { before, after, test } from 'node:test';
import assert from 'node:assert/strict';
import request from 'supertest';
import { mongoFixture } from './helpers.js';
import { postgresFixture } from './postgres-fixture.js';
import { migrate } from '../scripts/migrate.js';
import { importPostgres, verifyRelationships } from '../scripts/import-postgres.js';
import { createApp } from '../src/app.js';

let source;
before(async () => { source = await postgresFixture(); });
after(async () => { await source?.close(); });

test('PostgreSQL transfers every entity with stable IDs, exact content, chapter order, and repeatable verification', async () => {
  const fixture = await mongoFixture('migration');
  const logs = [];
  try {
    await migrate(fixture.store);
    const first = await importPostgres(fixture.store, source.pool, { schema: source.schema, onProgress: log => logs.push(log) });
    assert.equal(first.status, 'verified');
    assert.deepEqual(first.sourceCounts, {
      users: 2, sessions: 2, stories: 20, story_chapters: 21, learning_records: 4, sync_operations: 1,
      auth_attempts: 2, dictionary: 1204, corpus_imports: 1, schema_migrations: 2,
    });
    assert.equal(first.targetCounts.story_chapters, 21);
    assert.equal(first.targetCounts.stories, 20);
    assert.equal(first.relationships, 5);
    const before = await fixture.db.collection('stories').find().sort({ _id: 1 }).toArray();
    const second = await importPostgres(fixture.store, source.pool, { schema: source.schema, onProgress: () => {} });
    assert.equal(second.sourceHash, first.sourceHash);
    assert.ok(Object.values(second.insertedCounts).every(count => count === 0));
    assert.deepEqual(await fixture.db.collection('stories').find().sort({ _id: 1 }).toArray(), before);
    const verified = await importPostgres(fixture.store, source.pool, { schema: source.schema, verifyOnly: true, onProgress: () => {} });
    assert.equal(verified.sourceHash, first.sourceHash);
    assert.equal(await fixture.db.collection('database_imports').countDocuments(), 1);
    assert.equal(await fixture.db.collection('sessions').countDocuments(), 2, 'Expired source sessions are retained during migration.');
    assert.equal(await fixture.db.collection('auth_attempts').countDocuments(), 2);
    for (const row of source.rows) {
      const stored = await fixture.db.collection('stories').findOne({ _id: row.id });
      assert.deepEqual(stored.content, row.content);
      assert.equal(stored.status, row.status);
      assert.equal(stored.version, String(row.version));
      assert.deepEqual(stored.created_at, row.created_at);
      assert.deepEqual(stored.updated_at, row.updated_at);
      const vocabulary = (await fixture.db.collection('story_vocabulary').find({ story_id: row.id }).sort({ position: 1 }).toArray()).map(word => word.content);
      assert.deepEqual(vocabulary, row.vocabulary);
    }
    for (const user of source.users) {
      const stored = await fixture.db.collection('users').findOne({ _id: user.id });
      assert.equal(stored.password_hash, user.password_hash);
      assert.deepEqual(stored.postgres_extra_fields, { legacy_flags: user.legacy_flags });
    }
    assert.deepEqual((await fixture.db.collection('learning_records').find({ user_id: source.userId }).sort({ revision: 1 }).toArray()).map(row => row.revision), [100, 250, 600, 901]);
    assert.equal((await fixture.db.collection('users').findOne({ _id: source.userId })).learning_revision, 901);
    assert.ok(logs.some(log => log.stage === 'complete'));
    assert.ok(!JSON.stringify(logs).includes(source.token));
    assert.ok(!JSON.stringify(logs).includes(process.env.TEST_POSTGRES_URL));
    assert.deepEqual((await source.pool.query('SELECT * FROM stories ORDER BY id')).rows, source.rows, 'Source content remains untouched.');
  } finally { await fixture.close(); }
});

test('existing clients retain sessions, passwords, sync cursors, retries and large decimal story versions', async () => {
  const fixture = await mongoFixture('continuity');
  try {
    await migrate(fixture.store);
    await importPostgres(fixture.store, source.pool, { schema: source.schema, onProgress: () => {} });
    const app = createApp(fixture.store);
    const bearer = 'Bearer ' + source.token;
    assert.equal((await request(app).get('/api/v1/me').set('Authorization', bearer).expect(200)).body.id, source.userId);
    const login = await request(app).post('/api/v1/auth/login').send({ email: source.email, password: source.password }).expect(200);
    assert.equal(login.body.user.id, source.userId);
    const sync = input => request(app).post('/api/v1/me/sync').set('Authorization', bearer).send(input);
    const initial = await sync({ cursor: 901, operations: [] }).expect(200);
    assert.equal(initial.body.cursor, 901);
    assert.deepEqual(initial.body.records, []);
    const replay = await sync({ cursor: 0, operations: [source.operation] }).expect(200);
    assert.equal(replay.body.cursor, 901);
    assert.equal(replay.body.records.find(row => row.kind === 'review').deleted, true);
    assert.equal(replay.body.records.find(row => row.kind === 'vocabulary').data.status, 'ALMOST_MASTERED');
    const { randomUUID } = await import('node:crypto');
    const changed = { ...source.operation, id: randomUUID(), data: { ...source.operation.data, completed: false } };
    const update = await sync({ cursor: 901, operations: [changed] }).expect(200);
    assert.equal(update.body.cursor, 902);
    assert.equal(update.body.records[0].data.completed, true);
    const firstId = source.stories[0].id;
    const story = (await request(app).get('/api/v1/stories/' + firstId + '/content').expect(200)).body;
    assert.equal(story.version, '9007199254740993');
    assert.deepEqual(story.chapters.map(chapter => chapter.id), ['opening', 'ending']);
    assert.deepEqual(story.chapters.flatMap(chapter => chapter.sentences), story.sentences);
    assert.deepEqual(story.legacyMetadata, source.rows.find(row => row.id === firstId).content.legacyMetadata);
    const manifest = await request(app).get('/api/v1/stories/' + firstId + '?view=manifest').expect(200);
    assert.equal(manifest.body.chapterCount, undefined);
    assert.equal(manifest.body.chapters.length, 2);
    const page = (await request(app).get('/api/v1/stories/' + firstId + '/chapters?limit=1').expect(200)).body;
    assert.equal(page.next, 1);
    const last = (await request(app).get('/api/v1/stories/' + firstId + '/chapters?after=1').expect(200)).body;
    assert.equal(last.chapters[0].id, 'ending');
    const admin = await request(app).post('/api/v1/auth/login').send({ email: source.users.find(user => user.role === 'admin').email, password: source.password }).expect(200);
    const draftId = source.stories.at(-1).id;
    await request(app).get('/api/v1/stories/' + draftId).expect(404);
    const published = await request(app).post('/api/v1/stories/' + draftId + '/publish').set('Authorization', 'Bearer ' + admin.body.token).send({ published: true }).expect(200);
    assert.equal(published.body.version, '9007199254740994');
  } finally { await fixture.close(); }
});

test('a source snapshot stays consistent during a concurrent PostgreSQL edit', async () => {
  const fixture = await mongoFixture('snapshot');
  const originalName = source.users.find(user => user.id === source.userId).display_name;
  try {
    await migrate(fixture.store);
    await importPostgres(fixture.store, source.pool, { schema: source.schema, onProgress: async log => {
      if (log.stage === 'snapshot') await source.base.query('UPDATE ' + source.schema + '.users SET display_name=$2 WHERE id=$1', [source.userId, 'Concurrent source edit']);
    } });
    assert.equal((await fixture.db.collection('users').findOne({ _id: source.userId })).display_name, originalName);
    assert.equal((await source.pool.query('SELECT display_name FROM users WHERE id=$1', [source.userId])).rows[0].display_name, 'Concurrent source edit');
  } finally {
    await source.base.query('UPDATE ' + source.schema + '.users SET display_name=$2 WHERE id=$1', [source.userId, originalName]);
    await fixture.close();
  }
});

test('a conflicting target is preserved and an interrupted import can resume without duplicates', async t => {
  t.mock.method(console, 'error', () => {});
  const fixture = await mongoFixture('resume');
  try {
    await migrate(fixture.store);
    const row = source.rows[0];
    await fixture.db.collection('stories').insertOne({
      _id: row.id, family: row.family, category: row.category, difficulty: row.difficulty, status: row.status,
      content: { ...row.content, legacyMetadata: { editorChanged: true } }, version: String(row.version),
      created_at: row.created_at, updated_at: row.updated_at,
    });
    await assert.rejects(importPostgres(fixture.store, source.pool, { schema: source.schema, onProgress: () => {} }), error => error.code === 'IMPORT_CONFLICT');
    assert.deepEqual((await fixture.db.collection('stories').findOne({ _id: row.id })).content.legacyMetadata, { editorChanged: true });
    await request(createApp(fixture.store)).get('/health').expect(503);
    // Explicitly repair only the deliberately conflicting disposable fixture.
    await fixture.db.collection('stories').updateOne({ _id: row.id }, { $set: {
      content: row.content, sentence_count: row.content.sentences.length,
      chapter_count: (await source.pool.query('SELECT count(*) FROM story_chapters WHERE story_id=$1', [row.id])).rows[0].count * 1,
      languages: Object.keys(row.content.title),
    } });
    const resumed = await importPostgres(fixture.store, source.pool, { schema: source.schema, onProgress: () => {} });
    assert.equal(resumed.status, 'verified');
    assert.equal(await fixture.db.collection('stories').countDocuments(), 20);
    assert.equal(await fixture.db.collection('users').countDocuments(), 2);
    await request(createApp(fixture.store)).get('/health').expect(200);
    await fixture.db.collection('story_vocabulary').deleteOne({});
    await assert.rejects(importPostgres(fixture.store, source.pool, { schema: source.schema, verifyOnly: true, onProgress: () => {} }), error => error.code === 'IMPORT_VERIFICATION_FAILED');
  } finally { await fixture.close(); }
});

test('relationship verification detects genuine orphaned MongoDB references', async () => {
  const fixture = await mongoFixture('relationships');
  try {
    await migrate(fixture.store);
    await fixture.db.collection('sessions').insertOne({ _id: 'orphan', user_id: 'missing-user', created_at: new Date(), expires_at: new Date() });
    await assert.rejects(verifyRelationships(fixture.db), error => error.code === 'IMPORT_VERIFICATION_FAILED');
  } finally { await fixture.close(); }
});

test('pre-chapter PostgreSQL sources derive ordered chapters without changing root content or dropping learning data', async () => {
  const legacy = await postgresFixture({ legacyOnly: true });
  const fixture = await mongoFixture('legacy');
  try {
    await migrate(fixture.store);
    const report = await importPostgres(fixture.store, legacy.pool, { schema: legacy.schema, onProgress: () => {} });
    assert.equal(report.sourceCounts.story_chapters, 0);
    assert.equal(report.derivedChapters, 20);
    assert.equal(report.targetCounts.story_chapters, 20);
    assert.equal(report.targetCounts.learning_records, 4);
    assert.equal(report.sourceCounts.dictionary, 0);
    const app = createApp(fixture.store);
    const id = legacy.stories[0].id;
    const chapter = await request(app).get('/api/v1/stories/' + id + '/chapters/main').expect(200);
    assert.deepEqual(chapter.body.sentences, legacy.rows.find(row => row.id === id).content.sentences);
    assert.equal(chapter.body.storyVersion, '1');
    assert.equal((await legacy.pool.query("SELECT to_regclass('story_chapters') AS name")).rows[0].name, null);
  } finally { await fixture.close(); await legacy.close(); }
});

test('legacy chapter positions and chapter-only exercises remain complete and paginate beyond position 100', async () => {
  const fixture = await mongoFixture('positions');
  const storyId = source.stories[0].id;
  const original = (await source.pool.query("SELECT content,vocabulary,version FROM story_chapters WHERE story_id=$1 AND id='opening'", [storyId])).rows[0];
  try {
    const { hash } = await import('../src/stories.js');
    const content = { ...original.content, exercises: [{ ...source.stories[0].exercises[0], id: 'chapter_only_import' }] };
    await source.pool.query("UPDATE story_chapters SET content=$2,version=$3 WHERE story_id=$1 AND id='opening'",
      [storyId, content, hash({ chapter: content, vocabulary: original.vocabulary })]);
    await source.pool.query('UPDATE story_chapters SET position=CASE position WHEN 1 THEN 103 ELSE 107 END WHERE story_id=$1', [storyId]);
    await migrate(fixture.store);
    const report = await importPostgres(fixture.store, source.pool, { schema: source.schema, onProgress: () => {} });
    assert.equal(report.exercises, 93);
    const app = createApp(fixture.store);
    const detail = (await request(app).get('/api/v1/stories/' + storyId + '/chapters/opening').expect(200)).body;
    assert.equal(detail.exercises[0].id, 'chapter_only_import');
    const first = (await request(app).get('/api/v1/stories/' + storyId + '/chapters?limit=1').expect(200)).body;
    assert.equal(first.chapters[0].order, 103);
    assert.equal(first.next, 103);
    const last = (await request(app).get('/api/v1/stories/' + storyId + '/chapters?after=103&limit=1').expect(200)).body;
    assert.equal(last.chapters[0].order, 107);
    assert.equal(last.next, null);
  } finally {
    await source.pool.query("UPDATE story_chapters SET content=$2,version=$3 WHERE story_id=$1 AND id='opening'",
      [storyId, original.content, original.version]);
    await source.pool.query("UPDATE story_chapters SET position=CASE id WHEN 'opening' THEN 1 ELSE 2 END WHERE story_id=$1", [storyId]);
    await fixture.close();
  }
});
