import { ApiError } from './errors.js';
import { isDeepStrictEqual } from 'node:util';
import { MongoOperationTimeoutError } from 'mongodb';
export const schemaVersion = 'mongodb_001';
export const collections = {
  users: { required: ['email', 'password_hash', 'display_name', 'role', 'created_at'], properties: {
    _id: { bsonType: 'string' }, email: { bsonType: 'string' }, role: { enum: ['learner', 'admin'] },
    created_at: { bsonType: 'date' }, learning_revision: { bsonType: ['int', 'long', 'double'] },
  } },
  sessions: { required: ['user_id', 'expires_at', 'created_at'], properties: {
    _id: { bsonType: 'string' }, user_id: { bsonType: 'string' }, expires_at: { bsonType: 'date' }, created_at: { bsonType: 'date' },
  } },
  stories: { required: ['family', 'category', 'difficulty', 'status', 'content', 'version', 'created_at', 'updated_at'], properties: {
    _id: { bsonType: 'string' }, difficulty: { enum: ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'] },
    status: { enum: ['draft', 'published'] }, content: { bsonType: 'object' }, version: { bsonType: 'string' },
    created_at: { bsonType: 'date' }, updated_at: { bsonType: 'date' },
  } },
  story_chapters: { required: ['story_id', 'id', 'position', 'content', 'vocabulary', 'version', 'sentence_count'], properties: {
    story_id: { bsonType: 'string' }, id: { bsonType: 'string' }, position: { bsonType: ['int', 'double'], minimum: 1 },
    content: { bsonType: 'object' }, vocabulary: { bsonType: 'array' }, version: { bsonType: 'string' },
  } },
  story_vocabulary: { required: ['story_id', 'position', 'content'], properties: {
    story_id: { bsonType: 'string' }, position: { bsonType: ['int', 'double'], minimum: 1 }, content: { bsonType: 'object' },
  } },
  learning_records: { required: ['user_id', 'kind', 'key', 'data', 'deleted', 'revision', 'updated_at'], properties: {
    user_id: { bsonType: 'string' }, kind: { enum: ['progress', 'vocabulary', 'review', 'profile'] },
    key: { bsonType: 'string' }, data: { bsonType: ['object', 'null'] }, deleted: { bsonType: 'bool' },
    revision: { bsonType: ['int', 'long', 'double'], minimum: 0 }, updated_at: { bsonType: 'date' },
  } },
  sync_operations: { required: ['user_id', 'operation_id', 'fingerprint', 'created_at'], properties: {
    user_id: { bsonType: 'string' }, operation_id: { bsonType: 'string' }, fingerprint: { bsonType: 'string' }, created_at: { bsonType: 'date' },
  } },
  auth_attempts: { required: ['attempts', 'expires_at'], properties: {
    attempts: { bsonType: ['int', 'long', 'double'] }, expires_at: { bsonType: 'date' },
  } },
  dictionary: { required: ['language', 'word', 'content'], properties: {
    language: { enum: ['en', 'id', 'tl'] }, word: { bsonType: 'string' }, content: { bsonType: 'object' },
  } },
  corpus_imports: { required: ['metadata', 'imported_at'], properties: {
    metadata: { bsonType: 'object' }, imported_at: { bsonType: 'date' },
  } },
  counters: {}, schema_migrations: {}, postgres_schema_migrations: {}, database_imports: {},
};
export const indexSpecs = {
  users: [{ key: { email: 1 }, name: 'users_email', unique: true }],
  sessions: [
    { key: { user_id: 1 }, name: 'sessions_user' },
    { key: { expires_at: 1 }, name: 'sessions_expiry' },
  ],
  stories: [
    { key: { status: 1, _id: 1 }, name: 'stories_catalog' },
    { key: { status: 1, category: 1, _id: 1 }, name: 'stories_category' },
    { key: { status: 1, difficulty: 1, _id: 1 }, name: 'stories_difficulty' },
    { key: { status: 1, difficulty: 1, category: 1, _id: 1 }, name: 'stories_filters' },
    { key: { status: 1, languages: 1, _id: 1 }, name: 'stories_language' },
    { key: { family: 1, _id: 1 }, name: 'stories_family' },
    { key: { 'content.title.en': 'text', 'content.title.id': 'text', 'content.title.tl': 'text',
      'content.summary.en': 'text', 'content.summary.id': 'text', 'content.summary.tl': 'text', category: 'text', family: 'text' },
      name: 'stories_search', default_language: 'none', language_override: 'search_language' },
  ],
  story_chapters: [
    { key: { story_id: 1, id: 1 }, name: 'chapters_identity', unique: true },
    { key: { story_id: 1, position: 1 }, name: 'chapters_order', unique: true },
  ],
  story_vocabulary: [
    { key: { story_id: 1, position: 1 }, name: 'story_vocabulary_order', unique: true },
    { key: { story_id: 1, 'content.language': 1, position: 1 }, name: 'story_vocabulary_language' },
  ],
  learning_records: [
    { key: { user_id: 1, kind: 1, key: 1 }, name: 'learning_identity', unique: true },
    { key: { user_id: 1, revision: 1 }, name: 'learning_sync' },
    { key: { user_id: 1, kind: 1, deleted: 1, key: 1 }, name: 'learning_list' },
  ],
  sync_operations: [{ key: { user_id: 1, operation_id: 1 }, name: 'sync_identity', unique: true }],
  auth_attempts: [{ key: { expires_at: 1 }, name: 'auth_attempts_expiry' }],
  dictionary: [{ key: { language: 1, word: 1 }, name: 'dictionary_identity', unique: true }],
};
export async function checkSchema(db, { allowImportInProgress = false, timeoutMS = 10_000 } = {}) {
  const deadline = Date.now() + timeoutMS;
  const options = () => {
    const remaining = deadline - Date.now();
    if (remaining <= 0) throw new MongoOperationTimeoutError('Database readiness check timed out.');
    return { timeoutMS: remaining };
  };
  const migration = await db.collection('schema_migrations').findOne({ _id: schemaVersion }, options());
  const definitions = await db.listCollections({}, options()).toArray();
  const names = new Set(definitions.map(item => item.name));
  if (!migration || Object.keys(collections).some(name => !names.has(name)))
    throw new ApiError(503, 'DATABASE_NOT_READY', 'The database is not ready for this release.');
  const imported = await db.collection('database_imports').findOne({ _id: 'postgresql' }, options());
  if (!allowImportInProgress && imported && imported.state !== 'verified')
    throw new ApiError(503, 'DATABASE_NOT_READY', 'The data migration has not been verified.');
  for (const [name, schema] of Object.entries(collections)) {
    const options = definitions.find(item => item.name === name).options;
    if (!isDeepStrictEqual(options.validator?.$jsonSchema, { bsonType: 'object', ...schema }) ||
        options.validationLevel !== 'strict' || options.validationAction !== 'error')
      throw new ApiError(503, 'DATABASE_NOT_READY', 'The database is not ready for this release.');
  }
  const topology = await db.command({ hello: 1 }, options());
  if ((!topology.setName && topology.msg !== 'isdbgrid') || topology.logicalSessionTimeoutMinutes === undefined)
    throw new ApiError(503, 'DATABASE_NOT_READY', 'The database must support MongoDB transactions.');
  for (const [name, specs] of Object.entries(indexSpecs)) {
    const indexes = await db.collection(name).listIndexes(options()).toArray();
    for (const spec of specs) {
      const actual = indexes.find(index => index.name === spec.name);
      const text = Object.values(spec.key).includes('text');
      const keysMatch = text
        ? Object.keys(spec.key).every(key => actual?.weights?.[key] === 1) && actual?.default_language === 'none'
        : JSON.stringify(actual?.key) === JSON.stringify(spec.key);
      if (!actual || !keysMatch || Boolean(actual.unique) !== Boolean(spec.unique) ||
          actual.expireAfterSeconds !== spec.expireAfterSeconds)
        throw new ApiError(503, 'DATABASE_NOT_READY', 'The database is not ready for this release.');
    }
  }
}
