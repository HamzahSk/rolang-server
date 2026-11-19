import { database } from '../src/db.js';
import { healthStatus } from '../src/health.js';
import { reportError } from '../src/errors.js';
import { storySummary, chapterRows, loadVocabulary } from '../src/stories.js';
import { indexSpecs } from '../src/schema.js';

const store = database();
try {
  const status = await healthStatus(store);
  if (status.status !== 'ok') { console.log(JSON.stringify(status)); process.exitCode = 1; }
  else {
    const scope = await store.scope();
    const row = await scope.db.collection('stories').find({ status: 'published' }).sort({ _id: 1 }).limit(1).next();
    if (row) {
      storySummary(row);
      await chapterRows(scope, row, true);
      await loadVocabulary(scope, row._id);
    }
    console.log(JSON.stringify({ ...status, catalog: row ? 'ok' : 'empty',
      indexes: Object.values(indexSpecs).reduce((total, specs) => total + specs.length, 0) }));
  }
} catch (error) { reportError(error, 'database_doctor'); process.exitCode = 1; }
finally { await store.close(); }
