import { before, after, test } from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import request from 'supertest';
import { createApp } from '../src/app.js';
import { seed } from '../scripts/seed.js';
import { mongoFixture } from './helpers.js';

let fixture, store, db, app, learner, other, admin;
const run = randomUUID();
const testStoryId = 'test_' + run.replaceAll('-', '');
before(async () => {
  fixture = await mongoFixture('api');
  ({ store, db } = fixture);
  await seed(store); await seed(store);
  app = createApp(store);
  for (const role of ['learner', 'other', 'admin']) {
    const email = role + '.' + run + '@example.test';
    const response = await request(app).post('/api/v1/auth/register').send({
      email, password: 'test-fixture-password', displayName: role,
    }).expect(201);
    if (role === 'learner') learner = response.body;
    if (role === 'other') other = response.body;
    if (role === 'admin') admin = response.body;
  }
  await db.collection('users').updateOne({ _id: admin.user.id }, { $set: { role: 'admin' } });
});
after(async () => { await fixture?.close(); });
const bearer = account => `Bearer ${account.token}`;
const progress = { storyId: 'market_beginner', language: 'en', sentence: 1, completed: false };
const operation = (data = progress) => ({ id: randomUUID(), kind: 'progress', key: 'market_beginner:en', data, deleted: false });

test('complete seed is repeatable without duplicate curriculum records', async () => {
  assert.equal(await db.collection('stories').countDocuments({ difficulty: 'A1', status: 'published' }), 21);
  assert.equal(await db.collection('story_chapters').countDocuments(), 30);
  assert.equal(await db.collection('corpus_imports').countDocuments(), 1);
});

test('catalog, filters, complete detail, translation, and vocabulary use the Android corpus contract', async () => {
  await request(app).get('/api/v1/health').expect(200);
  const response = await request(app).get('/api/v1/stories?language=tl&difficulty=A1&category=Kehidupan%20sehari-hari&limit=1').expect(200);
  assert.equal(response.body.stories.length, 1);
  assert.equal(response.body.stories[0].level, 'BEGINNER');
  const id = response.body.stories[0].id;
  const detail = await request(app).get(`/api/v1/stories/${id}`).expect(200);
  assert.ok(detail.body.vocabulary.length);
  assert.ok(detail.body.sentences[0].tl);
  const translations = await request(app).get(`/api/v1/stories/${id}/translations?language=id`).expect(200);
  assert.equal(translations.body.sentences[0], detail.body.sentences[0].id);
  const vocabulary = await request(app).get(`/api/v1/stories/${id}/vocabulary?language=en`).expect(200);
  assert.ok(vocabulary.body.vocabulary.every(word => word.language === 'en'));
  const page = await request(app).get('/api/v1/stories?limit=2').expect(200);
  const second = await request(app).get(`/api/v1/stories?limit=2&after=${page.body.next}`).expect(200);
  assert.ok(second.body.stories.every(s => s.id > page.body.next));
});

test('authentication validates requests, isolates roles, revokes sessions, and rejects privilege escalation', async () => {
  await request(app).get('/api/v1/me').expect(401);
  await request(app).post('/api/v1/auth/register').send({ email: 'bad', password: 'short', role: 'admin' }).expect(400);
  await request(app).post('/api/v1/auth/register').send({ email: learner.user.email,
    password: 'test-fixture-password', displayName: 'Duplicate' }).expect(409);
  await request(app).post('/api/v1/auth/login').send({ email: learner.user.email, password: 'wrong-password-value' }).expect(401);
  const login = await request(app).post('/api/v1/auth/login').send({ email: learner.user.email.toUpperCase(),
    password: 'test-fixture-password' }).expect(200);
  await request(app).get('/api/v1/me').set('Authorization', `Bearer ${login.body.token}`).expect(200);
  const edited = await request(app).put('/api/v1/me').set('Authorization', `Bearer ${login.body.token}`)
    .send({ displayName: 'Updated learner' }).expect(200);
  assert.equal(edited.body.displayName, 'Updated learner');
  await request(app).post('/api/v1/auth/logout').set('Authorization', `Bearer ${login.body.token}`).expect(204);
  await request(app).get('/api/v1/me').set('Authorization', `Bearer ${login.body.token}`).expect(401);
  assert.ok(!('password_hash' in login.body.user));
  await request(app).get('/api/v1/admin/stories').set('Authorization', bearer(learner)).expect(403);
  await db.collection('sessions').updateMany({ user_id: other.user.id }, { $set: { expires_at: new Date(Date.now() - 1000) } });
  await request(app).get('/api/v1/me').set('Authorization', bearer(other)).expect(401);
  other = (await request(app).post('/api/v1/auth/login').send({ email: other.user.email,
    password: 'test-fixture-password' }).expect(200)).body;
});

