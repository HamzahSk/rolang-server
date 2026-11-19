import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import handler from '../api/index.js';
import { database } from '../src/db.js';

const config = JSON.parse(await readFile(new URL('../vercel.json', import.meta.url), 'utf8'));
assert.equal(config.framework, null, 'Use the explicit API function instead of detecting the app factory as an Express handler.');
assert.equal(config.buildCommand, '', 'Plain JavaScript functions need no static-site build or output directory.');
assert.equal(typeof handler, 'function', 'The Vercel entrypoint must export a request handler.');
assert.ok(config.functions['api/index.js']);
assert.ok(config.rewrites.some(route => route.source === '/(.*)' && route.destination === '/api'));
await database().end();
console.log('Production entrypoint and Vercel configuration verified (no database connection required).');
