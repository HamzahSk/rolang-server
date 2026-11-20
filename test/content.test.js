import { before, after, test } from 'node:test';
import assert from 'node:assert/strict';
import request from 'supertest';
import { readCorpus, prepareCorpus, importCorpus, verifyCorpus } from '../scripts/import-corpus.js';
import { createApp } from '../src/app.js';
import { mongoFixture } from './helpers.js';

let fixture, store, db, app, corpus, token;
before(async () => {
  fixture = await mongoFixture('content');
  ({ store, db } = fixture);
  corpus = await readCorpus();
  await importCorpus(store, corpus);
  app = createApp(store);
  const account = await request(app).post('/api/v1/auth/register').send({
    email: fixture.name + '@example.test', password: 'test-fixture-password', displayName: 'Content test',
  }).expect(201);
  token = account.body.token;
  await db.collection('users').updateOne({ _id: account.body.user.id }, { $set: { role: 'admin' } });
});
after(async () => { await fixture?.close(); });

test('full legacy corpus import is exact, ordered, atomic, and idempotent',async () => {
  const first = await db.collection('stories').find({}, { projection: { _id: 1, version: 1, updated_at: 1 } }).sort({ _id: 1 }).toArray();
  const learnerRecord = { _id: 'content-test-progress', user_id: 'content-test-user', kind: 'progress',
    key: 'a1_01_sounds:id', data: { completed: true }, deleted: false, revision: 1, updated_at: new Date() };
  await db.collection('learning_records').insertOne(learnerRecord);
  await importCorpus(store,corpus);
  assert.deepEqual(await db.collection('stories').find({}, { projection: { _id: 1, version: 1, updated_at: 1 } }).sort({ _id: 1 }).toArray(),first);
  assert.deepEqual(await db.collection('learning_records').findOne({ _id: learnerRecord._id }), learnerRecord);
  const report = await verifyCorpus(store,corpus);
  assert.deepEqual([report.stories,report.chapters,report.vocabulary,report.exercises],[21,30,1486,150]);
  const changed = structuredClone(corpus);
  changed.stories.at(-1).title.en += ' edited';
  await assert.rejects(importCorpus(store,changed), error => error.code === 'IMPORT_CONFLICT');
  await verifyCorpus(store,corpus);
  assert.equal(await db.collection('corpus_imports').countDocuments(),1);
});

test('paginated catalogs and every stored detail/chapter preserve all learning content',async () => {
  const seen = [];
  let after;
  do {
    const page = await request(app).get('/api/v1/stories').query({limit:3,...(after ? {after} : {})}).expect(200);
    seen.push(...page.body.stories);
    assert.ok(page.body.stories.every(s => !s.sentences && !s.vocabulary && !s.exercises && s.version && s.chapterCount >= 1));
    after = page.body.next;
  } while (after);
  assert.equal(new Set(seen.map(s => s.id)).size,21);
  const {stories} = prepareCorpus(corpus);
  for (const story of stories) {
    const detail = (await request(app).get(`/api/v1/stories/${story.id}`).expect(200)).body;
    for (const key of ['title','summary','sentences','speakers','notes','objectives','focus','pronunciation','exercises','vocabulary']) assert.deepEqual(detail[key],story[key]);
    const content = (await request(app).get(`/api/v1/stories/${story.id}/content`).expect(200)).body;
    assert.deepEqual(content.sentences, story.sentences);
    assert.deepEqual(content.chapters.flatMap(chapter => chapter.sentences), story.sentences);
    assert.deepEqual(content.vocabulary, story.vocabulary);
    const vocabulary = (await request(app).get(`/api/v1/stories/${story.id}/vocabulary`).expect(200)).body;
    assert.deepEqual(vocabulary.vocabulary, story.vocabulary);
    for (const language of ['en', 'id', 'tl']) {
      const translations = (await request(app).get(`/api/v1/stories/${story.id}/translations`).query({ language }).expect(200)).body;
      assert.deepEqual(translations, { language, title: story.title[language], summary: story.summary[language],
        sentences: story.sentences.map(sentence => sentence[language]) });
      const words = (await request(app).get(`/api/v1/stories/${story.id}/vocabulary`).query({ language }).expect(200)).body;
      assert.deepEqual(words.vocabulary, story.vocabulary.filter(word => word.language === language));
    }
    const manifest = (await request(app).get(`/api/v1/stories/${story.id}?view=manifest`).expect(200)).body;
    assert.ok(!manifest.sentences);
    assert.deepEqual(manifest.speakers,story.speakers);
    const chapters = (await request(app).get(`/api/v1/stories/${story.id}/chapters?limit=1`).expect(200)).body;
    assert.equal(chapters.chapters[0].order,1);
    const expectedChapter = story.chapters?.[0] ?? { id: 'main', sentences: story.sentences, exercises: story.exercises };
    const chapter = (await request(app).get(`/api/v1/stories/${story.id}/chapters/${expectedChapter.id}`).expect(200)).body;
    assert.deepEqual(chapter.sentences,expectedChapter.sentences);
    assert.deepEqual(chapter.exercises,expectedChapter.exercises);
    assert.equal(chapter.storyVersion,detail.version);
    await request(app).get(`/api/v1/stories/${story.id}`).set('If-None-Match',`"${detail.version}"`).expect(304);
    await request(app).get(`/api/v1/stories/${story.id}/chapters/${expectedChapter.id}`).set('If-None-Match',`"${chapter.version}"`).expect(304);
  }
});

