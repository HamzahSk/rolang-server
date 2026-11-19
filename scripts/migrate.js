import { fileURLToPath } from 'node:url';
import { isDeepStrictEqual } from 'node:util';
import { database } from '../src/db.js';
import { collections, indexSpecs, schemaVersion, checkSchema } from '../src/schema.js';
import { reportError } from '../src/errors.js';

export async function migrate(store) {
  const db = await store.connect();
  const existing = new Map((await db.listCollections().toArray()).map(item => [item.name, item]));
  for (const [name, schema] of Object.entries(collections)) {
    if (!existing.has(name)) {
      try {
        await db.createCollection(name, { validator: { $jsonSchema: { bsonType: 'object', ...schema } },
          validationLevel: 'strict', validationAction: 'error' });
      } catch (error) { if (error.code !== 48) throw error; }
    } else if (!isDeepStrictEqual(existing.get(name).options.validator?.$jsonSchema, { bsonType: 'object', ...schema }) ||
        existing.get(name).options.validationLevel !== 'strict' || existing.get(name).options.validationAction !== 'error') {
      await db.command({ collMod: name, validator: { $jsonSchema: { bsonType: 'object', ...schema } },
        validationLevel: 'strict', validationAction: 'error' });
    }
    if (indexSpecs[name]) await db.collection(name).createIndexes(indexSpecs[name]);
  }
  await db.collection('schema_migrations').updateOne({ _id: schemaVersion },
    { $setOnInsert: { applied_at: new Date() } }, { upsert: true });
  await checkSchema(db, { allowImportInProgress: true });
}
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const store = database();
  try { await migrate(store); console.log('MongoDB collections and indexes verified.'); }
  catch (error) { reportError(error, 'mongodb_migration'); console.error('MongoDB initialization failed. Check configuration, database permissions, and index conflicts.'); process.exitCode = 1; }
  finally { await store.close(); }
}
