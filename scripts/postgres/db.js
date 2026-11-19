// Retained solely for source migration/rollback tools. Runtime API modules
// never import pg or fall back to PostgreSQL. Existing DATABASE_URL is retained.
import pg from 'pg';
import { reportError } from '../../src/errors.js';

export function postgresDatabase(env = process.env, options = {}) {
  if (!env.DATABASE_URL || !/^postgres(?:ql)?:\/\//.test(env.DATABASE_URL))
    throw Object.assign(new Error('Set DATABASE_URL for the PostgreSQL source.'), { code: 'POSTGRES_CONFIGURATION' });
  const pool = new pg.Pool({
    connectionString: env.DATABASE_URL,
    max: 1, idleTimeoutMillis: 10_000, connectionTimeoutMillis: 5_000,
    query_timeout: 30_000, allowExitOnIdle: true, ...options,
  });
  pool.on('error', error => reportError(error, 'postgres_migration_source'));
  return pool;
}
export async function postgresTransaction(pool, action) {
  const client = await pool.connect();
  let discard = false;
  try {
    await client.query('BEGIN');
    const result = await action(client);
    await client.query('COMMIT');
    return result;
  } catch (error) {
    try { await client.query('ROLLBACK'); }
    catch (rollbackError) { discard = true; reportError(rollbackError, 'postgres_rollback'); }
    throw error;
  } finally { client.release(discard); }
}