test('administrators create, edit, publish, unpublish, and delete fully translated stories', async () => {
  const sample = JSON.parse(await readFile(new URL('../docs/examples/story.json', import.meta.url), 'utf8'));
  const story = { ...sample, id: testStoryId };
  await request(app).post('/api/v1/stories').set('Authorization', bearer(learner)).send(story).expect(403);
  await request(app).post('/api/v1/stories').set('Authorization', bearer(admin)).send({ ...story, vocabulary: [] }).expect(400);
  await request(app).post('/api/v1/stories').set('Authorization', bearer(admin)).send(story).expect(201);
  const drafts = await request(app).get('/api/v1/admin/stories?limit=100').set('Authorization', bearer(admin)).expect(200);
  assert.ok(drafts.body.stories.some(s => s.id === testStoryId && s.status === 'draft'));
  await request(app).get(`/api/v1/stories/${testStoryId}`).expect(404);
  await request(app).put(`/api/v1/stories/${testStoryId}`).set('Authorization', bearer(admin)).send({ ...story, difficulty: 'A2' }).expect(200);
  await request(app).post(`/api/v1/stories/${testStoryId}/publish`).set('Authorization', bearer(admin)).send({ published: true }).expect(200);
  const published = await request(app).get(`/api/v1/stories/${testStoryId}`).expect(200);
  assert.equal(published.body.difficulty, 'A2');
  await request(app).post(`/api/v1/stories/${testStoryId}/publish`).set('Authorization', bearer(admin)).send({ published: false }).expect(200);
  await request(app).get(`/api/v1/stories/${testStoryId}`).expect(404);
  await request(app).delete(`/api/v1/stories/${testStoryId}`).set('Authorization', bearer(admin)).expect(204);
});

test('sync retries are idempotent, concurrent device writes have ordered revisions, and users are isolated', async () => {
  const first = operation();
  const post = input => request(app).post('/api/v1/me/sync').set('Authorization', bearer(learner)).send(input);
  const initial = await post({ cursor: 0, operations: [first] }).expect(200);
  assert.deepEqual(initial.body.acknowledged, [first.id]);
  const retry = await post({ cursor: 0, operations: [first] }).expect(200);
  assert.equal(retry.body.cursor, initial.body.cursor);
  await post({ cursor: 0, operations: [operation({ ...progress, completed: true })] }).expect(200);
  const reread = await post({ cursor: 0, operations: [operation()] }).expect(200);
  assert.equal(reread.body.records[0].data.completed, true);
  await post({ cursor: 0, operations: [{ ...first, data: { ...progress, sentence: 2 } }] }).expect(409);
  const otherData = await request(app).post('/api/v1/me/sync').set('Authorization', bearer(other)).send({ cursor: 0, operations: [] }).expect(200);
  assert.equal(otherData.body.records.length, 0);
  await Promise.all([post({ cursor: initial.body.cursor, operations: [operation({ ...progress, sentence: 2 })] }).expect(200),
    post({ cursor: initial.body.cursor, operations: [operation({ ...progress, completed: true })] }).expect(200)]);
  const latest = await post({ cursor: initial.body.cursor, operations: [] }).expect(200);
  assert.ok(latest.body.cursor > initial.body.cursor);
  assert.equal(latest.body.records.length, 1);
  const staleRetry = await post({ cursor: 0, operations: [first] }).expect(200);
  assert.equal(staleRetry.body.cursor, latest.body.cursor);
  assert.deepEqual(staleRetry.body.records[0].data, latest.body.records[0].data);
  await post({ cursor: latest.body.cursor, operations: [{ id: randomUUID(), kind: 'progress',
    key: first.key, data: null, deleted: true }] }).expect(200);
  const tombstone = await post({ cursor: latest.body.cursor, operations: [] }).expect(200);
  assert.equal(tombstone.body.records[0].deleted, true);
  await post({ cursor: tombstone.body.cursor + 1, operations: [] }).expect(409);
  await post({ cursor: 0, operations: [{ ...operation(), key: 'wrong' }] }).expect(400);
  await post({ cursor: 0, operations: [{ id: randomUUID(), kind: 'vocabulary', key: 'invalid', deleted: true, data: null }] }).expect(400);
});

