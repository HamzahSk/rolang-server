import { reportError, databaseFailure } from './errors.js';
export async function healthStatus(store) {
  let connected = false;
  try {
    const db = await store.connect();
    await db.command({ ping: 1 }, { timeoutMS: 5_000 });
    connected = true;
    await store.scope({ refresh: true });
    return { status: 'ok', apiVersion: 'v1', database: 'connected' };
  } catch (error) {
    reportError(error, connected ? 'health_initialization' : 'health_connection');
    return { status: 'unavailable', apiVersion: 'v1', database: connected ? 'connected' : 'unavailable',
      error: databaseFailure(error) ?? { code: 'DATABASE_UNAVAILABLE', message: 'MongoDB health verification failed.' } };
  }
}
