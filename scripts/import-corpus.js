import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { isDeepStrictEqual } from 'node:util';
import { z } from 'zod';
import { database, transaction, mongoOptions } from '../src/db.js';
import { reportError } from '../src/errors.js';
import { storySchema, lexeme, normalizeWord } from '../src/validation.js';
import { saveStory, saveChapters, hash, chapterDocuments, loadVocabulary } from '../src/stories.js';
import { documentId, assertDocumentSize } from '../src/documents.js';

export async function readCorpus(path = new URL('../data/corpus.json',import.meta.url)) {
  return JSON.parse(await readFile(path,'utf8'));
}
export function prepareCorpus(corpus) {
  const vocabulary = z.array(lexeme).parse(corpus.lexicon);
  const keys = vocabulary.map(w => `${w.language}:${w.word}`);
  if (new Set(keys).size !== keys.length) throw new Error('Duplicate dictionary entries.');
  const stories = corpus.stories.map(unit => {
    // Include words from every learning field, and focus phrases with spaces.
    const used = new Set();
    function visit(value, code) {
      if (typeof value === 'string' && code) {
        used.add(`${code}:${normalizeWord(value)}`);
        for (const word of value.match(/[\p{L}\p{M}]+(?:['’-][\p{L}\p{M}]+)*/gu) ?? []) used.add(`${code}:${normalizeWord(word)}`);
      } else if (Array.isArray(value)) value.forEach(v => visit(v,code));
      else if (value && typeof value === 'object') for (const [key,v] of Object.entries(value)) visit(v,['id','fil'].includes(key) ? key : code);
    }
    visit(unit);
    const difficulty = { BEGINNER:'A1', INTERMEDIATE:'B1', ADVANCED:'C1' }[unit.level];
    return storySchema.parse({ ...unit, difficulty, vocabulary:vocabulary.filter(w => used.has(`${w.language}:${w.word}`)) });
  });
  if (!stories.length || new Set(stories.map(s => s.id)).size !== stories.length) throw new Error('Empty corpus or duplicate story IDs.');
  return { stories,vocabulary };
}

const resolveScope = value => value.db ? value : value.scope();
const importConflict = () => Object.assign(new Error('Existing content differs. Review and back it up before using --replace-existing.'), { code: 'IMPORT_CONFLICT' });
export function countExercises(story, chapters = story.chapters ?? []) {
  // Root and chapter exercise definitions may share IDs. Count each learning
  // exercise once, while including exercises that exist only in chapters.
  return new Set([story, ...(story.chapters ?? []), ...chapters].flatMap(unit =>
    Array.isArray(unit.exercises) ? unit.exercises.map(item => item.id ?? hash(item)) : [])).size;
}

export async function verifyCorpus(value, corpus) {
  const scope = await resolveScope(value);
  const { stories, vocabulary } = prepareCorpus(corpus);
  const ids = stories.map(story => story.id);
  const stored = new Map((await scope.db.collection('stories').find({ _id: { $in: ids } }, mongoOptions(scope)).toArray()).map(row => [row._id, row]));
  const chapters = await scope.db.collection('story_chapters').find({ story_id: { $in: ids } }, mongoOptions(scope)).sort({ position: 1 }).toArray();
  for (const story of stories) {
    const row = stored.get(story.id);
    const { vocabulary: words, ...content } = story;
    if (!row || !isDeepStrictEqual(row.content, content) || row.status !== 'published' ||
        !isDeepStrictEqual(await loadVocabulary(scope, story.id), words))
      throw Object.assign(new Error('Story verification failed.'), { code: 'IMPORT_VERIFICATION_FAILED' });
    const actual = chapters.filter(chapter => chapter.story_id === story.id);
    const expected = chapterDocuments(story);
    if (actual.length !== expected.length || actual.some((row, index) => !isDeepStrictEqual(row, expected[index])))
      throw Object.assign(new Error('Chapter verification failed.'), { code: 'IMPORT_VERIFICATION_FAILED' });
  }
  const dictionary = new Map((await scope.db.collection('dictionary').find({
    _id: { $in: vocabulary.map(word => documentId(word.language, word.word)) },
  }, mongoOptions(scope)).toArray()).map(row => [row._id, row.content]));
  for (const word of vocabulary) {
    if (!isDeepStrictEqual(dictionary.get(documentId(word.language, word.word)), word))
      throw Object.assign(new Error('Dictionary verification failed.'), { code: 'IMPORT_VERIFICATION_FAILED' });
  }
  return { stories: stories.length, chapters: stories.reduce((total, story) => total + (story.chapters?.length ?? 1), 0),
    vocabulary: vocabulary.length, exercises: stories.reduce((total, story) => total + countExercises(story), 0),
    sourceHash: hash(corpus) };
}
export async function importCorpus(store, corpus, { replaceExisting = false } = {}) {
  const { stories, vocabulary } = prepareCorpus(corpus);
  return transaction(store, async scope => {
    await scope.db.collection('counters').updateOne({ _id: 'corpus_import' }, { $inc: { lock: 1 } },
      { ...mongoOptions(scope), upsert: true });
    const oldWords = new Map((await scope.db.collection('dictionary').find({
      _id: { $in: vocabulary.map(word => documentId(word.language, word.word)) },
    }, mongoOptions(scope)).toArray()).map(row => [row._id, row]));
    // Preflight dictionary conflicts before touching stories. Transaction
    // rollback also protects against later story/chapter conflicts.
    for (const word of vocabulary) {
      const old = oldWords.get(documentId(word.language, word.word));
      if (old && !isDeepStrictEqual(old.content, word) && !replaceExisting) throw importConflict();
    }
    for (const story of stories) {
      const { vocabulary: words, ...content } = story;
      const previous = await scope.db.collection('stories').findOne({ _id: story.id }, mongoOptions(scope));
      const same = previous && isDeepStrictEqual(previous.content, content) &&
        isDeepStrictEqual(await loadVocabulary(scope, story.id), words) && previous.status === 'published';
      if (previous && !same && !replaceExisting) throw importConflict();
      if (!same) await saveStory(scope, story, { previous, status: 'published' });
      else {
        const existing = await scope.db.collection('story_chapters').find({ story_id: story.id }, mongoOptions(scope)).sort({ position: 1 }).toArray();
        if (!existing.length) await saveChapters(scope, story);
        else if (!isDeepStrictEqual(existing, chapterDocuments(story))) {
          if (!replaceExisting) throw importConflict();
          await saveStory(scope, story, { previous, status: 'published' });
        }
      }
    }
    const writes = vocabulary.flatMap(word => {
      const _id = documentId(word.language, word.word);
      if (isDeepStrictEqual(oldWords.get(_id)?.content, word)) return [];
      return [{ replaceOne: { filter: { _id }, replacement: assertDocumentSize({
        _id, language: word.language, word: word.word, content: word,
      }), upsert: true } }];
    });
    if (writes.length) await scope.db.collection('dictionary').bulkWrite(writes, mongoOptions(scope));
    const report = await verifyCorpus(scope, corpus);
    await scope.db.collection('corpus_imports').updateOne({ _id: report.sourceHash },
      { $setOnInsert: { metadata: { ...report, version: corpus.version, course: corpus.course }, imported_at: new Date() } },
      { ...mongoOptions(scope), upsert: true });
    return report;
  }, { timeoutMS: 60_000 });
}
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  const store = database();
  try {
    const corpus = await readCorpus(args.find(arg => !arg.startsWith('--')));
    const report = args.includes('--verify') ? await verifyCorpus(store, corpus)
      : await importCorpus(store, corpus, { replaceExisting: args.includes('--replace-existing') });
    console.log(JSON.stringify(report, null, 2));
  } catch (error) {
    reportError(error, 'corpus_import');
    console.error('Corpus import/verification failed. Check MongoDB initialization, content validity, and existing-content conflicts.');
    process.exitCode = 1;
  } finally { await store.close(); }
}
