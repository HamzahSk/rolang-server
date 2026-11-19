// Archived PostgreSQL schema runner. The MongoDB importer never invokes it.
// Use only for a separately authorized rollback or disposable source fixtures.
import { readdir, readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { postgresDatabase, postgresTransaction } from './db.js';
import { reportError } from '../../src/errors.js';

export async function migratePostgres(pool) {
  await postgresTransaction(pool, async client => {
    await client.query('SELECT pg_advisory_xact_lock(78201342)');
    await client.query('CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())');
    const dir = new URL('../../migrations/', import.meta.url);
    for (const name of (await readdir(dir)).filter(name => name.endsWith('.sql')).sort()) {
      if ((await client.query('SELECT name FROM schema_migrations WHERE name=$1', [name])).rowCount) continue;
      await client.query(await readFile(new URL(name, dir), 'utf8'));
      await client.query('INSERT INTO schema_migrations(name) VALUES($1)', [name]);
    }
  });
}
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const pool = postgresDatabase();
  try { await migratePostgres(pool); console.log('Retained PostgreSQL migrations applied.'); }
  catch (error) { reportError(error, 'postgres_migration'); process.exitCode = 1; }
  finally { await pool.end(); }
}
