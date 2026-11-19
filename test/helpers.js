import { randomUUID } from 'node:crypto';
import { createDatabase } from '../src/db.js';

export async function mongoFixture(prefix) {
  if (!process.env.TEST_MONGODB_URI)
    throw new Error('Set TEST_MONGODB_URI to a disposable MongoDB replica set. See compose.test.yml and docs/DEPLOYMENT.md.');
  const name = 'rolang_test_' + prefix + '_' + randomUUID().replaceAll('-', '');
  const env = { MONGODB_URI: process.env.TEST_MONGODB_URI, MONGODB_DB_NAME: name };
  const store = createDatabase(env);
  const db = await store.connect();
  return { name, env, store, db, async close() {
    try {
      if (!db.databaseName.startsWith('rolang_test_')) throw new Error('Refusing to drop a non-test database.');
      await db.dropDatabase();
    } finally { await store.close(); }
  } };
}
