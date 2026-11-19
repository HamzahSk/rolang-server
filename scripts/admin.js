import { database } from '../src/db.js';
const store = database();
try {
  if (!process.argv[2]) throw new Error();
  const { db } = await store.scope();
  const result = await db.collection('users').updateOne({ email: process.argv[2].trim().toLowerCase() }, { $set: { role: 'admin' } });
  if (!result.matchedCount) throw new Error();
  console.log('Registered account promoted to administrator.');
} catch { console.error('Promotion failed. Supply the email of an existing account and verify MongoDB configuration.'); process.exitCode = 1; }
finally { await store.close(); }
