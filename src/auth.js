import { randomBytes, randomUUID, scrypt as scryptCallback, timingSafeEqual, createHash } from 'node:crypto';
import { promisify } from 'node:util';
import { ApiError } from './errors.js';
import { mongoOptions } from './db.js';
import { serverConfig } from './config.js';

const scrypt = promisify(scryptCallback);
const digest = value => createHash('sha256').update(value).digest('hex');
export async function hashPassword(password) {
  const salt = randomBytes(16).toString('hex');
  const key = await scrypt(password, salt, 64);
  return 'scrypt:' + salt + ':' + key.toString('hex');
}
export async function verifyPassword(password, stored) {
  const [, salt, hex] = stored.split(':');
  const key = await scrypt(password, salt, 64);
  const expected = Buffer.from(hex, 'hex');
  return expected.length === key.length && timingSafeEqual(key, expected);
}
export async function session(scope, user) {
  const token = randomBytes(32).toString('base64url');
  const expires = new Date(Date.now() + serverConfig().sessionDays * 86_400_000);
  await scope.db.collection('sessions').insertOne({
    _id: digest(token), user_id: user._id, expires_at: expires, created_at: new Date(),
  }, mongoOptions(scope));
  return { token, expiresAt: expires.toISOString(),
    user: { id: user._id, email: user.email, displayName: user.display_name, role: user.role } };
}
export function authentication(store) {
  return async (req, _res, next) => {
    const match = /^Bearer ([A-Za-z0-9_-]{43})$/.exec(req.get('authorization') ?? '');
    if (!match) throw new ApiError(401, 'UNAUTHENTICATED', 'Sign in to continue.');
    const hash = digest(match[1]);
    const { db } = await store.scope();
    const saved = await db.collection('sessions').findOne({ _id: hash, expires_at: { $gt: new Date() } });
    const user = saved && await db.collection('users').findOne({ _id: saved.user_id },
      { projection: { email: 1, display_name: 1, role: 1 } });
    if (!user) throw new ApiError(401, 'UNAUTHENTICATED', 'Your session has expired. Sign in again.');
    req.user = { id: user._id, email: user.email, display_name: user.display_name, role: user.role };
    req.tokenHash = hash;
    next();
  };
}
export function administrator(req, _res, next) {
  if (req.user.role !== 'admin') throw new ApiError(403, 'FORBIDDEN', 'Administrator access is required.');
  next();
}
export async function rateLimit(store, email, ip) {
  const { db } = await store.scope();
  for (const bucket of ['email:' + digest(email), 'ip:' + digest(ip)]) {
    const now = new Date();
    const expired = { $lte: [{ $ifNull: ['$expires_at', new Date(0)] }, now] };
    const update = [{ $set: {
      attempts: { $cond: [expired, 1, { $add: [{ $ifNull: ['$attempts', 0] }, 1] }] },
      expires_at: { $cond: [expired, new Date(now.getTime() + 900_000), '$expires_at'] },
    } }];
    let row;
    try {
      row = await db.collection('auth_attempts').findOneAndUpdate({ _id: bucket }, update,
        { upsert: true, returnDocument: 'after' });
    } catch (error) {
      if (error.code !== 11000) throw error;
      // Another instance may insert the same new bucket first.
      row = await db.collection('auth_attempts').findOneAndUpdate({ _id: bucket }, update,
        { returnDocument: 'after' });
      if (!row) throw error;
    }
    if (row.attempts > (bucket.startsWith('ip:') ? 100 : 20))
      throw new ApiError(429, 'RATE_LIMITED', 'Too many sign-in attempts. Try again in 15 minutes.');
  }
}
export { randomUUID };
