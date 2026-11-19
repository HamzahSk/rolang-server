import { test } from 'node:test';
import assert from 'node:assert/strict';
import request from 'supertest';
import { createApp } from '../src/app.js';
import { database, transaction } from '../src/db.js';
import { failureInfo, reportError } from '../src/errors.js';
import { requiredMigrations } from '../src/health.js';

test('both health paths check connectivity and readiness without exposing database details', async t => {
  const queries = [];
  const app = createApp({ query: async sql => {
    queries.push(sql);
    return { rows: sql.includes('schema_migrations') ? requiredMigrations.map(name => ({ name })) : [{ ready: true }] };
  } });
  for (const path of ['/health', '/api/v1/health']) {
    const result = await request(app).get(path).expect(200);
    assert.deepEqual(result.body, { status: 'ok', apiVersion: 'v1', database: 'connected' });
    assert.equal(result.headers['cache-control'], 'no-store');
  }
  assert.ok(queries.some(sql => sql.includes('story_chapters')));
  assert.ok(queries.some(sql => sql.includes('has_sequence_privilege')));
  t.mock.method(console, 'error', () => {});
  const offline = createApp({ query: async () => { throw Object.assign(new Error('postgres://private'), { code: 'ECONNREFUSED' }); } });
  const result = await request(offline).get('/health').expect(503);
  assert.equal(result.body.database, 'unavailable');
  assert.equal(result.body.error.code, 'DATABASE_UNAVAILABLE');
  assert.ok(!JSON.stringify(result.body).includes('private'));
  const pending = createApp({ query: async () => ({ rows: [] }) });
  const notReady = await request(pending).get('/health').expect(503);
  assert.equal(notReady.body.database, 'connected');
  assert.equal(notReady.body.error.code, 'DATABASE_NOT_READY');
  const denied = createApp({ query: async sql => ({ rows: sql.includes('schema_migrations')
    ? requiredMigrations.map(name => ({ name })) : [{ ready: false }] }) });
  assert.equal((await request(denied).get('/health').expect(503)).body.error.code, 'DATABASE_NOT_READY');
});

test('database outages, missing migrations and programming errors return distinct non-success statuses', async t => {
  t.mock.method(console, 'error', () => {});
  for (const [error, status, code] of [
    [Object.assign(new Error('private'), { code: '28P01' }), 503, 'DATABASE_UNAVAILABLE'],
    [Object.assign(new Error('private'), { code: '42P01' }), 503, 'DATABASE_NOT_READY'],
    [new Error('Query read timeout'), 503, 'DATABASE_UNAVAILABLE'],
    [new TypeError('private'), 500, 'INTERNAL_ERROR'],
  ]) {
    const app = createApp({ query: async () => { throw error; } });
    const result = await request(app).get('/api/v1/stories').expect(status);
    assert.equal(result.body.error.code, code);
    assert.ok(!JSON.stringify(result.body).includes('private'));
    await request(app).get('/api/v1/stories?limit=-1').expect(400);
    await request(app).get('/api/v1/me').expect(401);
    await request(app).get('/unknown').expect(404);
    await request(app).get('/').expect(404);
  }
});

test('diagnostics redact messages, unknown codes, SQL values, URLs and nested connection errors', t => {
  const log = t.mock.method(console, 'error', () => {});
  const error = Object.assign(new Error('postgres://secret-user:secret-password@private-host/database'), {
    code: 'secret-code', detail: 'secret-value', query: 'secret-sql',
  });
  reportError(error, 'request');
  assert.deepEqual(JSON.parse(log.mock.calls[0].arguments[0]), {
    event: 'backend_error', context: 'request', category: 'internal', code: 'UNKNOWN',
  });
  const nested = new AggregateError([Object.assign(error, { code: 'ECONNRESET' })]);
  assert.deepEqual(failureInfo(nested), { category: 'database_connection', code: 'ECONNRESET' });
  reportError(nested, 'database_pool');
  assert.ok(!JSON.stringify(log.mock.calls).includes('secret'));
});

test('failed rollback preserves the original failure and removes the broken client', async t => {
  t.mock.method(console, 'error', () => {});
  const failure = Object.assign(new Error('query failed'), { code: 'ECONNRESET' });
  const releases = [];
  const client = {
    query: async sql => { if (sql === 'ROLLBACK') throw new Error('connection closed'); },
    release: discard => releases.push(discard),
  };
  await assert.rejects(transaction({ connect: async () => client }, async () => { throw failure; }), error => error === failure);
  assert.deepEqual(releases, [true]);
});

test('the shared pool is reused and idle socket errors do not crash initialization', async t => {
  const log = t.mock.method(console, 'error', () => {});
  const pool = database();
  try {
    assert.equal(database(), pool);
    assert.equal(pool.totalCount, 0);
    assert.doesNotThrow(() => pool.emit('error', Object.assign(new Error('private'), { code: 'ECONNRESET' })));
    assert.equal(JSON.parse(log.mock.calls[0].arguments[0]).context, 'database_pool');
    assert.equal(pool.totalCount, 0);
  } finally { await pool.end(); }
});
