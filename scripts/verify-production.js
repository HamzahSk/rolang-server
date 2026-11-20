import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { readCorpus, prepareCorpus, countExercises } from './import-corpus.js';
import { chapterDocuments, hash } from '../src/stories.js';

const direct = process.argv[1] === fileURLToPath(import.meta.url);

function serverOrigin(value) {
  const url = new URL(value);
  const local = ['localhost', '127.0.0.1', '::1'].includes(url.hostname);
  if (url.protocol !== 'https:' && !(local && url.protocol === 'http:'))
    throw new Error('Use an HTTPS server origin (HTTP is allowed only for localhost).');
  if (url.username || url.password || url.search || url.hash || url.pathname !== '/')
    throw new Error('Supply only the server origin, without credentials, path, query, or fragment.');
  return url;
}

async function response(origin, path, { expectedStatus = 200, headers } = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30_000);
  const url = new URL(path, origin);
  let result;
  try {
    result = await fetch(url, { headers, signal: controller.signal });
    assert.equal(result.status, expectedStatus, `${url.pathname}${url.search} returned HTTP ${result.status}`);
    if (expectedStatus === 304) return { headers: result.headers };
    return { body: await result.json(), headers: result.headers };
  } finally {
    clearTimeout(timeout);
  }
}

function exactFields(actual, expected, context, omitted = []) {
  const skip = new Set(omitted);
  for (const [key, value] of Object.entries(expected)) {
    if (!skip.has(key)) assert.deepEqual(actual[key], value, `${context}.${key} differs from the canonical corpus`);
  }
}

