import express from 'express';
import { z, ZodError } from 'zod';
import { database, transaction, mongoOptions } from './db.js';
import { ApiError, missing, databaseFailure, reportError } from './errors.js';
import { serverConfig } from './config.js';
import { healthStatus } from './health.js';
import { authentication, administrator, hashPassword, verifyPassword, session, rateLimit, randomUUID } from './auth.js';
import { storySchema, registration, login, catalogQuery, identifier,
  language, schemas, syncSchema, operationSchema } from './validation.js';
import { synchronize, lockUser, putRecord, record } from './learning.js';
import { publicStory, storySummary, saveStory, chapterSummary, chapterRows, loadVocabulary, conditional } from './stories.js';
import { nextStoryVersion } from './documents.js';

const clientIp = req => serverConfig().vercel
  ? (req.get('x-vercel-forwarded-for')?.split(',')[0].trim() || req.ip || 'unknown')
  : (req.ip || 'unknown');

export function createApp(store = database()) {
  const app = express();
  app.disable('x-powered-by');
  app.use((req, res, next) => {
    res.set({ 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
    const origin = req.get('origin');
    if (origin && serverConfig().corsOrigins.includes(origin)) {
      res.set({ 'Access-Control-Allow-Origin': origin, Vary: 'Origin',
        'Access-Control-Allow-Headers': 'Authorization, Content-Type, If-None-Match',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS' });
    }
    if (req.method === 'OPTIONS') return res.sendStatus(204);
    next();
  });
  app.use(express.json({ limit: '2mb', strict: true }));
  const api = express.Router();
  const auth = authentication(store);
  const health = async (_req, res) => {
    const status = await healthStatus(store);
    res.status(status.status === 'ok' ? 200 : 503).json(status);
  };
  app.get('/health', health);
  api.get('/health', health);
  api.post('/auth/register', async (req, res) => {
    const input = registration.parse(req.body);
    await rateLimit(store, input.email, clientIp(req));
    const passwordHash = await hashPassword(input.password);
    const result = await transaction(store, async scope => {
      const user = { _id: randomUUID(), email: input.email, password_hash: passwordHash,
        display_name: input.displayName, role: 'learner', created_at: new Date(), learning_revision: 0 };
      await scope.db.collection('users').insertOne(user, mongoOptions(scope));
      return session(scope, user);
    });
    res.status(201).json(result);
  });
  api.post('/auth/login', async (req, res) => {
    const input = login.parse(req.body);
    await rateLimit(store, input.email, clientIp(req));
    const { db } = await store.scope();
    const user = await db.collection('users').findOne({ email: input.email });
    const valid = await verifyPassword(input.password, user?.password_hash ?? 'scrypt:' + '0'.repeat(32) + ':' + '0'.repeat(128));
    if (!user || !valid) throw new ApiError(401, 'INVALID_CREDENTIALS', 'Email or password is incorrect.');
    res.json(await session({ db }, user));
  });
  api.post('/auth/logout', auth, async (req, res) => {
    const { db } = await store.scope();
    await db.collection('sessions').deleteOne({ _id: req.tokenHash });
    res.sendStatus(204);
  });
  api.get('/me', auth, async (req, res) => {
    res.json({ id: req.user.id, email: req.user.email, displayName: req.user.display_name, role: req.user.role });
  });
  api.put('/me', auth, async (req, res) => {
    const input = z.object({ displayName: z.string().trim().min(1).max(100) }).strict().parse(req.body);
    const { db } = await store.scope();
    await db.collection('users').updateOne({ _id: req.user.id }, { $set: { display_name: input.displayName } });
    res.json({ id: req.user.id, displayName: input.displayName });
  });
  const moduleTitles = {
    foundations: 'Dasar bahasa', greetings: 'Salam dan perkenalan', time: 'Angka dan waktu',
    routine: 'Kegiatan sehari-hari', family: 'Keluarga dan hubungan', school: 'Sekolah',
    grammar: 'Tata bahasa dan kegiatan', food: 'Makanan dan belanja', travel: 'Tempat dan arah',
    friends: 'Persahabatan', review: 'Tinjauan akhir A1',
  };
  async function curriculumRows() {
    const { db } = await store.scope();
    return db.collection('stories').find({ status: 'published', difficulty: 'A1' }).sort({ 'content.order': 1, _id: 1 }).toArray();
  }
  function curriculumModules(rows) {
    const grouped = new Map();
    for (const row of rows) {
      const module = grouped.get(row.family) ?? { id: row.family, title: moduleTitles[row.family] ?? row.family,
        order: row.content.order, unitCount: 0, lessonCount: 0, storyCount: 0 };
      module.order = Math.min(module.order, row.content.order);
      module.unitCount++;
      if (row.content.kind === 'LESSON') module.lessonCount++;
      else module.storyCount++;
      grouped.set(row.family, module);
    }
    return [...grouped.values()].sort((a, b) => a.order - b.order || a.id.localeCompare(b.id));
  }
  api.get('/curriculum', async (_req, res) => {
    const rows = await curriculumRows();
    res.json({ id: 'id-tl-a1', nativeLanguage: 'id', targetLanguage: 'tl', difficulty: 'A1', level: 'BEGINNER',
      title: 'Tagalog A1 untuk penutur bahasa Indonesia', unitCount: rows.length,
      lessonCount: rows.filter(row => row.content.kind === 'LESSON').length,
      storyCount: rows.filter(row => row.content.kind === 'STORY').length,
      modules: curriculumModules(rows) });
  });
  api.get('/curriculum/modules', async (_req, res) => {
    const rows = await curriculumRows();
    res.json({ curriculumId: 'id-tl-a1', modules: curriculumModules(rows) });
  });
  api.get('/curriculum/modules/:id', async (req, res) => {
    const id = identifier.parse(req.params.id);
    const rows = (await curriculumRows()).filter(row => row.family === id);
    if (!rows.length) throw missing();
    res.json({ curriculumId: 'id-tl-a1', module: curriculumModules(rows)[0], units: rows.map(storySummary) });
  });
  api.get('/stories', async (req, res) => {
    const query = catalogQuery.parse(req.query);
    const filter = { status: 'published',
      ...(query.language ? { languages: query.language } : {}),
      ...(query.category !== undefined ? { category: query.category } : {}),
      ...(query.difficulty ? { difficulty: query.difficulty } : {}),
      ...(query.after ? { _id: { $gt: query.after } } : {}),
      ...((query.search || query.q) ? { $text: { $search: query.search || query.q, $language: 'none' } } : {}),
    };
    const { db } = await store.scope();
    const rows = await db.collection('stories').find(filter, { projection: {
      'content.sentences': 0, 'content.vocabulary': 0, 'content.chapters': 0, 'content.speakers': 0,
      'content.objectives': 0, 'content.notes': 0, 'content.exercises': 0, 'content.focus': 0, 'content.pronunciation': 0,
    } }).sort({ _id: 1 }).limit(query.limit + 1).toArray();
    const items = rows.slice(0, query.limit);
    res.json({ stories: items.map(storySummary), next: rows.length > query.limit ? items.at(-1)._id : null });
  });
  async function publishedStory(scope, req) {
    const id = identifier.parse(req.params.id);
    const row = await scope.db.collection('stories').findOne({ _id: id, status: 'published' }, mongoOptions(scope));
    if (!row) throw missing();
    return row;
  }
  // Multi-collection reads use one snapshot so a chapter can never be labelled
  // with an earlier story version during a concurrent editorial update.
  async function readPublished(req, action) {
    identifier.parse(req.params.id);
    return transaction(store, async scope => action(scope, await publishedStory(scope, req)));
  }
  api.get('/stories/:id', async (req, res) => {
    const query = z.object({ view: z.enum(['manifest', 'full']).default('full') }).strict().parse(req.query);
    const body = await readPublished(req, async (scope, row) => {
      row.vocabulary = await loadVocabulary(scope, row._id);
      const detail = publicStory(row, true);
      if (query.view === 'manifest') delete detail.sentences;
      return { ...detail, sentenceCount: row.sentence_count, chapters: (await chapterRows(scope, row, true)).map(chapterSummary) };
    });
    if (!conditional(req, res, body.version)) res.json(body);
  });
  api.get('/stories/:id/chapters', async (req, res) => {
    const query = z.object({ limit: z.coerce.number().int().min(1).max(100).default(30),
      after: z.coerce.number().int().min(0).max(Number.MAX_SAFE_INTEGER).default(0) }).strict().parse(req.query);
    const body = await readPublished(req, async (scope, row) => {
      const rows = (await chapterRows(scope, row, true)).filter(chapter => chapter.position > query.after);
      const items = rows.slice(0, query.limit);
      return { storyId: row._id, version: String(row.version), chapters: items.map(chapterSummary),
        next: rows.length > query.limit ? items.at(-1).position : null };
    });
    res.json(body);
  });
  api.get('/stories/:id/chapters/:chapterId', async (req, res) => {
    const id = identifier.parse(req.params.chapterId);
    const body = await readPublished(req, async (scope, row) => {
      let chapter = await scope.db.collection('story_chapters').findOne({ story_id: row._id, id }, mongoOptions(scope));
      if (!chapter) chapter = (await chapterRows(scope, row)).find(item => item.id === id);
      if (!chapter) throw missing();
      return { ...chapter.content, storyId: row._id, order: chapter.position, version: chapter.version,
        storyVersion: String(row.version), vocabulary: chapter.vocabulary };
    });
    if (!conditional(req, res, body.version)) res.json(body);
  });
  api.get('/stories/:id/content', async (req, res) => {
    const body = await readPublished(req, async (scope, row) => {
      row.vocabulary = await loadVocabulary(scope, row._id);
      return { ...publicStory(row, true), chapters: (await chapterRows(scope, row)).map(chapter => ({
        ...chapter.content, order: chapter.position, version: chapter.version, vocabulary: chapter.vocabulary,
      })) };
    });
    if (!conditional(req, res, body.version)) res.json(body);
  });
  api.get('/stories/:id/translations', async (req, res) => {
    const code = language.parse(req.query.language);
    res.json(await readPublished(req, async (_scope, row) => ({
      language: code, title: row.content.title[code], summary: row.content.summary[code],
      sentences: row.content.sentences.map(sentence => sentence[code]),
    })));
  });
  api.get('/stories/:id/vocabulary', async (req, res) => {
    const code = language.optional().parse(req.query.language);
    res.json(await readPublished(req, async (scope, row) => ({ vocabulary: await loadVocabulary(scope, row._id, code) })));
  });
  async function readLesson(req, action) {
    return readPublished(req, async (scope, row) => {
      if (row.content.kind !== 'LESSON') throw missing();
      return action(scope, row);
    });
  }
  api.get('/lessons/:id', async (req, res) => {
    const body = await readLesson(req, async (scope, row) => {
      row.vocabulary = await loadVocabulary(scope, row._id);
      return { ...publicStory(row, true), chapters: (await chapterRows(scope, row, true)).map(chapterSummary) };
    });
    if (!conditional(req, res, body.version)) res.json(body);
  });
  api.get('/lessons/:id/vocabulary', async (req, res) => {
    const code = language.optional().parse(req.query.language);
    res.json(await readLesson(req, async (scope, row) => ({ lessonId: row._id,
      vocabulary: await loadVocabulary(scope, row._id, code) })));
  });
  api.get('/lessons/:id/exercises', async (req, res) => {
    res.json(await readLesson(req, async (_scope, row) => ({ lessonId: row._id,
      exercises: row.content.exercises ?? [] })));
  });
  api.get('/admin/stories', auth, administrator, async (req, res) => {
    const { limit, after } = catalogQuery.pick({ limit: true, after: true }).parse(req.query);
    const body = await transaction(store, async scope => {
      const rows = await scope.db.collection('stories').find(after ? { _id: { $gt: after } } : {}, mongoOptions(scope))
        .sort({ _id: 1 }).limit(limit + 1).toArray();
      const items = rows.slice(0, limit);
      for (const row of items) row.vocabulary = await loadVocabulary(scope, row._id);
      return { stories: items.map(row => publicStory(row, true)), next: rows.length > limit ? items.at(-1)._id : null };
    });
    res.json(body);
  });
  api.post('/stories', auth, administrator, async (req, res) => {
    const story = storySchema.parse(req.body);
    const row = await transaction(store, scope => saveStory(scope, story));
    res.status(201).json(publicStory(row, true));
  });
  api.put('/stories/:id', auth, administrator, async (req, res) => {
    const story = storySchema.parse(req.body);
    if (identifier.parse(req.params.id) !== story.id) throw new ApiError(400, 'INVALID_ID', 'Story ID cannot change.');
    const row = await transaction(store, async scope => {
      const previous = await scope.db.collection('stories').findOne({ _id: story.id }, mongoOptions(scope));
      if (!previous) throw missing();
      return saveStory(scope, story, { previous });
    });
    res.json(publicStory(row, true));
  });
  api.post('/stories/:id/publish', auth, administrator, async (req, res) => {
    const { published } = z.object({ published: z.boolean() }).strict().parse(req.body);
    const id = identifier.parse(req.params.id);
    const row = await transaction(store, async scope => {
      const previous = await scope.db.collection('stories').findOne({ _id: id }, mongoOptions(scope));
      if (!previous) throw missing();
      const version = await nextStoryVersion(scope);
      const updated = await scope.db.collection('stories').findOneAndUpdate({ _id: id }, {
        $set: { status: published ? 'published' : 'draft', updated_at: new Date(), version },
      }, { ...mongoOptions(scope), returnDocument: 'after' });
      return { ...updated, vocabulary: await loadVocabulary(scope, id) };
    });
    res.json(publicStory(row, true));
  });
  api.delete('/stories/:id', auth, administrator, async (req, res) => {
    const id = identifier.parse(req.params.id);
    await transaction(store, async scope => {
      if (!(await scope.db.collection('stories').deleteOne({ _id: id }, mongoOptions(scope))).deletedCount) throw missing();
      await scope.db.collection('story_chapters').deleteMany({ story_id: id }, mongoOptions(scope));
      await scope.db.collection('story_vocabulary').deleteMany({ story_id: id }, mongoOptions(scope));
    });
    res.sendStatus(204);
  });
  api.post('/me/sync', auth, async (req, res) => res.json(await synchronize(store, req.user.id, syncSchema.parse(req.body))));
  for (const [path, kind] of [['progress', 'progress'], ['vocabulary', 'vocabulary'], ['reviews', 'review'], ['preferences', 'profile'], ['history', 'progress']]) {
    api.get('/me/' + path, auth, async (req, res) => {
      const query = z.object({ after: z.string().max(512).optional(),
        limit: z.coerce.number().int().min(1).max(500).default(100) }).strict().parse(req.query);
      const { db } = await store.scope();
      const rows = await db.collection('learning_records').find({ user_id: req.user.id, kind, deleted: false,
        ...(query.after ? { key: { $gt: query.after } } : {}) }).sort({ key: 1 }).limit(query.limit + 1).toArray();
      const items = rows.slice(0, query.limit).map(record);
      res.json({ records: items, next: rows.length > query.limit ? items.at(-1).key : null });
    });
    if (path === 'history') continue;
    api.put('/me/' + path + '/:key', auth, async (req, res) => {
      const data = schemas[kind].parse(req.body);
      const key = z.string().min(1).max(512).parse(req.params.key);
      operationSchema.parse({ id: randomUUID(), kind, key, data, deleted: false });
      res.json(await transaction(store, async scope => {
        await lockUser(scope, req.user.id);
        return putRecord(scope, req.user.id, kind, key, data);
      }));
    });
    api.delete('/me/' + path + '/:key', auth, async (req, res) => {
      const key = z.string().min(1).max(512).parse(req.params.key);
      operationSchema.parse({ id: randomUUID(), kind, key, data: null, deleted: true });
      await transaction(store, async scope => {
        await lockUser(scope, req.user.id);
        await putRecord(scope, req.user.id, kind, key, null, true);
      });
      res.sendStatus(204);
    });
  }
  app.use('/api/v1', api);
  app.use((_req, _res, next) => next(missing()));
  app.use((error, _req, res, _next) => {
    if (error instanceof ZodError) return res.status(400).json({ error: { code: 'VALIDATION_ERROR',
      message: 'Request validation failed.', fields: error.issues.map(issue => ({ path: issue.path.join('.'), message: issue.message })) } });
    if (error instanceof ApiError) return res.status(error.status).json({ error: { code: error.code, message: error.message } });
    if (error.type === 'entity.parse.failed') return res.status(400).json({ error: { code: 'INVALID_JSON', message: 'Send a valid JSON object.' } });
    if (error.type === 'entity.too.large') return res.status(413).json({ error: { code: 'BODY_TOO_LARGE', message: 'Request body exceeds 2 MB.' } });
    if (error.code === 11000) return res.status(409).json({ error: { code: 'ALREADY_EXISTS', message: 'This resource already exists.' } });
    reportError(error, 'request');
    const databaseError = databaseFailure(error);
    if (databaseError) return res.status(503).json({ error: databaseError });
    res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: 'An unexpected server error occurred.' } });
  });
  return app;
}
