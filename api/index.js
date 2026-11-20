import { createApp } from '../src/app.js';
import { database } from '../src/db.js';
import { seed } from '../scripts/seed.js';

const store = database();
await seed(store);

export default createApp(store);