async function concurrent(items, limit, action) {
  const results = new Array(items.length);
  let next = 0;
  async function worker() {
    while (next < items.length) {
      const index = next++;
      results[index] = await action(items[index], index);
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return results;
}

function expectedModules(stories) {
  const groups = new Map();
  for (const story of stories) {
    const current = groups.get(story.family) ?? { id: story.family, order: story.order,
      unitCount: 0, lessonCount: 0, storyCount: 0, ids: [] };
    current.order = Math.min(current.order, story.order);
    current.unitCount++;
    if (story.kind === 'LESSON') current.lessonCount++;
    else current.storyCount++;
    current.ids.push(story.id);
    groups.set(story.family, current);
  }
  return [...groups.values()].sort((a, b) => a.order - b.order || a.id.localeCompare(b.id));
}

export async function verifyProduction(value) {
  const origin = serverOrigin(value);
  const api = new URL('/api/v1/', origin);
  const corpus = await readCorpus();
  const { stories, vocabulary } = prepareCorpus(corpus);
  const modules = expectedModules(stories);

  const health = (await response(origin, '/health')).body;
  assert.deepEqual(health, { status: 'ok', apiVersion: 'v1', database: 'connected' });

  const curriculum = (await response(api, 'curriculum')).body;
  assert.equal(curriculum.id, 'id-fil-a1');
  assert.equal(curriculum.nativeLanguage, 'id');
  assert.equal(curriculum.targetLanguage, 'fil');
  assert.equal(curriculum.difficulty, 'A1');
  assert.equal(curriculum.level, 'BEGINNER');
  assert.equal(curriculum.unitCount, stories.length);
  assert.equal(curriculum.lessonCount, stories.filter(story => story.kind === 'LESSON').length);
  assert.equal(curriculum.storyCount, stories.filter(story => story.kind === 'STORY').length);
  assert.deepEqual(curriculum.modules.map(item => item.id), modules.map(item => item.id));

  const moduleList = (await response(api, 'curriculum/modules')).body;
  assert.deepEqual(moduleList.modules, curriculum.modules);
  await concurrent(modules, 6, async expected => {
    const body = (await response(api, `curriculum/modules/${expected.id}`)).body;
    assert.equal(body.curriculumId, 'id-fil-a1');
    for (const key of ['id', 'order', 'unitCount', 'lessonCount', 'storyCount'])
      assert.equal(body.module[key], expected[key], `module ${expected.id}.${key} differs`);
    assert.deepEqual(body.units.map(unit => unit.id), expected.ids);
  });

  const catalog = (await response(api, 'stories?limit=100&language=fil&difficulty=A1')).body;
  assert.equal(catalog.next, null);
  const expectedCatalog = [...stories].sort((a, b) => a.id.localeCompare(b.id));
  assert.deepEqual(catalog.stories.map(story => story.id), expectedCatalog.map(story => story.id));
  for (const [index, item] of catalog.stories.entries()) {
    const expected = expectedCatalog[index];
    exactFields(item, expected, `catalog.${expected.id}`, ['sentences', 'speakers', 'objectives', 'notes',
      'exercises', 'focus', 'pronunciation', 'chapters', 'vocabulary']);
    assert.equal(item.status, 'published');
    assert.equal(item.sentenceCount, expected.sentences.length);
    assert.equal(item.chapterCount, expected.chapters?.length ?? 1);
  }

  const retrievedVocabulary = new Map();
  const retrievedExercises = new Map();
  let retrievedChapters = 0;
  await concurrent(stories, 4, async story => {
    const manifestResult = await response(api, `stories/${story.id}?view=manifest`);
    const manifest = manifestResult.body;
    assert.equal('sentences' in manifest, false, `${story.id} manifest unexpectedly contains sentences`);
    exactFields(manifest, story, `manifest.${story.id}`, ['sentences', 'chapters']);
    assert.equal(manifest.status, 'published');
    // Vercel may preserve the application ETag as a weak validator.
    assert.match(manifestResult.headers.get('etag') ?? '', /^(?:W\/)?"[0-9]+"$/);

    const content = (await response(api, `stories/${story.id}/content`)).body;
    exactFields(content, story, `content.${story.id}`, ['chapters']);
    assert.equal(content.status, 'published');
    const expectedChapters = chapterDocuments(story);
    assert.equal(content.chapters.length, expectedChapters.length);
    retrievedChapters += content.chapters.length;
    for (const [index, chapter] of content.chapters.entries()) {
      const expected = expectedChapters[index];
      exactFields(chapter, expected.content, `content.${story.id}.chapters.${expected.id}`);
      assert.equal(chapter.order, expected.position);
      assert.equal(chapter.version, expected.version);
      assert.deepEqual(chapter.vocabulary, expected.vocabulary);
    }

    const chapterList = (await response(api, `stories/${story.id}/chapters?limit=100`)).body;
    assert.equal(chapterList.storyId, story.id);
    assert.equal(chapterList.version, content.version);
    assert.equal(chapterList.next, null);
    assert.deepEqual(chapterList.chapters.map(chapter => chapter.id), expectedChapters.map(chapter => chapter.id));
    await concurrent(expectedChapters, 4, async expected => {
      const chapter = (await response(api, `stories/${story.id}/chapters/${expected.id}`)).body;
      exactFields(chapter, expected.content, `chapter.${story.id}.${expected.id}`);
      assert.equal(chapter.storyId, story.id);
      assert.equal(chapter.storyVersion, content.version);
      assert.equal(chapter.order, expected.position);
      assert.equal(chapter.version, expected.version);
      assert.deepEqual(chapter.vocabulary, expected.vocabulary);
    });

    for (const word of content.vocabulary) retrievedVocabulary.set(`${word.language}:${word.word}`, word);
    for (const unit of [content, ...content.chapters]) {
      for (const exercise of unit.exercises ?? []) {
        const previous = retrievedExercises.get(exercise.id);
        if (previous) assert.deepEqual(exercise, previous, `exercise ${exercise.id} has conflicting definitions`);
        retrievedExercises.set(exercise.id, exercise);
      }
    }
    if (story.kind === 'LESSON') {
      const exercises = (await response(api, `lessons/${story.id}/exercises`)).body;
      assert.equal(exercises.lessonId, story.id);
      assert.deepEqual(exercises.exercises, story.exercises ?? []);
      const words = (await response(api, `lessons/${story.id}/vocabulary`)).body;
      assert.equal(words.lessonId, story.id);
      assert.deepEqual(words.vocabulary, story.vocabulary);
    }
  });

  const byKey = items => [...items].sort((a, b) =>
    `${a.language}:${a.word}`.localeCompare(`${b.language}:${b.word}`));
  assert.deepEqual(byKey(retrievedVocabulary.values()), byKey(vocabulary));
  assert.equal(retrievedChapters, stories.reduce((total, story) => total + (story.chapters?.length ?? 1), 0));
  assert.equal(retrievedExercises.size, stories.reduce((total, story) => total + countExercises(story), 0));

  return {
    origin: origin.origin,
    database: health.database,
    course: { nativeLanguage: 'id', targetLanguage: 'fil', difficulty: 'A1' },
    units: stories.length,
    lessons: stories.filter(story => story.kind === 'LESSON').length,
    dialogues: stories.filter(story => story.kind === 'DIALOGUE').length,
    stories: stories.filter(story => story.kind === 'STORY').length,
    chapters: retrievedChapters,
    vocabulary: retrievedVocabulary.size,
    exercises: retrievedExercises.size,
    sourceHash: hash(corpus),
    verifiedAt: new Date().toISOString(),
  };
}

if (direct) {
  const origin = process.argv[2] ?? process.env.ROLANG_API_ORIGIN;
  if (!origin) {
    console.error('Usage: npm run verify:production -- https://your-server.example');
    process.exitCode = 1;
  } else {
    try { console.log(JSON.stringify(await verifyProduction(origin), null, 2)); }
    catch (error) {
      console.error(`Production content verification failed: ${error.message}`);
      process.exitCode = 1;
    }
  }
}
