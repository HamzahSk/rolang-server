import { z } from 'zod';

export const language = z.enum(['id', 'fil']);
export const difficulty = z.enum(['A1', 'A2', 'B1', 'B2', 'C1', 'C2']);
export const identifier = z.string().regex(/^[a-zA-Z0-9_-]{1,80}$/);
const text = z.string().trim().min(1).max(10_000);
const translated = z.object({ id: text, fil: text }).strict();
const word = z.string().min(1).max(120).regex(/^[\p{L}\p{M}]+(?:['-][\p{L}\p{M}]+)*(?: [\p{L}\p{M}]+(?:['-][\p{L}\p{M}]+)*)*$/u);
export const lexeme = z.object({ language: z.literal('fil'), word, translations: translated, meanings: translated,
  pos: text, notes: translated, pronunciation: z.string().max(1000).optional(),
  practice: z.object({ prompt: translated, choices: z.array(text).min(1).max(100) }).strict().optional() }).strict();
export const levelFor = d => ({ A1: 'BEGINNER', A2: 'BEGINNER', B1: 'INTERMEDIATE',
  B2: 'INTERMEDIATE', C1: 'ADVANCED', C2: 'ADVANCED' })[d];
export const normalizeWord = value => value.toLowerCase().replaceAll('’', "'");
const localizedStrings = z.object({ id: z.array(text).max(500), fil: z.array(text).max(500) }).strict();
const lessonVocabulary = z.object({
  term: word, reading: z.string().trim().min(1).max(1000),
  partOfSpeech: translated, meaning: translated, usage: translated,
}).strict();
const grammarPoint = z.object({
  title: translated, explanation: translated, formula: translated,
  rules: z.array(translated).min(2).max(20), pitfalls: z.array(translated).min(2).max(20),
}).strict();
const exampleGuide = z.object({ pattern: translated, breakdown: translated, tip: translated }).strict();
const exercise = z.object({
  id: identifier, type: z.enum(['MULTIPLE_CHOICE','VOCABULARY_TRANSLATION','FILL_BLANK','GRAMMAR','SENTENCE_CONSTRUCTION','COMPREHENSION']),
  prompt: translated, answer: translated, explanation: translated,
  choices: localizedStrings.optional(), tokens: localizedStrings.optional(),
  speech: z.object({ fil: text }).strict(),
}).strict().superRefine((item, ctx) => {
  for (const code of ['id','fil']) {
    if (['MULTIPLE_CHOICE','GRAMMAR'].includes(item.type) &&
        (!item.choices || item.choices[code].length < 2 || !item.choices[code].includes(item.answer[code])))
      ctx.addIssue({ code:'custom', message:'Choices must include the answer in every language.' });
    if (item.type === 'SENTENCE_CONSTRUCTION' && !item.tokens?.[code]?.length)
      ctx.addIssue({ code:'custom', message:'Sentence construction requires tokens.' });
  }
});
const learningFields = {
  sentences: z.array(translated).min(1).max(300),
  speakers: z.array(z.string().max(100).nullable()).max(300).optional(),
  objectives: z.array(translated).max(100).optional(),
  notes: z.array(z.object({ title: translated, text: translated }).strict()).max(100).optional(),
  exercises: z.array(exercise).max(300).optional(), focus: localizedStrings.optional(),
  pronunciation: z.object({ id:z.string().max(10000), fil:z.string().max(10000) }).strict().optional(),
  context: translated.optional(), lessonVocabulary: z.array(lessonVocabulary).max(100).optional(),
  grammar: z.array(grammarPoint).max(100).optional(), exampleGuides: z.array(exampleGuide).max(300).optional(),
};
export const chapterSchema = z.object({ id: identifier, title: translated, summary: translated.optional(), ...learningFields }).strict();
export const storySchema = z.object({
  id: identifier, family: identifier, category: z.string().trim().min(1).max(100), difficulty,
  level: z.enum(['BEGINNER','INTERMEDIATE','ADVANCED']).optional(),
  order: z.number().int().positive().optional(), kind: z.enum(['LESSON','DIALOGUE','STORY']).optional(),
  image: z.string().max(2000).optional(), cover: z.url().max(2000).optional(),
  title: translated, summary: translated, ...learningFields,
  vocabulary: z.array(lexeme).min(1).max(5000), chapters: z.array(chapterSchema).min(1).max(100).optional(),
}).strict().superRefine((story, ctx) => {
  const keys = new Set();
  for (const item of story.vocabulary) {
    const key = `${item.language}:${normalizeWord(item.word)}`;
    if (keys.has(key) || item.word !== normalizeWord(item.word))
      ctx.addIssue({ code:'custom', path:['vocabulary'], message:'Vocabulary must contain unique normalized words.' });
    keys.add(key);
  }
  const units = [story, ...(story.chapters ?? [])];
  if (story.chapters && new Set(story.chapters.map(c => c.id)).size !== story.chapters.length)
    ctx.addIssue({ code:'custom', path:['chapters'], message:'Chapter IDs must be unique within a story.' });
  // For chaptered stories the legacy text is the ordered concatenation. Old clients keep working.
  if (story.chapters && JSON.stringify(story.sentences) !== JSON.stringify(story.chapters.flatMap(c => c.sentences)))
    ctx.addIssue({ code:'custom', path:['sentences'], message:'Story sentences must match ordered chapter sentences.' });
  const hasStructuredLesson = story.context || story.lessonVocabulary || story.grammar || story.exampleGuides;
  if (story.kind === 'LESSON' && hasStructuredLesson) {
    const requiredPractice = new Set(['MULTIPLE_CHOICE','VOCABULARY_TRANSLATION','FILL_BLANK','GRAMMAR','SENTENCE_CONSTRUCTION']);
    for (const item of story.exercises ?? []) requiredPractice.delete(item.type);
    if (!story.context || (story.objectives?.length ?? 0) < 3 || (story.lessonVocabulary?.length ?? 0) < 3 ||
        (story.grammar?.length ?? 0) < 2 || story.exampleGuides?.length !== story.sentences.length || requiredPractice.size)
      ctx.addIssue({ code:'custom', path:['kind'], message:'Lessons require context, detailed goals, vocabulary, grammar, guided examples, and varied practice.' });
  }
  const definitions = new Map();
  for (const unit of units) {
    for (const exercise of unit.exercises ?? []) {
      const signature = JSON.stringify(exercise);
      if (definitions.has(exercise.id) && definitions.get(exercise.id) !== signature)
        ctx.addIssue({ code:'custom', path:['exercises'], message:'An exercise ID cannot have conflicting definitions across chapters.' });
      definitions.set(exercise.id,signature);
    }
    if (unit.speakers?.length && unit.speakers.length !== unit.sentences.length)
      ctx.addIssue({ code:'custom', path:['speakers'], message:'Speakers must align with sentences.' });
    if (unit.exercises && new Set(unit.exercises.map(e => e.id)).size !== unit.exercises.length)
      ctx.addIssue({ code:'custom', path:['exercises'], message:'Exercise IDs must be unique.' });
    for (const code of ['fil']) {
      for (const sentence of unit.sentences) {
        const tokens = sentence[code].match(/[\p{L}\p{M}]+(?:['’-][\p{L}\p{M}]+)*/gu) ?? [];
        if (tokens.some(token => !keys.has(`${code}:${normalizeWord(token)}`)))
          ctx.addIssue({ code:'custom', path:['vocabulary'], message:`Missing ${code} dictionary coverage.` });
      }
      if (unit.focus?.[code].some(value => !keys.has(`${code}:${normalizeWord(value)}`)))
        ctx.addIssue({ code:'custom', path:['focus'], message:`Missing ${code} focus vocabulary.` });
    }
  }
});
export const registration = z.object({ email: z.email().max(254).transform(s => s.toLowerCase()),
  password: z.string().min(12).max(128), displayName: z.string().trim().min(1).max(100) }).strict();
export const login = registration.pick({ email: true, password: true });
const timestamp = z.number().int().min(0).max(8_640_000_000_000_000);
const nonnegative = z.number().int().min(0).max(1_000_000);
export const progressSchema = z.object({ storyId: identifier, language: z.literal('fil'),
  sentence: z.number().int().min(0).max(299), completed: z.boolean() }).strict();
export const vocabularyStatus = z.enum(['NEW', 'LEARNING', 'ALMOST_MASTERED', 'KNOWN']);
export const legacyVocabularyStatus = v => v.mastered ? 'KNOWN' : v.repetitions >= 3 ? 'ALMOST_MASTERED' : 'LEARNING';
export const vocabularySchema = z.object({
  language: z.literal('fil'), reference: z.literal('id'), word, translation: text, meaning: text, partOfSpeech: text,
  explanation: text, example: text, exampleTranslation: text, storyId: identifier,
  storyTitle: text, category: z.string().min(1).max(100), createdAt: timestamp, dueAt: timestamp,
  repetitions: nonnegative, intervalDays: z.number().int().min(0).max(365),
  ease: z.number().min(1.3).max(100), lapses: nonnegative, mastered: z.boolean(), lastReviewedAt: timestamp,
  status: vocabularyStatus.optional(), statusChangedAt: timestamp.optional(),
}).strict().refine(v => v.word === normalizeWord(v.word), { message: 'Use normalized vocabulary words.' })
  .refine(v => v.status === undefined || (v.status === 'KNOWN') === v.mastered,
    { message: 'Known status and mastered must agree.' })
  .transform(v => ({ ...v, status: v.status ?? legacyVocabularyStatus(v), statusChangedAt: v.statusChangedAt ?? 0 }));
export const reviewSchema = z.object({ vocabularyKey: z.string().min(1).max(512), language: z.literal('fil'),
  reference: z.literal('id'), reviewedAt: timestamp, correct: z.boolean(),
  rating: z.enum(['AGAIN', 'HARD', 'GOOD', 'EASY']) }).strict();
export const profileSchema = z.object({ target: z.literal('fil'), native: z.literal('id'),
  level: z.literal('BEGINNER'), fontSize: z.number().min(16).max(28),
  dark: z.boolean() }).strict();
export const kinds = z.enum(['progress', 'vocabulary', 'review', 'profile']);
export const keyFor = (kind, data) => kind === 'progress' ? `${data.storyId}:${data.language}`
  : kind === 'vocabulary' ? `${data.language}:${data.reference}:${data.storyId}:${data.word}` : 'preferences';
export const schemas = { progress: progressSchema, vocabulary: vocabularySchema, review: reviewSchema, profile: profileSchema };
export const operationSchema = z.object({ id: z.uuid(), kind: kinds,
  key: z.string().min(1).max(512), deleted: z.boolean(), data: z.unknown() }).strict().superRefine((op, ctx) => {
  const validKey = op.kind === 'progress' ? /^[a-zA-Z0-9_-]{1,80}:fil$/.test(op.key)
    : op.kind === 'vocabulary' ? /^fil:id:[a-zA-Z0-9_-]{1,80}:[\p{L}\p{M}]+(?:['-][\p{L}\p{M}]+)*(?: [\p{L}\p{M}]+(?:['-][\p{L}\p{M}]+)*)*$/u.test(op.key)
    : op.kind === 'profile' ? op.key === 'preferences' : z.uuid().safeParse(op.key).success;
  if (!validKey) ctx.addIssue({ code: 'custom', path: ['key'], message: 'Invalid learning record key.' });
  if (op.kind === 'review' && !z.uuid().safeParse(op.key).success) {
    ctx.addIssue({ code: 'custom', path: ['key'], message: 'Review key must be a UUID.' });
  }
  if (op.deleted) {
    if (op.data !== null) ctx.addIssue({ code: 'custom', path: ['data'], message: 'Tombstone data must be null.' });
    return;
  }
  const parsed = schemas[op.kind].safeParse(op.data);
  if (!parsed.success) {
    ctx.addIssue({ code: 'custom', path: ['data'], message: 'Invalid learning record.' });
  } else if (op.kind !== 'review' && keyFor(op.kind, parsed.data) !== op.key) {
    ctx.addIssue({ code: 'custom', path: ['key'], message: 'Key does not match learning record.' });
  }
});
export const syncSchema = z.object({ cursor: z.number().int().min(0).max(Number.MAX_SAFE_INTEGER),
  operations: z.array(operationSchema).max(100) }).strict();
export const catalogQuery = z.object({ language: language.optional(), category: z.string().max(100).optional(),
  search: z.string().trim().min(1).max(200).optional(), q: z.string().trim().min(1).max(200).optional(),
  difficulty: difficulty.optional(), limit: z.coerce.number().int().min(1).max(100).default(30),
  after: identifier.optional() }).strict();
