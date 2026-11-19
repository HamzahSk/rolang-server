export class ApiError extends Error {
  constructor(status, code, message) { super(message); this.status = status; this.code = code; }
}
export const missing = () => new ApiError(404, 'NOT_FOUND', 'The requested resource was not found.');

const schemaCodes = new Set(['42P01', '42703', '42501', '3F000']);
const connectionCodes = new Set(['ECONNREFUSED', 'ECONNRESET', 'ENOTFOUND', 'EAI_AGAIN',
  'ETIMEDOUT', 'EPIPE', 'ENETUNREACH', 'EHOSTUNREACH', '08000', '08001', '08003', '08004',
  '08006', '08007', '08P01', '28P01', '28000', '3D000', '53300', '53400', '57P01', '57P02', '57P03', '57014',
  'CERT_HAS_EXPIRED', 'CERT_NOT_YET_VALID', 'DEPTH_ZERO_SELF_SIGNED_CERT',
  'SELF_SIGNED_CERT_IN_CHAIN', 'UNABLE_TO_VERIFY_LEAF_SIGNATURE', 'UNABLE_TO_GET_ISSUER_CERT_LOCALLY',
  'ERR_TLS_CERT_ALTNAME_INVALID', 'ERR_SSL_WRONG_VERSION_NUMBER']);
const configurationCodes = new Set(['ERR_INVALID_URL', 'ERR_INVALID_ARG_TYPE']);
const sqlCodes = new Set(['23502', '23503', '23505', '23514', '40001', '40P01', '42601', '42883']);

export function failureInfo(error, depth = 0) {
  const code = error?.code;
  if (schemaCodes.has(code) || code === 'DATABASE_NOT_READY') return { category: 'database_schema', code };
  if (connectionCodes.has(code)) return { category: 'database_connection', code };
  if (configurationCodes.has(code)) return { category: 'database_configuration', code };
  if (sqlCodes.has(code)) return { category: 'database_query', code };
  if (['The server does not support SSL connections',
    'SASL: SCRAM-SERVER-FIRST-MESSAGE: client password must be a string',
    'SASL: SCRAM-SERVER-FIRST-MESSAGE: client password must be a non-empty string'].includes(error?.message))
    return { category: 'database_configuration', code: 'DATABASE_TLS_OR_AUTH_CONFIGURATION' };
  if (depth < 3) {
    for (const nested of [error?.cause, ...(Array.isArray(error?.errors) ? error.errors : [])]) {
      const info = failureInfo(nested, depth + 1);
      if (info.code !== 'UNKNOWN') return info;
    }
  }
  // pg uses plain Errors for these timeouts and disconnected sockets.
  if (['Connection terminated unexpectedly', 'Connection terminated', 'Query read timeout',
    'Connection terminated due to connection timeout', 'timeout exceeded when trying to connect'].includes(error?.message))
    return { category: 'database_connection', code: 'DATABASE_TIMEOUT_OR_DISCONNECT' };
  return { category: 'internal', code: 'UNKNOWN' };
}

export function reportError(error, context) {
  // Only static context and allowlisted codes. Messages, stacks, SQL, URLs and
  // request bodies can contain credentials or user data and must never be logged.
  console.error(JSON.stringify({ event: 'backend_error', context, ...failureInfo(error) }));
}
