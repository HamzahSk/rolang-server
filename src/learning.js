import { createHash } from 'node:crypto';
import { transaction, mongoOptions } from './db.js';
import { ApiError } from './errors.js';
import { documentId, assertDocumentSize, safeRevision } from './documents.js';
import { legacyVocabularyStatus, vocabularySchema } from './validation.js';

export const record = row => ({ kind: row.kind, key: row.key,
  data: row.kind === 'vocabulary' && !row.deleted ? { ...row.data,
    status: row.data.status ?? legacyVocabularyStatus(row.data), statusChangedAt: row.data.statusChangedAt ?? 0 } : row.data,
  deleted: row.deleted, revision: safeRevision(row.revision) });
export async function lockUser(scope, userId) {
  // Competing transactions write the same user document, so one must retry
  // before publishing its revisions. No cursor can pass an uncommitted write.
  const result = await scope.db.collection('users').updateOne({ _id: userId }, { $inc: { sync_lock: 1 } }, mongoOptions(scope));
  if (!result.matchedCount) throw new ApiError(409, 'RESOURCE_CONFLICT', 'A related resource is no longer available.');
}
export async function putRecord(scope, userId, kind, key, data, deleted = false) {
  if (kind === 'vocabulary' && !deleted) data = vocabularySchema.parse(data);
  const _id = documentId(userId, kind, key);
  const collection = scope.db.collection('learning_records');
  const previous = await collection.findOne({ _id }, mongoOptions(scope));
  if (kind === 'progress' && !deleted && previous && !previous.deleted)
    data = { ...data, completed: Boolean(previous.data?.completed || data.completed) };
  const user = await scope.db.collection('users').findOneAndUpdate(
    { _id: userId }, { $inc: { learning_revision: 1 } }, { ...mongoOptions(scope), returnDocument: 'after' });
  if (!user) throw new ApiError(409, 'RESOURCE_CONFLICT', 'A related resource is no longer available.');
  const row = assertDocumentSize({ _id, user_id: userId, kind, key, data, deleted,
    revision: safeRevision(user.learning_revision), updated_at: new Date() });
  await collection.replaceOne({ _id }, row, { ...mongoOptions(scope), upsert: true });
  return record(row);
}
export async function synchronize(store, userId, input) {
  return transaction(store, async scope => {
    await lockUser(scope, userId);
    const acknowledged = [];
    for (const op of input.operations) {
      const fingerprint = createHash('sha256').update(JSON.stringify(op)).digest('hex');
      const _id = documentId(userId, op.id);
      const previous = await scope.db.collection('sync_operations').findOne({ _id }, mongoOptions(scope));
      if (previous) {
        if (previous.fingerprint !== fingerprint)
          throw new ApiError(409, 'OPERATION_CONFLICT', 'Operation ID was already used for different data.');
      } else {
        await scope.db.collection('sync_operations').insertOne({
          _id, user_id: userId, operation_id: op.id, fingerprint, created_at: new Date(),
        }, mongoOptions(scope));
        await putRecord(scope, userId, op.kind, op.key, op.data, op.deleted);
      }
      acknowledged.push(op.id);
    }
    const latestRow = await scope.db.collection('learning_records').find({ user_id: userId }, mongoOptions(scope))
      .sort({ revision: -1 }).limit(1).next();
    const latest = latestRow ? safeRevision(latestRow.revision) : 0;
    if (input.cursor > latest) throw new ApiError(409, 'CURSOR_INVALID', 'Reset the synchronization cursor to zero.');
    const rows = await scope.db.collection('learning_records').find({
      user_id: userId, revision: { $gt: input.cursor },
    }, mongoOptions(scope)).sort({ revision: 1 }).limit(501).toArray();
    const hasMore = rows.length > 500;
    const records = rows.slice(0, 500).map(record);
    return { acknowledged, records, hasMore, cursor: hasMore ? records.at(-1).revision : latest };
  });
}
