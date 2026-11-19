import { test } from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import request from 'supertest';
import { createApp } from '../src/app.js';
import { createDatabase, database, transaction, mongoOptions } from '../src/db.js';
import { mongoFixture } from './helpers.js';
import { collections, indexSpecs } from '../src/schema.js';

test('missing/invalid MongoDB configuration returns safe 503 responses while non-database routes work', async t => {
  const log = t.mock.method(console, 'error', () => {});
  for (const env of [{}, { MONGODB_URI: 'mongodb://secret-user:secret-password@host/?invalidOption=true', MONGODB_DB_NAME: 'rolang' }]) {
    const store = createDatabase(env);
    try {
      const app = createApp(store);
      for (const path of ['/health', '/api/v1/health', '/api/v1/stories']) {
        const result = await request(app).get(path).expect(503);
        assert.equal(result.body.error.code, 'DATABASE_UNAVAILABLE');
        assert.ok(!JSON.stringify(result.body).includes('secret'));
      }
      await request(app).get('/api/v1/me').expect(401);
      await request(app).get('/api/v1/stories?limit=-1').expect(400);
      await request(app).get('/unknown').expect(404);
      await request(app).get('/').expect(404);
    } finally { await store.close(); }
  }
  assert.ok(!JSON.stringify(log.mock.calls).includes('secret'));
});
test('simultaneous failed connections time out and a subsequent attempt can reconnect', async t => {
  t.mock.method(console, 'error', () => {});
  const env = { MONGODB_URI: 'mongodb://127.0.0.1:1', MONGODB_DB_NAME: 'rolang_test_recovery_' + randomUUID().replaceAll('-', '') };
  const store = createDatabase(env);
  const app = createApp(store);
  const started = Date.now();
  try {
    const responses = await Promise.all(Array.from({ length: 8 }, () => request(app).get('/health').expect(503)));
    assert.ok(Date.now() - started < 7000, 'Cold connection failure must fit Vercel request limits.');
    assert.ok(responses.every(result => result.body.database === 'unavailable'));
    env.MONGODB_URI = process.env.TEST_MONGODB_URI;
    assert.ok(env.MONGODB_URI, 'Set TEST_MONGODB_URI for real recovery verification.');
    await request(app).get('/health').expect(200);
  } finally {
    const db = await store.connect().catch(() => undefined);
    if (db) await db.dropDatabase();
    await store.close();
  }
});
test('one shared manager/client serves concurrent warm requests and keeps the explicit database name', async () => {
  const fixture = await mongoFixture('reuse');
  try {
    await fixture.store.scope();
    const connections = await Promise.all(Array.from({ length: 12 }, () => fixture.store.connect()));
    assert.ok(connections.every(db => db === fixture.db));
    assert.equal(fixture.db.databaseName, fixture.name);
    assert.equal(database(), database());
    const app = createApp(fixture.store);
    await Promise.all(Array.from({ length: 12 }, () => request(app).get('/api/v1/stories').expect(200)));
  } finally { await fixture.close(); await database().close(); }
});
test('health automatically initializes and repairs MongoDB while preserving existing documents', async () => {
  const fixture = await mongoFixture('schema');
  const check = () => request(createApp(fixture.store)).get('/health');
  try {
    const pending = await check().expect(200);
    assert.equal(pending.body.database, 'connected');
    await check().expect(200);
    for (const name of Object.keys(collections)) {
      assert.ok(await fixture.db.listCollections({ name }).hasNext());
    }
    for (const [name, indexes] of Object.entries(indexSpecs))
      assert.ok((await fixture.db.collection(name).listIndexes().toArray()).length >= indexes.length + 1);
    const story = { _id: 'retained_story', family: 'reader', category: 'Reading', difficulty: 'A1', status: 'published',
      content: { sentences: [{ en: 'Read.', id: 'Baca.', tl: 'Basahin.' }], exercises: [{ id: 'existing_exercise' }] },
      version: '9007199254740993', created_at: new Date(), updated_at: new Date(), extra_content: { keep: true } };
    await fixture.db.collection('stories').insertOne(story);
    // Stale administration markers are unrelated to runtime readiness.
    await fixture.db.collection('schema_migrations').insertOne({ _id: 'obsolete_release' });
    await fixture.db.collection('database_imports').insertOne({ _id: 'obsolete_source', state: 'failed' });
    await fixture.db.collection('users').dropIndex('users_email');
    await check().expect(200);
    await fixture.db.command({ collMod: 'stories', validator: {}, validationLevel: 'off' });
    await check().expect(200);
    // The schema can remain correct while enforcement is disabled. Re-running
    // initialization must repair those modes too, before health becomes ready.
    await fixture.db.command({ collMod: 'stories', validationLevel: 'off', validationAction: 'warn' });
    await check().expect(200);
    assert.deepEqual(await fixture.db.collection('stories').findOne({ _id: story._id }), story);
    assert.equal(await fixture.db.collection('database_imports').countDocuments(), 1);
  } finally { await fixture.close(); }
});
test('separate cold instances initialize through API requests without an administration command', async () => {
  const fixture = await mongoFixture('cold');
  const stores = Array.from({ length: 4 }, () => createDatabase(fixture.env));
  try {
    const responses = await Promise.all(stores.flatMap(store => Array.from({ length: 3 }, () =>
      request(createApp(store)).get('/api/v1/stories').expect(200))));
    assert.ok(responses.every(response => response.body.stories.length === 0 && response.body.next === null));
    assert.deepEqual((await fixture.db.listCollections().toArray()).map(item => item.name).sort(), Object.keys(collections).sort());
  } finally {
    await Promise.all(stores.map(store => store.close()));
    await fixture.close();
  }
});
test('incompatible indexes and duplicate data fail readiness rather than deleting or accepting content', async t => {
  t.mock.method(console, 'error', () => {});
  const fixture = await mongoFixture('conflict');
  const app = createApp(fixture.store);
  try {
    await request(app).get('/health').expect(200);
    await fixture.db.collection('users').dropIndex('users_email');
    await fixture.db.collection('users').createIndex({ email: 1 }, { name: 'users_email' });
    const conflict = await request(app).get('/health').expect(503);
    assert.equal(conflict.body.database, 'connected');
    assert.equal(conflict.body.error.code, 'DATABASE_NOT_READY');
    assert.match(conflict.body.error.message, /index.*incompatible/);
    await request(app).get('/api/v1/stories').expect(503);
    await fixture.db.collection('users').dropIndex('users_email');
    const users = ['one', 'two'].map(_id => ({ _id, email: 'same@example.test', password_hash: 'existing_hash',
      display_name: _id, role: 'learner', created_at: new Date() }));
    await fixture.db.collection('users').insertMany(users);
    const duplicate = await request(app).get('/health').expect(503);
    assert.equal(duplicate.body.error.code, 'DATABASE_NOT_READY');
    assert.match(duplicate.body.error.message, /duplicate records/);
    await request(app).get('/api/v1/stories').expect(503);
    assert.deepEqual(await fixture.db.collection('users').find({}).sort({ _id: 1 }).toArray(), users);
    // Correct the test fixture's conflict, then confirm the same manager retries.
    await fixture.db.collection('users').updateOne({ _id: 'two' }, { $set: { email: 'different@example.test' } });
    await request(app).get('/health').expect(200);
    await request(app).get('/api/v1/stories').expect(200);
  } finally { await fixture.close(); }
});
test('real MongoDB permission errors prevent readiness and a later request can retry initialization',
  { skip: process.env.TEST_MONGODB_FAILPOINTS !== '1' }, async t => {
    t.mock.method(console, 'error', () => {});
    const fixture = await mongoFixture('permissions');
    try {
      await fixture.db.admin().command({ configureFailPoint: 'failCommand', mode: { times: 1 },
        data: { failCommands: ['createIndexes'], errorCode: 13 } });
      const app = createApp(fixture.store);
      const failed = await request(app).get('/health').expect(503);
      assert.equal(failed.body.database, 'connected');
      assert.equal(failed.body.error.code, 'DATABASE_NOT_READY');
      assert.match(failed.body.error.message, /permissions/);
      await request(app).get('/api/v1/stories').expect(200);
      await request(app).get('/health').expect(200);
    } finally {
      await fixture.db.admin().command({ configureFailPoint: 'failCommand', mode: 'off' });
      await fixture.close();
    }
  });