test('Indonesian-Tagalog curriculum APIs expose ordered modules, lesson practice, and answers', async () => {
  const curriculum = (await request(app).get('/api/v1/curriculum').expect(200)).body;
  assert.equal(curriculum.nativeLanguage, 'id');
  assert.equal(curriculum.targetLanguage, 'tl');
  assert.equal(curriculum.difficulty, 'A1');
  assert.equal(curriculum.unitCount, 21);
  assert.equal(curriculum.lessonCount, 10);
  assert.ok(curriculum.modules.length >= 9);
  const module = (await request(app).get(`/api/v1/curriculum/modules/${curriculum.modules[0].id}`).expect(200)).body;
  assert.ok(module.units.length);
  const lessonId = prepareCorpus(corpus).stories.find(story => story.kind === 'LESSON').id;
  const lesson = (await request(app).get(`/api/v1/lessons/${lessonId}`).expect(200)).body;
  assert.ok(lesson.objectives.length && lesson.notes.length && lesson.exercises.length && lesson.vocabulary.length);
  const exercises = (await request(app).get(`/api/v1/lessons/${lessonId}/exercises`).expect(200)).body.exercises;
  assert.ok(exercises.every(item => item.answer.id && item.explanation.id));
  await request(app).get('/api/v1/lessons/a1_08_family_lunch').expect(404);
});

test('ordered multiple chapters have independent versions and validated content',async () => {
  const original = prepareCorpus(corpus).stories[0];
  const story = { ...original,id:'chapter_test',chapters:[
    {id:'first',title:structuredClone(original.title),sentences:original.sentences.slice(0,2)},
    {id:'second',title:structuredClone(original.title),sentences:original.sentences.slice(2)},
  ] };
  await request(app).post('/api/v1/stories').set('Authorization',`Bearer ${token}`).send(story).expect(201);
  await request(app).post('/api/v1/stories/chapter_test/publish').set('Authorization',`Bearer ${token}`).send({published:true}).expect(200);
  const first = (await request(app).get('/api/v1/stories/chapter_test/chapters?limit=1').expect(200)).body;
  assert.equal(first.next,1);
  const second = (await request(app).get('/api/v1/stories/chapter_test/chapters?after=1&limit=1').expect(200)).body;
  assert.equal(second.chapters[0].id,'second');
  const version = first.version;
  const chapterVersion = second.chapters[0].version;
  story.chapters[0].title.en += ' updated';
  await request(app).put('/api/v1/stories/chapter_test').set('Authorization',`Bearer ${token}`).send(story).expect(200);
  const latest = (await request(app).get('/api/v1/stories/chapter_test/content').expect(200)).body;
  assert.notEqual(latest.version,version);
  assert.equal(latest.chapters[1].version,chapterVersion);
  assert.deepEqual(latest.chapters.flatMap(c => c.sentences),story.sentences);
  await request(app).get('/api/v1/stories/chapter_test/chapters/nope').expect(404);
  await request(app).get('/api/v1/stories/chapter_test/chapters?after=-1').expect(400);
  await request(app).put('/api/v1/stories/chapter_test').set('Authorization',`Bearer ${token}`).send({...story,chapters:[story.chapters[0],story.chapters[0]]}).expect(400);
  await request(app).put('/api/v1/stories/chapter_test').set('Authorization',`Bearer ${token}`).send({...story,vocabulary:[]}).expect(400);
});
