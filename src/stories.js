import { createHash } from 'node:crypto';
import { levelFor, normalizeWord } from './validation.js';
import { mongoOptions } from './db.js';
import { documentId, assertDocumentSize, nextStoryVersion } from './documents.js';

export const hash = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
export function chaptersFor(story) {
  if (story.chapters) return story.chapters;
  const fields = ['sentences', 'speakers', 'objectives', 'notes', 'exercises', 'focus', 'pronunciation'];
  return [{ id: 'main', title: story.title, summary: story.summary,
    ...Object.fromEntries(fields.filter(key => story[key] !== undefined).map(key => [key, story[key]])) }];
}
export function vocabularyFor(chapter, vocabulary) {
  const keys = new Set();
  for (const code of ['en', 'id', 'tl']) {
    for (const sentence of chapter.sentences) for (const token of sentence[code].match(/[\p{L}\p{M}]+(?:['’-][\p{L}\p{M}]+)*/gu) ?? [])
      keys.add(code + ':' + normalizeWord(token));
    for (const word of chapter.focus?.[code] ?? []) keys.add(code + ':' + normalizeWord(word));
  }
  return vocabulary.filter(item => keys.has(item.language + ':' + item.word));
}
export function vocabularyDocuments(storyId, vocabulary) {
  return vocabulary.map((content, index) => assertDocumentSize({
    _id: documentId(storyId, index + 1), story_id: storyId, position: index + 1, content,
  }));
}
export function chapterDocuments(story) {
  return chaptersFor(story).map((content, index) => {
    const vocabulary = vocabularyFor(content, story.vocabulary);
    return assertDocumentSize({
      _id: documentId(story.id, content.id), story_id: story.id, id: content.id, position: index + 1,
      content, vocabulary, version: hash({ chapter: content, vocabulary }), sentence_count: content.sentences.length,
    });
  });
}
export async function saveChapters(scope, story) {
  const documents = chapterDocuments(story);
  const collection = scope.db.collection('story_chapters');
  await collection.deleteMany({ story_id: story.id }, mongoOptions(scope));
  if (documents.length) await collection.insertMany(documents, mongoOptions(scope));
}
export async function saveStory(scope, story, { previous, status = previous?.status ?? 'draft' } = {}) {
  const { vocabulary, ...content } = story;
  const now = new Date();
  const version = await nextStoryVersion(scope);
  const row = assertDocumentSize({
    _id: story.id, family: story.family, category: story.category, difficulty: story.difficulty, status,
    content, sentence_count: story.sentences.length, chapter_count: chaptersFor(story).length,
    languages: Object.keys(story.title), version, created_at: previous?.created_at ?? now, updated_at: now,
  });
  // Preflight every BSON document before replacing any of the existing content.
  const words = vocabularyDocuments(story.id, vocabulary);
  chapterDocuments(story);
  if (previous) await scope.db.collection('stories').replaceOne({ _id: story.id }, row, mongoOptions(scope));
  else await scope.db.collection('stories').insertOne(row, mongoOptions(scope));
  await scope.db.collection('story_vocabulary').deleteMany({ story_id: story.id }, mongoOptions(scope));
  if (words.length) await scope.db.collection('story_vocabulary').insertMany(words, mongoOptions(scope));
  await saveChapters(scope, story);
  return { ...row, vocabulary };
}
export async function loadVocabulary(scope, storyId, language) {
  return (await scope.db.collection('story_vocabulary').find({
    story_id: storyId, ...(language ? { 'content.language': language } : {}),
  }, mongoOptions(scope)).sort({ position: 1 }).toArray()).map(row => row.content);
}
export async function chapterRows(scope, row, summaryOnly = false) {
  const projection = summaryOnly ? { id: 1, position: 1, 'content.title': 1, 'content.summary': 1, sentence_count: 1, version: 1 } : undefined;
  const rows = await scope.db.collection('story_chapters').find({ story_id: row._id },
    { ...mongoOptions(scope), ...(projection ? { projection } : {}) }).sort({ position: 1 }).toArray();
  if (rows.length) return rows;
  // Preserve readability of pre-chapter PostgreSQL sources and existing data.
  const vocabulary = row.vocabulary ?? await loadVocabulary(scope, row._id);
  return chapterDocuments({ ...row.content, id: row._id, vocabulary });
}
export function chapterSummary(row) {
  return { id: row.id, order: row.position, title: row.content.title, summary: row.content.summary,
    sentenceCount: row.sentence_count ?? row.content.sentences.length, version: row.version };
}
export const publicStory = (row, includeVocabulary = false) => ({
  ...row.content, level: levelFor(row.difficulty), status: row.status, version: String(row.version),
  updatedAt: row.updated_at.toISOString(), ...(includeVocabulary ? { vocabulary: row.vocabulary } : {}),
});
export function storySummary(row) {
  const story = publicStory(row);
  return { sentenceCount: row.sentence_count, chapterCount: row.chapter_count,
    ...Object.fromEntries(['id', 'family', 'category', 'difficulty', 'level', 'order', 'kind', 'image', 'cover',
      'title', 'summary', 'status', 'version', 'updatedAt'].filter(key => story[key] !== undefined).map(key => [key, story[key]])) };
}
export function conditional(req, res, version) {
  res.set({ ETag: '"' + version + '"', 'Cache-Control': 'private, no-cache' });
  if (req.get('if-none-match') === '"' + version + '"') { res.status(304).end(); return true; }
  return false;
}
