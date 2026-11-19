import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { MongoParseError, MongoServerSelectionError, MongoOperationTimeoutError } from 'mongodb';
import { mongodbConfig, serverConfig } from '../src/config.js';
import { failureInfo, reportError } from '../src/errors.js';
import { assertDocumentSize, maxDocumentBytes, safeRevision, storyVersion } from '../src/documents.js';
import { readCorpus, prepareCorpus } from '../scripts/import-corpus.js';

test('configuration uses explicit MongoDB names and bounded pool/server settings', () => {
  const config = mongodbConfig({ MONGODB_URI: 'mongodb+srv://example.test/ignored',
    MONGODB_DB_NAME: 'rolang' });
  assert.equal(config.name, 'rolang');
  assert.equal(config.options.maxPoolSize, 5);
  assert.equal(config.options.minPoolSize, 0);
  assert.equal(config.options.timeoutMS, 15_000);
  for (const env of [{}, { MONGODB_URI: 'invalid://example.test/rolang', MONGODB_DB_NAME: 'rolang' },
    { MONGODB_URI: 'mongodb://example.test', MONGODB_DB_NAME: 'bad/name' }])
    assert.throws(() => mongodbConfig(env), error => error.code === 'MONGODB_CONFIGURATION');
  assert.equal(serverConfig({ SESSION_DAYS: '100', PORT: 'invalid' }).sessionDays, 90);
  assert.equal(serverConfig({ PORT: 'invalid' }).port, 3000);
});
test('production handler imports without database configuration', () => {
  const env = { ...process.env };
  for (const key of ['MONGODB_URI', 'MONGODB_DB_NAME']) delete env[key];
  const code = "const {default:handler} = await import('./api/index.js'); if (typeof handler !== 'function') process.exit(1);";
  const result = spawnSync(process.execPath, ['--input-type=module', '-e', code], { env, encoding: 'utf8', timeout: 5000 });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stderr, '');
});
test('driver diagnostics redact URI credentials, messages, values and unknown codes', t => {
  const log = t.mock.method(console, 'error', () => {});
  const secret = 'mongodb+srv://secret-user:secret-password@private-host/database';
  reportError(Object.assign(new Error(secret), { code: 'secret-code', detail: 'secret-value' }), 'request');
  assert.deepEqual(JSON.parse(log.mock.calls[0].arguments[0]), {
    event: 'backend_error', context: 'request', category: 'internal', code: 'UNKNOWN',
  });
  assert.equal(failureInfo(new MongoParseError(secret)).category, 'database_configuration');
  assert.equal(failureInfo(new MongoOperationTimeoutError(secret)).category, 'database_connection');
  const nested = new AggregateError([Object.assign(new Error(secret), { code: 'ECONNRESET' })]);
  assert.deepEqual(failureInfo(nested), { category: 'database_connection', code: 'ECONNRESET' });
  reportError(new MongoServerSelectionError(secret, {}), 'mongodb_client');
  assert.ok(!JSON.stringify(log.mock.calls).includes('secret'));
});
test('BSON limits and integer conversions prevent oversized documents and revision loss', () => {
  assert.throws(() => assertDocumentSize({ text: 'x'.repeat(maxDocumentBytes) }), error => error.code === 'DOCUMENT_TOO_LARGE');
  assert.throws(() => safeRevision('9007199254740992'), error => error.code === 'INVALID_DATABASE_VALUE');
  assert.equal(storyVersion('9007199254740993'), '9007199254740993');
  assert.throws(() => storyVersion('9223372036854775808'), error => error.code === 'INVALID_DATABASE_VALUE');
});
test('the entire retained corpus still validates without narrowing its learning content', async () => {
  const { stories, vocabulary } = prepareCorpus(await readCorpus());
  assert.equal(stories.length, 21);
  assert.equal(vocabulary.length, 1486);
  assert.equal(stories.reduce((count, story) => count + (story.exercises?.length ?? 0) +
    (story.chapters ?? []).reduce((sum, chapter) => sum + (chapter.exercises?.length ?? 0), 0), 0), 150);
  assert.ok(stories.filter(story => story.kind === 'STORY').every(story => story.sentences.length >= 5));
});