test('transactions abort real writes and enforce a serverless deadline', { skip: process.env.TEST_MONGODB_FAILPOINTS !== '1' }, async () => {
  const fixture = await mongoFixture('deadline');
  let timedSessionId;
  try {
    await fixture.store.scope();
    await assert.rejects(transaction(fixture.store, async scope => {
      await scope.db.collection('counters').insertOne({ _id: 'rollback_fixture', value: 1 }, mongoOptions(scope));
      throw new Error('Abort fixture transaction.');
    }), /Abort fixture/);
    assert.equal(await fixture.db.collection('counters').findOne({ _id: 'rollback_fixture' }), null);
    await fixture.db.admin().command({ configureFailPoint: 'failCommand', mode: { times: 1 },
      data: { failCommands: ['find'], blockConnection: true, blockTimeMS: 1500 } });
    const start = Date.now();
    await assert.rejects(transaction(fixture.store, async scope => {
      timedSessionId = scope.session.id;
      await scope.db.collection('stories').findOne({}, mongoOptions(scope));
    }, { timeoutMS: 100 }), error => error.name === 'MongoOperationTimeoutError');
    assert.ok(Date.now() - start < 1200, 'The configured transaction timeout must take effect.');
  } finally {
    await fixture.db.admin().command({ configureFailPoint: 'failCommand', mode: 'off' });
    // The deliberate server-side socket stall can outlive the client deadline.
    // Kill only this disposable session before dropping its test database.
    if (timedSessionId) await fixture.db.admin().command({ killSessions: [timedSessionId] });
    await fixture.close();
  }
});
test('the real driver recovers from a socket disconnect without replacing the shared manager', { skip: process.env.TEST_MONGODB_FAILPOINTS !== '1' }, async () => {
  const fixture = await mongoFixture('socket');
  try {
    await fixture.store.scope();
    const app = createApp(fixture.store);
    await request(app).get('/api/v1/stories').expect(200);
    await fixture.db.admin().command({ configureFailPoint: 'failCommand', mode: { times: 1 },
      data: { failCommands: ['find'], closeConnection: true } });
    await request(app).get('/api/v1/stories').expect(200);
    await request(app).get('/health').expect(200);
  } finally {
    await fixture.db.admin().command({ configureFailPoint: 'failCommand', mode: 'off' });
    await fixture.close();
  }
});

