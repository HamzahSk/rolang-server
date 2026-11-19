import { database } from '../src/db.js';
import { healthStatus } from '../src/health.js';
import { reportError } from '../src/errors.js';

// Read-only production verification. Never print connection parameters or data.
const pool = database();
try {
  const status = await healthStatus(pool);
  if (status.status !== 'ok') {
    console.log(JSON.stringify(status));
    process.exitCode = 1;
  } else {
    await pool.query(`SELECT id,version,updated_at,jsonb_array_length(content->'sentences')
      FROM stories WHERE status='published' ORDER BY id LIMIT 1`);
    console.log(JSON.stringify({ ...status, catalog: 'ok' }));
  }
} catch (error) {
  reportError(error, 'database_doctor');
  process.exitCode = 1;
} finally { await pool.end(); }
