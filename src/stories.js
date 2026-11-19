import { createHash } from 'node:crypto';
import { levelFor, normalizeWord } from './validation.js';

export const hash = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
export function chaptersFor(story) {
  if (story.chapters) return story.chapters;
  const fields = ['sentences','speakers','objectives','notes','exercises','focus','pronunciation'];
  return [{ id:'main', title:story.title, summary:story.summary,
    ...Object.fromEntries(fields.filter(k => story[k] !== undefined).map(k => [k,story[k]])) }];
}
export function vocabularyFor(chapter, vocabulary) {
  const keys = new Set();
  for (const code of ['en','id','tl']) {
    for (const sentence of chapter.sentences) for (const token of sentence[code].match(/[\p{L}\p{M}]+(?:['’-][\p{L}\p{M}]+)*/gu) ?? [])
      keys.add(`${code}:${normalizeWord(token)}`);
    for (const word of chapter.focus?.[code] ?? []) keys.add(`${code}:${normalizeWord(word)}`);
  }
  return vocabulary.filter(v => keys.has(`${v.language}:${v.word}`));
}
export async function saveChapters(client, story) {
  await client.query('DELETE FROM story_chapters WHERE story_id=$1', [story.id]);
  for (const [index, chapter] of chaptersFor(story).entries()) {
    const vocabulary = vocabularyFor(chapter, story.vocabulary);
    await client.query(`INSERT INTO story_chapters(story_id,id,position,content,vocabulary,version) VALUES($1,$2,$3,$4,$5,$6)`,
      [story.id,chapter.id,index+1,chapter,JSON.stringify(vocabulary),hash({chapter,vocabulary})]);
  }
}
export function chapterSummary(row) {
  return { id:row.id, order:row.position, title:row.title ?? row.content?.title, summary:row.summary ?? row.content?.summary,
    sentenceCount:row.sentence_count ?? row.content.sentences.length, version:row.version };
}
export const publicStory = (row, includeVocabulary = false) => ({ ...row.content,
  level:levelFor(row.difficulty), status:row.status, version:String(row.version), updatedAt:row.updated_at.toISOString(),
  ...(includeVocabulary ? { vocabulary:row.vocabulary } : {}) });
export function storySummary(row) {
  const s = publicStory(row);
  return { sentenceCount:row.sentence_count, chapterCount:row.chapter_count, ...Object.fromEntries(['id','family','category','difficulty','level','order','kind','image','cover','title','summary','status','version','updatedAt']
    .filter(key => s[key] !== undefined).map(key => [key,s[key]])) };
}
export function conditional(req, res, version) {
  res.set({ ETag:`"${version}"`, 'Cache-Control':'private, no-cache' });
  if (req.get('if-none-match') === `"${version}"`) { res.status(304).end(); return true; }
  return false;
}