test('real transaction conflicts replay aborted work and uncertain commits preserve one callback execution', { skip: process.env.TEST_MONGODB_FAILPOINTS !== '1' }, async () => {
  const fixture = await mongoFixture('retries');
  try {
    await fixture.store.scope();
    await fixture.db.admin().command({ configureFailPoint: 'failCommand', mode: { times: 1 },
      data: { failCommands: ['insert'], errorCode: 112, errorLabels: ['TransientTransactionError'] } });
    let attempts = 0;
    await transaction(fixture.store, async scope => {
      attempts++;
      await scope.db.collection('counters').insertOne({ _id: 'transient_retry', value: 1 }, mongoOptions(scope));
    });
    assert.equal(attempts, 2);
    assert.equal(await fixture.db.collection('counters').countDocuments({ _id: 'transient_retry' }), 1);
    // More failures than the driver's first commit retry exercise our outer
    // uncertain-commit retry without running the business operation again.
    await fixture.db.admin().command({ configureFailPoint: 'failCommand', mode: { times: 3 },
      data: { failCommands: ['commitTransaction'], errorCode: 91 } });
    let callbacks = 0;
    await transaction(fixture.store, async scope => {
      callbacks++;
      await scope.db.collection('counters').insertOne({ _id: 'commit_retry', value: 1 }, mongoOptions(scope));
    });
    assert.equal(callbacks, 1);
    assert.equal(await fixture.db.collection('counters').countDocuments({ _id: 'commit_retry' }), 1);
  } finally {
    await fixture.db.admin().command({ configureFailPoint: 'failCommand', mode: 'off' });
    await fixture.close();
  }
});
