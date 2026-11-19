// Node loads .env only with --env-file; Vercel injects these same process variables.
export class DatabaseConfigurationError extends Error {
  constructor() {
    super('Set valid MONGODB_URI and MONGODB_DB_NAME environment variables.');
    this.code = 'MONGODB_CONFIGURATION';
  }
}
const integer = (value, fallback, min, max) => {
  const number = Number(value);
  return value && Number.isFinite(number) ? Math.max(min, Math.min(max, Math.floor(number))) : fallback;
};
export function mongodbConfig(env = process.env) {
  const uri = env.MONGODB_URI?.trim();
  const name = env.MONGODB_DB_NAME?.trim();
  if (!uri || !/^mongodb(?:\+srv)?:\/\//.test(uri) || !name ||
      Buffer.byteLength(name) > 63 || /[\/\\. "\0$*<>:|?]/.test(name)) throw new DatabaseConfigurationError();
  return {
    uri, name,
    options: {
      appName: 'rolang-server',
      maxPoolSize: 5,
      minPoolSize: 0,
      maxConnecting: 2,
      maxIdleTimeMS: 60_000,
      serverSelectionTimeoutMS: 5_000,
      connectTimeoutMS: 5_000,
      waitQueueTimeoutMS: 5_000,
      socketTimeoutMS: 15_000,
      // Driver 6.21 implements client-side operation and transaction deadlines.
      // Keep it pinned: newer releases currently ignore this option.
      timeoutMS: 15_000,
      retryReads: true,
      retryWrites: true,
    },
  };
}
export function serverConfig(env = process.env) {
  return {
    sessionDays: integer(env.SESSION_DAYS, 30, 1, 90),
    corsOrigins: (env.CORS_ORIGINS ?? '').split(',').map(value => value.trim()).filter(Boolean),
    port: integer(env.PORT, 3000, 1, 65_535),
    vercel: env.VERCEL === '1',
  };
}
