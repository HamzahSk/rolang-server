import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import handler from '../api/index.js';
import { database } from '../src/db.js';

const config = JSON.parse(await readFile(new URL('../vercel.json', import.meta.url), 'utf8'));
assert.equal(config.framework, null, 'Use the explicit API function instead of framework detection.');
assert.equal(config.buildCommand, '', 'Plain JavaScript API functions must skip the static-site build.');
assert.equal(typeof handler, 'function', 'The Vercel entrypoint must export a request handler.');
assert.ok(config.functions['api/index.js']);
assert.ok(config.rewrites.some(route => route.source === '/(.*)' && route.destination === '/api'));
await database().close();
console.log('Production entrypoint and Vercel configuration verified without database access.');
