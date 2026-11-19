import pg from 'pg';
import { attachDatabasePool } from '@vercel/functions';
import { reportError } from './errors.js';

let sharedPool;
export function database() {
  // A small pool is reused within a warm Vercel function. Use the provider's
  // pooled endpoint; never disable TLS certificate verification here.
  if (sharedPool && !sharedPool.ending) return sharedPool;
  const pool = new pg.Pool({
    ...(process.env.DATABASE_URL ? { connectionString: process.env.DATABASE_URL } : {}),
    max: Math.max(1, Math.min(10, Math.floor(Number(process.env.DATABASE_POOL_SIZE) || 3))),
    idleTimeoutMillis: 10_000,
    connectionTimeoutMillis: 5_000,
    query_timeout: 15_000,
    allowExitOnIdle: true,
  });
  // pg emits idle socket failures outside request promises. An unhandled pool
  // error terminates Node and becomes FUNCTION_INVOCATION_FAILED on Vercel.
  pool.on('error', error => reportError(error, 'database_pool'));
  // Let idle timers finish before Vercel suspends a function, while retaining
  // the pool for concurrent requests and subsequent warm invocations.
  if (process.env.VERCEL === '1') attachDatabasePool(pool);
  return sharedPool = pool;
}

export async function transaction(pool, action) {
  const client = await pool.connect();
  let discard = false;
  try {
    await client.query('BEGIN');
    const result = await action(client);
    await client.query('COMMIT');
    return result;
  } catch (error) {
    try { await client.query('ROLLBACK'); }
    catch (rollbackError) { discard = true; reportError(rollbackError, 'database_rollback'); }
    throw error;
  } finally { client.release(discard); }
}
