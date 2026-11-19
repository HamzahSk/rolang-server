import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { database, transaction, mongoOptions } from '../src/db.js';
import { saveStory } from '../src/stories.js';
import { storySchema } from '../src/validation.js';
import { reportError } from '../src/errors.js';

export async function seed(store) {
  const samples = JSON.parse(await readFile(new URL('../data/sample-stories.json', import.meta.url), 'utf8')).map(sample => storySchema.parse(sample));
  let inserted = 0;
  for (const story of samples) {
    const created = await transaction(store, async scope => {
      if (await scope.db.collection('stories').findOne({ _id: story.id }, mongoOptions(scope))) return false;
      await saveStory(scope, story, { status: 'published' });
      return true;
    });
    if (created) inserted++;
  }
  return { inserted, skipped: samples.length - inserted };
}
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const store = database();
  try { console.log(JSON.stringify(await seed(store))); }
  catch (error) { reportError(error, 'seed'); console.error('Seed failed. Initialize MongoDB first and check sample data.'); process.exitCode = 1; }
  finally { await store.close(); }
}
