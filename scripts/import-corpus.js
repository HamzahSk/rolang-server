import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { isDeepStrictEqual } from 'node:util';
import { z } from 'zod';
import { database, transaction } from '../src/db.js';
import { reportError } from '../src/errors.js';
import { storySchema, lexeme, normalizeWord } from '../src/validation.js';
import { saveChapters, hash } from '../src/stories.js';

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
      else if (value && typeof value === 'object') for (const [key,v] of Object.entries(value)) visit(v,['en','id','tl'].includes(key) ? key : code);
    }
    visit(unit);
    const difficulty = { BEGINNER:'A1', INTERMEDIATE:'B1', ADVANCED:'C1' }[unit.level];
    return storySchema.parse({ ...unit, difficulty, vocabulary:vocabulary.filter(w => used.has(`${w.language}:${w.word}`)) });
  });
  if (!stories.length || new Set(stories.map(s => s.id)).size !== stories.length) throw new Error('Empty corpus or duplicate story IDs.');
  return { stories,vocabulary };
}
export async function verifyCorpus(pool,corpus) {
  const { stories,vocabulary } = prepareCorpus(corpus);
  for (const story of stories) {
    const { rows } = await pool.query('SELECT content,vocabulary,status FROM stories WHERE id=$1',[story.id]);
    const { vocabulary:words,...content } = story;
    if (!rows.length || !isDeepStrictEqual(rows[0].content,content) || !isDeepStrictEqual(rows[0].vocabulary,words) || rows[0].status !== 'published')
      throw new Error(`Story verification failed: ${story.id}`);
    const chapters = await pool.query('SELECT content FROM story_chapters WHERE story_id=$1 ORDER BY position',[story.id]);
    if (!chapters.rows.length || !isDeepStrictEqual(chapters.rows.flatMap(r => r.content.sentences),story.sentences))
      throw new Error(`Chapter verification failed: ${story.id}`);
  }
  for (const word of vocabulary) {
    const { rows } = await pool.query('SELECT content FROM dictionary WHERE language=$1 AND word=$2',[word.language,word.word]);
    if (!rows.length || !isDeepStrictEqual(rows[0].content,word)) throw new Error(`Dictionary verification failed: ${word.language}:${word.word}`);
  }
  return { stories:stories.length, chapters:stories.reduce((n,s) => n+(s.chapters?.length ?? 1),0),
    vocabulary:vocabulary.length, exercises:stories.reduce((n,s) => n+(s.exercises?.length ?? 0),0), sourceHash:hash(corpus) };
}
export async function importCorpus(pool,corpus,{ replaceExisting = false } = {}) {
  const { stories,vocabulary } = prepareCorpus(corpus);
  return transaction(pool, async client => {
    await client.query('SELECT pg_advisory_xact_lock(78201343)');
    for (const story of stories) {
      const { vocabulary:words,...content } = story;
      const previous = await client.query('SELECT content,vocabulary FROM stories WHERE id=$1 FOR UPDATE',[story.id]);
      const same = previous.rows.length && isDeepStrictEqual(previous.rows[0].content,content) && isDeepStrictEqual(previous.rows[0].vocabulary,words);
      if (previous.rows.length && !same && !replaceExisting) throw new Error(`Conflicting story ${story.id}; review it, then use --replace-existing if intentional.`);
      if (!previous.rows.length) await client.query(`INSERT INTO stories(id,family,category,difficulty,status,content,vocabulary)
        VALUES($1,$2,$3,$4,'published',$5,$6)`,[story.id,story.family,story.category,story.difficulty,content,JSON.stringify(words)]);
      else if (!same) await client.query(`UPDATE stories SET family=$2,category=$3,difficulty=$4,status='published',content=$5,vocabulary=$6,
        updated_at=clock_timestamp(),version=nextval('story_version') WHERE id=$1`,[story.id,story.family,story.category,story.difficulty,content,JSON.stringify(words)]);
      await saveChapters(client,story);
    }
    for (const word of vocabulary) {
      const old = await client.query('SELECT content FROM dictionary WHERE language=$1 AND word=$2',[word.language,word.word]);
      if (old.rows.length && !isDeepStrictEqual(old.rows[0].content,word) && !replaceExisting) throw new Error(`Conflicting dictionary entry ${word.language}:${word.word}`);
      await client.query(`INSERT INTO dictionary(language,word,content) VALUES($1,$2,$3)
        ON CONFLICT(language,word) DO UPDATE SET content=excluded.content`,[word.language,word.word,word]);
    }
    const report = await verifyCorpus(client,corpus);
    await client.query('INSERT INTO corpus_imports(source_hash,metadata) VALUES($1,$2) ON CONFLICT DO NOTHING',
      [report.sourceHash,{ ...report,version:corpus.version,course:corpus.course }]);
    return report;
  });
}
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  const pool = database();
  try {
    const corpus = await readCorpus(args.find(a => !a.startsWith('--')));
    const report = args.includes('--verify') ? await verifyCorpus(pool,corpus)
      : await importCorpus(pool,corpus,{replaceExisting:args.includes('--replace-existing')});
    console.log(JSON.stringify(report,null,2));
  } catch (error) {
    reportError(error, 'corpus_import');
    console.error('Corpus import/verification failed. Check migrations, content validity, and existing-content conflicts before retrying.');
    process.exitCode=1;
  }
  finally { await pool.end(); }
}
