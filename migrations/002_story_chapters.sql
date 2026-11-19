CREATE SEQUENCE story_version;
ALTER TABLE stories ADD COLUMN version BIGINT NOT NULL DEFAULT nextval('story_version');
CREATE TABLE story_chapters (
  story_id TEXT NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
  id TEXT NOT NULL,
  position INTEGER NOT NULL CHECK(position > 0),
  content JSONB NOT NULL,
  vocabulary JSONB NOT NULL,
  version TEXT NOT NULL,
  PRIMARY KEY(story_id,id), UNIQUE(story_id,position)
);
-- Preserve the complete legacy dictionary, including entries outside story text.
CREATE TABLE dictionary (
  language TEXT NOT NULL CHECK(language IN ('en','id','tl')),
  word TEXT NOT NULL, content JSONB NOT NULL, PRIMARY KEY(language,word)
);
CREATE TABLE corpus_imports (
  source_hash TEXT PRIMARY KEY, metadata JSONB NOT NULL,
  imported_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