test('sync download pagination delivers every record and advances cursors without duplicating events', async () => {
  const operations = Array.from({ length: 512 }, (_, i) => ({ id: randomUUID(), kind: 'review', key: randomUUID(),
    deleted: false, data: { vocabularyKey: 'en:id:market_beginner:maya', language: 'en', reference: 'id',
      reviewedAt: 1000 + i, correct: true, rating: 'GOOD' } }));
  for (let i = 0; i < operations.length; i += 100) {
    await request(app).post('/api/v1/me/sync').set('Authorization', bearer(other))
      .send({ cursor: 0, operations: operations.slice(i, i + 100) }).expect(200);
  }
  const first = await request(app).post('/api/v1/me/sync').set('Authorization', bearer(other))
    .send({ cursor: 0, operations: [] }).expect(200);
  assert.equal(first.body.records.length, 500);
  assert.equal(first.body.hasMore, true);
  const second = await request(app).post('/api/v1/me/sync').set('Authorization', bearer(other))
    .send({ cursor: first.body.cursor, operations: [] }).expect(200);
  assert.equal(second.body.records.length, 12);
  assert.equal(second.body.hasMore, false);
  assert.equal(new Set([...first.body.records, ...second.body.records].map(r => r.key)).size, 512);
});

test('authentication rate limits persist across separate application instances', async () => {
  const freshApp = createApp(store);
  const email = `limited.${run}@example.test`;
  for (let i = 0; i < 20; i++) {
    await request(i % 2 ? freshApp : app).post('/api/v1/auth/login').send({ email, password: 'test-fixture-password' }).expect(401);
  }
  await request(freshApp).post('/api/v1/auth/login').send({ email, password: 'test-fixture-password' }).expect(429);
});

test('learning REST endpoints persist preferences, progress/history, vocabulary and review schedules', async () => {
  const sample = { language: 'en', reference: 'id', word: 'maya', translation: 'Maya', meaning: 'Name',
    partOfSpeech: 'proper noun', explanation: 'Name', example: 'Maya walks.', exampleTranslation: 'Maya berjalan.',
    storyId: 'market_beginner', storyTitle: 'Market', category: 'Everyday life', createdAt: 1000, dueAt: 2000,
    repetitions: 1, intervalDays: 1, ease: 2.5, lapses: 0, mastered: false, lastReviewedAt: 1000 };
  const key = 'en:id:market_beginner:maya';
  const base = '/api/v1/me';
  await request(app).put(`${base}/vocabulary/${encodeURIComponent(key)}`).set('Authorization', bearer(learner)).send(sample).expect(200);
  const words = await request(app).get(`${base}/vocabulary`).set('Authorization', bearer(learner)).expect(200);
  assert.equal(words.body.records[0].data.dueAt, 2000);
  await request(app).put(`${base}/progress/market_beginner:en`).set('Authorization', bearer(learner)).send(progress).expect(200);
  const history = await request(app).get(`${base}/history`).set('Authorization', bearer(learner)).expect(200);
  assert.ok(history.body.records.some(r => r.key === 'market_beginner:en'));
  await request(app).put(`${base}/preferences/preferences`).set('Authorization', bearer(learner)).send({
    target: 'tl', native: 'en', level: 'ADVANCED', fontSize: 24, dark: true }).expect(200);
  await request(app).put(`${base}/reviews/${randomUUID()}`).set('Authorization', bearer(learner)).send({
    vocabularyKey: key, language: 'en', reference: 'id', reviewedAt: 1000, correct: true, rating: 'GOOD' }).expect(200);
  await request(app).get(`${base}/reviews`).set('Authorization', bearer(learner)).expect(200);
  for (const path of ['progress', 'preferences', 'reviews']) {
    const result = await request(app).get(`${base}/${path}`).set('Authorization', bearer(learner)).expect(200);
    assert.ok(result.body.records.length);
    for (const item of result.body.records)
      await request(app).delete(`${base}/${path}/${encodeURIComponent(item.key)}`).set('Authorization', bearer(learner)).expect(204);
  }
  await request(app).delete(`${base}/vocabulary/${encodeURIComponent(key)}`).set('Authorization', bearer(learner)).expect(204);
  assert.equal((await request(app).get(`${base}/vocabulary`).set('Authorization', bearer(learner)).expect(200)).body.records.length, 0);
});

test('invalid filters, malformed JSON, large bodies, and unavailable databases return safe errors', async () => {
  await request(app).get('/api/v1/stories?difficulty=A9').expect(400);
  await request(app).get('/api/v1/stories?limit=-1').expect(400);
  await request(app).post('/api/v1/auth/login').set('Content-Type', 'application/json').send('{').expect(400);
  await request(app).post('/api/v1/auth/login').send({ oversized: 'x'.repeat(2_100_000) }).expect(413);
  await request(app).get('/api/v1/unknown').expect(404);
});

