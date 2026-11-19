import { before, after, test } from 'node:test';
import assert from 'node:assert/strict';
import pg from 'pg';
import { randomUUID } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import request from 'supertest';
import { database } from '../src/db.js';
import { migrate } from '../scripts/migrate.js';
import { readCorpus, prepareCorpus, importCorpus, verifyCorpus } from '../scripts/import-corpus.js';
import { createApp } from '../src/app.js';
import { once } from 'node:events';
import { transaction } from '../src/db.js';

const base = database();
const schema = `content_${randomUUID().replaceAll('-','')}`;
let pool, app, corpus, token;
before(async () => {
  await base.query(`CREATE SCHEMA ${schema}`);
  pool = new pg.Pool({ connectionString:process.env.DATABASE_URL, options:`-c search_path=${schema}`, allowExitOnIdle:true });
  await migrate(pool);
  corpus = await readCorpus();
  await importCorpus(pool,corpus);
  app = createApp(pool);
  const account = await request(app).post('/api/v1/auth/register').send({email:`${schema}@example.test`,password:'test-fixture-password',displayName:'Content test'}).expect(201);
  token = account.body.token;
  await pool.query("UPDATE users SET role='admin' WHERE id=$1",[account.body.user.id]);
});
after(async () => { await pool?.end(); await base.query(`DROP SCHEMA ${schema} CASCADE`); await base.end(); });

test('full legacy corpus import is exact, ordered, atomic, and idempotent',async () => {
  const first = await pool.query('SELECT id,version,updated_at FROM stories ORDER BY id');
  await importCorpus(pool,corpus);
  assert.deepEqual((await pool.query('SELECT id,version,updated_at FROM stories ORDER BY id')).rows,first.rows);
  const report = await verifyCorpus(pool,corpus);
  assert.deepEqual([report.stories,report.chapters,report.vocabulary,report.exercises],[20,20,1204,92]);
  const changed = structuredClone(corpus);
  changed.stories.at(-1).title.en += ' edited';
  await assert.rejects(importCorpus(pool,changed),/Conflicting story/);
  await verifyCorpus(pool,corpus);
  assert.equal((await pool.query('SELECT count(*) FROM corpus_imports')).rows[0].count,'1');
});

test('paginated catalogs and every migrated detail/chapter preserve all learning content',async () => {
  const seen = [];
  let after;
  do {
    const page = await request(app).get('/api/v1/stories').query({limit:3,...(after ? {after} : {})}).expect(200);
    seen.push(...page.body.stories);
    assert.ok(page.body.stories.every(s => !s.sentences && !s.vocabulary && !s.exercises && s.version && s.chapterCount === 1));
    after = page.body.next;
  } while (after);
  assert.equal(new Set(seen.map(s => s.id)).size,20);
  const {stories} = prepareCorpus(corpus);
  for (const story of stories) {
    const detail = (await request(app).get(`/api/v1/stories/${story.id}`).expect(200)).body;
    for (const key of ['title','summary','sentences','speakers','notes','objectives','focus','pronunciation','exercises','vocabulary']) assert.deepEqual(detail[key],story[key]);
    const manifest = (await request(app).get(`/api/v1/stories/${story.id}?view=manifest`).expect(200)).body;
    assert.ok(!manifest.sentences);
    assert.deepEqual(manifest.speakers,story.speakers);
    const chapters = (await request(app).get(`/api/v1/stories/${story.id}/chapters?limit=1`).expect(200)).body;
    assert.equal(chapters.chapters[0].order,1);
    const chapter = (await request(app).get(`/api/v1/stories/${story.id}/chapters/main`).expect(200)).body;
    assert.deepEqual(chapter.sentences,story.sentences);
    assert.deepEqual(chapter.exercises,story.exercises);
    assert.equal(chapter.storyVersion,detail.version);
    await request(app).get(`/api/v1/stories/${story.id}`).set('If-None-Match',`"${detail.version}"`).expect(304);
    await request(app).get(`/api/v1/stories/${story.id}/chapters/main`).set('If-None-Match',`"${chapter.version}"`).expect(304);
  }
});

