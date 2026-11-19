import { MongoClient, MongoOperationTimeoutError } from 'mongodb';
import { setTimeout as delay } from 'node:timers/promises';
import { mongodbConfig } from './config.js';
import { initializeDatabase } from './schema.js';
import { reportError } from './errors.js';

const timedOut = () => new MongoOperationTimeoutError('Database request timed out.');
export function createDatabase(env = process.env) {
  let client, connection, readiness, readyUntil = 0;
  return {
    // No configuration, DNS, or sockets during module imports. Simultaneous
    // cold requests share one promise; warm requests share the driver's pool.
    async connect() {
      if (!connection) {
        const config = mongodbConfig(env);
        const candidate = new MongoClient(config.uri, config.options);
        candidate.on('error', error => reportError(error, 'mongodb_client'));
        client = candidate;
        connection = candidate.connect().then(() => candidate.db(config.name)).catch(async error => {
          if (client === candidate) { connection = undefined; client = undefined; }
          await candidate.close().catch(() => {});
          throw error;
        });
      }
      return connection;
    },
    async scope({ refresh = false } = {}) {
      const db = await this.connect();
      if ((refresh || Date.now() >= readyUntil) && !readiness) {
        readyUntil = 0;
        readiness = initializeDatabase(db).then(() => { readyUntil = Date.now() + 60_000; })
          .finally(() => { readiness = undefined; });
      }
      if (readiness) await readiness;
      return { db };
    },
    async transaction(action, { timeoutMS = 20_000 } = {}) {
      const deadline = Date.now() + timeoutMS;
      const { db } = await this.scope();
      const session = client.startSession();
      const scope = { db, session, deadline };
      let attempt = 0;
      const abort = async () => {
        if (session.inTransaction()) await session.abortTransaction({ timeoutMS: 250 })
          .catch(error => reportError(error, 'mongodb_abort'));
      };
      try {
        // Use the driver's Core API. Every operation (including cursor batches)
        // gets the remaining deadline; commit retries never replay the callback.
        while (Date.now() < deadline) {
          session.startTransaction({ readConcern: { level: 'snapshot' },
            writeConcern: { w: 'majority' }, readPreference: 'primary',
            maxCommitTimeMS: Math.min(5_000, deadline - Date.now()) });
          let result;
          try { result = await action(scope); }
          catch (error) {
            await abort();
            if (!error.hasErrorLabel?.('TransientTransactionError')) throw error;
            if (Date.now() >= deadline) throw timedOut();
            await delay(Math.min(10 * ++attempt, 100, Math.max(1, deadline - Date.now())));
            continue;
          }
          let retryTransaction = false;
          while (Date.now() < deadline) {
            try {
              await session.commitTransaction({ timeoutMS: deadline - Date.now() });
              return result;
            } catch (error) {
              if (error.name === 'MongoOperationTimeoutError' || error.code === 50) throw error;
              if (Date.now() >= deadline) throw timedOut();
              if (error.hasErrorLabel?.('UnknownTransactionCommitResult')) continue;
              if (error.hasErrorLabel?.('TransientTransactionError')) { retryTransaction = true; break; }
              throw error;
            }
          }
          if (!retryTransaction) throw timedOut();
          await delay(Math.min(10 * ++attempt, 100, Math.max(1, deadline - Date.now())));
        }
        throw timedOut();
      } finally {
        // Best-effort abort is bounded and must not replace the original error.
        await session.endSession({ timeoutMS: 250 }).catch(error => reportError(error, 'mongodb_session_cleanup'));
      }
    },
    async close() {
      const current = client;
      await connection?.catch(() => {});
      await current?.close();
      client = connection = readiness = undefined;
      readyUntil = 0;
    },
  };
}
const cacheKey = Symbol.for('rolang.mongodb');
export function database() {
  return globalThis[cacheKey] ??= createDatabase();
}
export const transaction = (store, action, options) => store.transaction(action, options);
export function mongoOptions(scope) {
  const options = scope.session ? { session: scope.session } : {};
  if (scope.deadline !== undefined) {
    const remaining = scope.deadline - Date.now();
    if (remaining <= 0) throw timedOut();
    options.timeoutMS = remaining;
  }
  return options;
}
