import { fileURLToPath } from 'node:url';
import { database } from '../src/db.js';
import { reportError } from '../src/errors.js';
import { importCorpus, readCorpus } from './import-corpus.js';

export async function seed(store) {
  const corpus = await readCorpus();
  const { db } = await store.scope();
  const ids = corpus.stories.map(story => story.id);
  const existing = await db.collection('stories').countDocuments({ _id: { $in: ids } });
  const report = await importCorpus(store, corpus);
  return { ...report, inserted: report.stories - existing, skipped: existing };
}
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const store = database();
  try { console.log(JSON.stringify(await seed(store))); }
  catch (error) { reportError(error, 'seed'); console.error('Seed failed. Check MongoDB connectivity, permissions, and corpus data.'); process.exitCode = 1; }
  finally { await store.close(); }
}
