import { BSON, Long } from 'mongodb';
import { createHash } from 'node:crypto';
import { ApiError } from './errors.js';
import { mongoOptions } from './db.js';

export const documentId = (...parts) => createHash('sha256').update(JSON.stringify(parts)).digest('hex');
export const maxDocumentBytes = 16 * 1024 * 1024 - 64 * 1024;
export function assertDocumentSize(document) {
  if (BSON.calculateObjectSize(document) > maxDocumentBytes)
    throw new ApiError(413, 'DOCUMENT_TOO_LARGE', 'Content exceeds the MongoDB document size limit. Split it into smaller chapters.');
  return document;
}
export function safeRevision(value) {
  const result = Number(value);
  if (!Number.isSafeInteger(result) || result < 0)
    throw Object.assign(new Error('Learning revision exceeds the API integer range.'), { code: 'IMPORT_INVALID_SOURCE' });
  return result;
}
export function storyVersion(value) {
  const text = String(value);
  if (!/^[1-9][0-9]*$/.test(text) || BigInt(text) > 9_223_372_036_854_775_807n)
    throw Object.assign(new Error('Invalid story version.'), { code: 'IMPORT_INVALID_SOURCE' });
  return text;
}
export async function nextStoryVersion(scope) {
  const counter = await scope.db.collection('counters').findOneAndUpdate(
    { _id: 'story_version' }, { $inc: { value: Long.ONE } },
    { ...mongoOptions(scope), upsert: true, returnDocument: 'after' });
  return storyVersion(counter.value);
}
