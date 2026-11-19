import { ApiError, reportError, failureInfo } from './errors.js';

export const requiredMigrations = ['001_initial.sql', '002_story_chapters.sql'];

export async function checkSchema(pool) {
  const { rows } = await pool.query('SELECT name FROM schema_migrations WHERE name = ANY($1::text[])', [requiredMigrations]);
  if (requiredMigrations.some(name => !rows.some(row => row.name === name)))
    throw new ApiError(503, 'DATABASE_NOT_READY', 'The database is not ready for this release.');
  // Resolve tables, columns and sequence permissions without reading records,
  // scanning content or advancing sequences. Migration history alone is not
  // enough if the runtime role uses the wrong search_path or permissions.
  await pool.query(`SELECT u.id,u.email,u.password_hash,u.display_name,u.role,
    s.token_hash,s.user_id,s.expires_at,t.id,t.family,t.category,t.difficulty,t.status,t.content,t.vocabulary,t.version,t.updated_at,
    c.story_id,c.id,c.position,c.content,c.vocabulary,c.version,
    r.user_id,r.kind,r.key,r.data,r.deleted,r.revision,r.updated_at,
    o.user_id,o.operation_id,o.fingerprint,a.bucket,a.attempts,a.expires_at,
    d.language,d.word,d.content,i.source_hash,i.metadata
    FROM users u,sessions s,stories t,story_chapters c,learning_records r,sync_operations o,auth_attempts a,dictionary d,corpus_imports i
    LIMIT 0`);
  const { rows: permissions } = await pool.query(`SELECT
    has_sequence_privilege('story_version','USAGE') AND
    has_sequence_privilege('learning_records_revision_seq','USAGE') AND
    bool_and(has_table_privilege(table_name,privilege_name)) AS ready
    FROM (VALUES ('users','INSERT'),('users','UPDATE'),('sessions','INSERT'),('sessions','DELETE'),
      ('stories','INSERT'),('stories','UPDATE'),('stories','DELETE'),('story_chapters','INSERT'),('story_chapters','DELETE'),
      ('learning_records','INSERT'),('learning_records','UPDATE'),('sync_operations','INSERT'),
      ('auth_attempts','INSERT'),('auth_attempts','UPDATE')) AS permissions(table_name,privilege_name)`);
  if (!permissions[0]?.ready) throw new ApiError(503, 'DATABASE_NOT_READY', 'The database is not ready for this release.');
}

export async function healthStatus(pool) {
  let connected = false;
  try {
    await pool.query('SELECT 1');
    connected = true;
    await checkSchema(pool);
    return { status: 'ok', apiVersion: 'v1', database: 'connected' };
  } catch (error) {
    reportError(error, connected ? 'health_schema' : 'health_connection');
    const notReady = connected && failureInfo(error).category === 'database_schema';
    return { status: 'unavailable', apiVersion: 'v1', database: connected ? 'connected' : 'unavailable',
      error: { code: notReady ? 'DATABASE_NOT_READY' : 'DATABASE_UNAVAILABLE',
        message: notReady ? 'The database is not ready for this release.' : 'The database is temporarily unavailable.' } };
  }
}