test('ordered multiple chapters have independent versions and validated content',async () => {
  const original = prepareCorpus(corpus).stories[0];
  const story = { ...original,id:'chapter_test',chapters:[
    {id:'first',title:structuredClone(original.title),sentences:original.sentences.slice(0,2)},
    {id:'second',title:structuredClone(original.title),sentences:original.sentences.slice(2)},
  ] };
  await request(app).post('/api/v1/stories').set('Authorization',`Bearer ${token}`).send(story).expect(201);
  await request(app).post('/api/v1/stories/chapter_test/publish').set('Authorization',`Bearer ${token}`).send({published:true}).expect(200);
  const first = (await request(app).get('/api/v1/stories/chapter_test/chapters?limit=1').expect(200)).body;
  assert.equal(first.next,1);
  const second = (await request(app).get('/api/v1/stories/chapter_test/chapters?after=1&limit=1').expect(200)).body;
  assert.equal(second.chapters[0].id,'second');
  const version = first.version;
  const chapterVersion = second.chapters[0].version;
  story.chapters[0].title.en += ' updated';
  await request(app).put('/api/v1/stories/chapter_test').set('Authorization',`Bearer ${token}`).send(story).expect(200);
  const latest = (await request(app).get('/api/v1/stories/chapter_test/content').expect(200)).body;
  assert.notEqual(latest.version,version);
  assert.equal(latest.chapters[1].version,chapterVersion);
  assert.deepEqual(latest.chapters.flatMap(c => c.sentences),story.sentences);
  await request(app).get('/api/v1/stories/chapter_test/chapters/nope').expect(404);
  await request(app).get('/api/v1/stories/chapter_test/chapters?after=-1').expect(400);
  await request(app).put('/api/v1/stories/chapter_test').set('Authorization',`Bearer ${token}`).send({...story,chapters:[story.chapters[0],story.chapters[0]]}).expect(400);
  await request(app).put('/api/v1/stories/chapter_test').set('Authorization',`Bearer ${token}`).send({...story,vocabulary:[]}).expect(400);
});

test('health rejects unapplied migrations and schema drift, then recovers after migration', async t => {
  t.mock.method(console, 'error', () => {});
  const fixtureSchema = `health_${randomUUID().replaceAll('-', '')}`;
  await base.query(`CREATE SCHEMA ${fixtureSchema}`);
  const fixture = new pg.Pool({ connectionString: process.env.DATABASE_URL,
    options: `-c search_path=${fixtureSchema}`, allowExitOnIdle: true });
  const check = () => request(createApp(fixture)).get('/health');
  try {
    let response = await check().expect(503);
    assert.equal(response.body.database, 'connected');
    assert.equal(response.body.error.code, 'DATABASE_NOT_READY');
    await transaction(fixture, async client => {
      await client.query(await readFile(new URL('../migrations/001_initial.sql', import.meta.url), 'utf8'));
      await client.query('CREATE TABLE schema_migrations(name TEXT PRIMARY KEY)');
      await client.query("INSERT INTO schema_migrations(name) VALUES ('001_initial.sql')");
    });
    await check().expect(503);
    await migrate(fixture);
    await check().expect(200);
    // A valid migration ledger must not conceal a missing runtime column.
    await fixture.query('ALTER TABLE stories RENAME COLUMN version TO fixture_version');
    response = await check().expect(503);
    assert.equal(response.body.error.code, 'DATABASE_NOT_READY');
    await fixture.query('ALTER TABLE stories RENAME COLUMN fixture_version TO version');
    await check().expect(200);
  } finally {
    await fixture.end();
    await base.query(`DROP SCHEMA ${fixtureSchema} CASCADE`);
  }
});

test('the application pool survives an actual idle PostgreSQL disconnect and reconnects', async () => {
  const client = await base.connect();
  const { rows } = await client.query('SELECT pg_backend_pid() AS pid');
  client.release();
  // allowExitOnIdle unrefs idle sockets; retain this one while observing its
  // asynchronous failure so the test runner cannot exit before the event.
  client.ref();
  const disconnected = once(base, 'error');
  await pool.query('SELECT pg_terminate_backend($1)', [rows[0].pid]);
  await disconnected;
  assert.equal((await base.query('SELECT 1 AS value')).rows[0].value, 1);
});
