import { randomUUID, randomBytes, createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { postgresDatabase } from '../scripts/postgres/db.js';
import { migratePostgres } from '../scripts/postgres/migrate.js';
import { readCorpus, prepareCorpus } from '../scripts/import-corpus.js';
import { chapterDocuments, hash } from '../src/stories.js';
import { hashPassword } from '../src/auth.js';

export async function postgresFixture({ legacyOnly = false } = {}) {
  if (!process.env.TEST_POSTGRES_URL) throw new Error('Set TEST_POSTGRES_URL to a disposable PostgreSQL database. See compose.test.yml.');
  const schema = 'rolang_source_' + randomUUID().replaceAll('-', '');
  const env = { DATABASE_URL: process.env.TEST_POSTGRES_URL };
  const base = postgresDatabase(env);
  await base.query('CREATE SCHEMA ' + schema);
  const pool = postgresDatabase(env, { options: '-c search_path=' + schema });
  const corpus = await readCorpus();
  const { stories, vocabulary } = prepareCorpus(corpus);
  const userId = randomUUID();
  const otherId = randomUUID();
  const token = randomBytes(32).toString('base64url');
  const email = 'source.' + userId + '@example.test';
  const password = 'retained-test-password';
  const operation = { id: randomUUID(), kind: 'progress', key: stories[0].id + ':en', deleted: false,
    data: { storyId: stories[0].id, language: 'en', sentence: 1, completed: true } };
  try {
    if (legacyOnly) {
      await pool.query(await readFile(new URL('../migrations/001_initial.sql', import.meta.url), 'utf8'));
      await pool.query('CREATE TABLE schema_migrations(name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())');
      await pool.query("INSERT INTO schema_migrations(name) VALUES('001_initial.sql')");
    } else { await migratePostgres(pool); await migratePostgres(pool); }
    await pool.query('ALTER TABLE users ADD COLUMN legacy_flags JSONB');
    const passwordHash = await hashPassword(password);
    await pool.query("INSERT INTO users(id,email,password_hash,display_name,role,legacy_flags) VALUES($1,$2,$3,'Source learner','learner',$4),($5,$6,$3,'Source admin','admin',$4)",
      [userId, email, passwordHash, { retained: true }, otherId, 'admin.' + otherId + '@example.test']);
    const digest = value => createHash('sha256').update(value).digest('hex');
    await pool.query("INSERT INTO sessions(token_hash,user_id,expires_at) VALUES($1,$2,now()+interval '30 days'),($3,$2,now()-interval '1 day')",
      [digest(token), userId, digest('expired-session')]);
    for (const [index, original] of stories.entries()) {
      const story = structuredClone(original);
      if (!legacyOnly && index === 0) {
        const split = Math.floor(story.sentences.length / 2);
        story.chapters = [
          { id: 'opening', title: story.title, sentences: story.sentences.slice(0, split) },
          { id: 'ending', title: story.title, sentences: story.sentences.slice(split) },
        ];
      }
      const { vocabulary: words, ...content } = story;
      if (index === 0) content.legacyMetadata = { retained: ['all', 'fields'], custom: { revision: 7 } };
      await pool.query('INSERT INTO stories(id,family,category,difficulty,status,content,vocabulary) VALUES($1,$2,$3,$4,$5,$6,$7)',
        [story.id, story.family, story.category, story.difficulty, index === stories.length - 1 ? 'draft' : 'published', content, JSON.stringify(words)]);
      if (!legacyOnly) for (const chapter of chapterDocuments(story)) {
        await pool.query('INSERT INTO story_chapters(story_id,id,position,content,vocabulary,version) VALUES($1,$2,$3,$4,$5,$6)',
          [story.id, chapter.id, chapter.position, chapter.content, JSON.stringify(chapter.vocabulary), chapter.version]);
      }
    }
    if (!legacyOnly) {
      await pool.query('UPDATE stories SET version=$2 WHERE id=$1', [stories[0].id, '9007199254740993']);
      const entries = vocabulary.map(word => ({ language: word.language, word: word.word, content: word }));
      await pool.query('INSERT INTO dictionary(language,word,content) SELECT language,word,content FROM jsonb_to_recordset($1) AS rows(language TEXT,word TEXT,content JSONB)', [JSON.stringify(entries)]);
      await pool.query('INSERT INTO corpus_imports(source_hash,metadata) VALUES($1,$2)', [hash(corpus), {
        version: corpus.version, course: corpus.course, stories: stories.length, vocabulary: vocabulary.length,
      }]);
    }
    const vocabularyKey = 'en:id:market_beginner:maya';
    const word = { language: 'en', reference: 'id', word: 'maya', translation: 'Maya', meaning: 'Name',
      partOfSpeech: 'proper noun', explanation: 'Name', example: 'Maya walks.', exampleTranslation: 'Maya berjalan.',
      storyId: 'market_beginner', storyTitle: 'Market', category: 'Everyday life', createdAt: 1000, dueAt: 2000,
      repetitions: 3, intervalDays: 1, ease: 2.5, lapses: 0, mastered: false, lastReviewedAt: 1000 };
    for (const row of [
      ['progress', operation.key, operation.data, false, 100],
      ['vocabulary', vocabularyKey, word, false, 250],
      ['review', randomUUID(), null, true, 600],
      ['profile', 'preferences', { target: 'tl', native: 'en', level: 'ADVANCED', fontSize: 24, dark: true }, false, 901],
    ]) await pool.query('INSERT INTO learning_records(user_id,kind,key,data,deleted,revision) VALUES($1,$2,$3,$4,$5,$6)', [userId, ...row]);
    await pool.query('INSERT INTO sync_operations(user_id,operation_id,fingerprint) VALUES($1,$2,$3)',
      [userId, operation.id, hash(operation)]);
    await pool.query("INSERT INTO auth_attempts(bucket,attempts,expires_at) VALUES('retained-active',2,now()+interval '15 minutes'),('retained-expired',3,now()-interval '1 day')");
    const rows = (await pool.query('SELECT * FROM stories ORDER BY id')).rows;
    const users = (await pool.query('SELECT * FROM users ORDER BY id')).rows;
    return { schema, base, pool, corpus, stories, rows, users, userId, otherId, token, email, password, operation,
      async close() {
        await pool.end();
        try {
          if (!schema.startsWith('rolang_source_')) throw new Error('Refusing to drop a non-test schema.');
          await base.query('DROP SCHEMA ' + schema + ' CASCADE');
        } finally { await base.end(); }
      } };
  } catch (error) {
    await pool.end();
    await base.query('DROP SCHEMA ' + schema + ' CASCADE');
    await base.end();
    throw error;
  }
}
