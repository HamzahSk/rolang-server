import { reportError, failureInfo } from './errors.js';
import { checkSchema } from './schema.js';
export async function healthStatus(store) {
  let connected = false;
  try {
    const db = await store.connect();
    await db.command({ ping: 1 }, { timeoutMS: 5_000 });
    connected = true;
    await checkSchema(db);
    return { status: 'ok', apiVersion: 'v1', database: 'connected' };
  } catch (error) {
    reportError(error, connected ? 'health_schema' : 'health_connection');
    const notReady = connected && failureInfo(error).category === 'database_schema';
    return { status: 'unavailable', apiVersion: 'v1', database: connected ? 'connected' : 'unavailable',
      error: { code: notReady ? 'DATABASE_NOT_READY' : 'DATABASE_UNAVAILABLE',
        message: notReady ? 'The database is not ready for this release.' : 'The database is temporarily unavailable.' } };
  }
}