test('all vocabulary statuses synchronize with manual metadata, idempotency, and legacy compatibility', async () => {
  const key = 'en:id:market_beginner:market';
  const sample = { language: 'en', reference: 'id', word: 'market', translation: 'pasar', meaning: 'A place to buy food',
    partOfSpeech: 'noun', explanation: 'A morning market', example: 'Maya walks to the market.',
    exampleTranslation: 'Maya berjalan ke pasar.', storyId: 'market_beginner', storyTitle: 'Market', category: 'Everyday life',
    createdAt: 1000, dueAt: 2000, repetitions: 0, intervalDays: 0, ease: 2.5, lapses: 0,
    mastered: false, lastReviewedAt: 0 };
  const post = input => request(app).post('/api/v1/me/sync').set('Authorization', bearer(learner)).send(input);
  let previous;
  for (const [index, status] of ['NEW', 'LEARNING', 'ALMOST_MASTERED', 'KNOWN'].entries()) {
    const op = { id: randomUUID(), kind: 'vocabulary', key, deleted: false,
      data: { ...sample, status, mastered: status === 'KNOWN', statusChangedAt: 3000 + index } };
    const synced = await post({ cursor: 0, operations: [op] }).expect(200);
    const word = synced.body.records.find(r => r.key === key).data;
    assert.equal(word.status, status);
    assert.equal(word.statusChangedAt, 3000 + index);
    if (previous) {
      const stale = await post({ cursor: 0, operations: [previous] }).expect(200);
      assert.equal(stale.body.records.find(r => r.key === key).data.status, status);
    }
    previous = op;
  }
  const endpoint = `/api/v1/me/vocabulary/${encodeURIComponent(key)}`;
  await request(app).put(endpoint).set('Authorization', bearer(learner))
    .send({ ...sample, status: 'KNOWN', mastered: false }).expect(400);
  await post({ cursor: 0, operations: [{ ...previous, id: randomUUID(), data: { ...previous.data, status: 'INVALID' } }] }).expect(400);
  await request(app).put(endpoint).set('Authorization', bearer(learner))
    .send({ ...sample, repetitions: 3 }).expect(200);
  const legacy = await request(app).get('/api/v1/me/vocabulary').set('Authorization', bearer(learner)).expect(200);
  assert.equal(legacy.body.records.find(r => r.key === key).data.status, 'ALMOST_MASTERED');
  assert.equal(legacy.body.records.find(r => r.key === key).data.statusChangedAt, 0);
  // Pre-upgrade database rows acquire the same defaults without a destructive migration.
  await db.collection('learning_records').updateOne({ user_id: learner.user.id, kind: 'vocabulary', key },
    { $unset: { 'data.status': '', 'data.statusChangedAt': '' } });
  const existing = await post({ cursor: 0, operations: [] }).expect(200);
  assert.equal(existing.body.records.find(r => r.key === key).data.status, 'ALMOST_MASTERED');
});

test('indexed catalog search accepts multilingual terms alongside filtering and pagination', async () => {
  const sample = JSON.parse(await readFile(new URL('../data/corpus.json', import.meta.url), 'utf8')).stories[0];
  const result = await request(app).get('/api/v1/stories').query({ search: sample.title.en, limit: 1 }).expect(200);
  assert.ok(result.body.stories.length);
  const localized = await request(app).get('/api/v1/stories').query({ q: sample.title.tl, language: 'tl', difficulty: sample.difficulty }).expect(200);
  assert.ok(localized.body.stories.some(story => story.id === sample.id));
  await request(app).get('/api/v1/stories?search=' + 'x'.repeat(201)).expect(400);
  assert.equal((await request(app).get('/api/v1/stories?search=nonexistentwordqzx').expect(200)).body.stories.length, 0);
});
test('learning list pagination returns all keys once', async () => {
  const first = await request(app).get('/api/v1/me/reviews?limit=7').set('Authorization', bearer(other)).expect(200);
  assert.equal(first.body.records.length, 7);
  assert.ok(first.body.next);
  const second = await request(app).get('/api/v1/me/reviews').query({ limit: 7, after: first.body.next })
    .set('Authorization', bearer(other)).expect(200);
  assert.ok(second.body.records.every(record => record.key > first.body.next));
  assert.equal(new Set([...first.body.records, ...second.body.records].map(record => record.key)).size, 14);
});
