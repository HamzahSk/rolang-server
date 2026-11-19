export class ApiError extends Error {
  constructor(status, code, message) { super(message); this.status = status; this.code = code; }
}
export const missing = () => new ApiError(404, 'NOT_FOUND', 'The requested resource was not found.');
const connectionCodes = new Set(['ECONNREFUSED', 'ECONNRESET', 'ENOTFOUND', 'EAI_AGAIN', 'ETIMEDOUT',
  'EPIPE', 'ENETUNREACH', 'EHOSTUNREACH', 'CERT_HAS_EXPIRED', 'CERT_NOT_YET_VALID',
  'DEPTH_ZERO_SELF_SIGNED_CERT', 'SELF_SIGNED_CERT_IN_CHAIN', 'UNABLE_TO_VERIFY_LEAF_SIGNATURE',
  'UNABLE_TO_GET_ISSUER_CERT_LOCALLY', 'ERR_TLS_CERT_ALTNAME_INVALID', 'ERR_SSL_WRONG_VERSION_NUMBER']);
const connectionNames = new Set(['MongoServerSelectionError', 'MongoNetworkError', 'MongoNetworkTimeoutError',
  'MongoOperationTimeoutError', 'MongoWaitQueueTimeoutError', 'MongoPoolClearedError', 'MongoTopologyClosedError',
  'MongoNotConnectedError', 'MongoClientClosedError']);
const mongoConnectionCodes = new Set([6, 7, 18, 50, 89, 91, 189, 262, 9001, 11600, 11602, 13435, 13436]);
const mongoSchemaCodes = new Set([13, 26, 48, 67, 72, 85, 86, 263, 303]);
const contentCodes = new Set(['IMPORT_CONFLICT', 'IMPORT_VERIFICATION_FAILED', 'INVALID_DATABASE_VALUE']);
export function failureInfo(error, depth = 0) {
  const code = error?.code;
  if (code === 'DATABASE_NOT_READY' || mongoSchemaCodes.has(code)) return { category: 'database_schema', code };
  if (connectionCodes.has(code) || mongoConnectionCodes.has(code)) return { category: 'database_connection', code };
  if (code === 'MONGODB_CONFIGURATION' || ['MongoParseError', 'MongoInvalidArgumentError'].includes(error?.name))
    return { category: 'database_configuration', code: 'MONGODB_CONFIGURATION' };
  if (connectionNames.has(error?.name)) return { category: 'database_connection', code: error.name };
  if ([2, 9, 14, 20, 27, 65, 11000, 121, 112, 251].includes(code)) return { category: 'database_query', code };
  if (contentCodes.has(code)) return { category: 'database_content', code };
  if (depth < 3) {
    for (const nested of [error?.cause, ...(Array.isArray(error?.errors) ? error.errors : [])]) {
      const info = failureInfo(nested, depth + 1);
      if (info.code !== 'UNKNOWN') return info;
    }
  }
  return { category: 'internal', code: 'UNKNOWN' };
}
export function databaseFailure(error) {
  const { category, code } = failureInfo(error);
  if (category === 'database_configuration') return { code: 'DATABASE_UNAVAILABLE',
    message: 'MongoDB configuration is invalid. Set MONGODB_URI and MONGODB_DB_NAME.' };
  if (category === 'database_connection') return { code: 'DATABASE_UNAVAILABLE',
    message: 'MongoDB is temporarily unavailable. Check connectivity and authentication.' };
  if (category === 'database_schema') return { code: 'DATABASE_NOT_READY',
    message: error instanceof ApiError ? error.message : code === 13
      ? 'MongoDB access was denied. Check collection and index management permissions.'
      : 'MongoDB initialization failed. Check collection definitions and index conflicts.' };
}
export function reportError(error, context) {
  // Only static context and allowlisted codes: driver messages, URLs, stacks,
  // commands and request bodies can contain secrets and must not be serialized.
  console.error(JSON.stringify({ event: 'backend_error', context, ...failureInfo(error) }));
}
