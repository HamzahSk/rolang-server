import { database } from '../src/db.js';
import { indexSpecs } from '../src/schema.js';
import { reportError } from '../src/errors.js';

const store = database();
try {
  // Connect without running readiness first: the legacy text index is exactly
  // what prevents normal initialization from creating the focused replacement.
  const db = await store.connect();
  const stories = db.collection('stories');
  const desired = indexSpecs.stories.find(spec => spec.name === 'stories_search_id_fil');
  const exists = await db.listCollections({ name: 'stories' }).hasNext();
  const indexes = exists ? await stories.listIndexes().toArray() : [];
  const textIndexes = indexes.filter(index => index.weights);
  const unexpected = textIndexes.filter(index => !['stories_search', desired.name].includes(index.name));
  if (unexpected.length)
    throw new Error(`Refusing to replace an unrecognized text index: ${unexpected.map(index => index.name).join(', ')}`);

  const legacy = textIndexes.find(index => index.name === 'stories_search');
  if (legacy) {
    await stories.dropIndex(legacy.name);
    try {
      await stories.createIndex(desired.key, {
        name: desired.name,
        default_language: desired.default_language,
        language_override: desired.language_override,
      });
    } catch (error) {
      const oldKey = Object.fromEntries(Object.keys(legacy.weights).map(key => [key, 'text']));
      await stories.createIndex(oldKey, {
        name: legacy.name,
        default_language: legacy.default_language,
        language_override: legacy.language_override,
      }).catch(() => {});
      throw error;
    }
  }
  await store.scope({ refresh: true });
  console.log(JSON.stringify({ migrated: Boolean(legacy), searchIndex: desired.name, learningRecordsChanged: 0 }));
} catch (error) {
  reportError(error, 'language_pair_migration');
  console.error('Language-pair migration failed. Existing content and learning records were not removed.');
  process.exitCode = 1;
} finally {
  await store.close();
}
