import { createApp } from './app.js';
import { serverConfig } from './config.js';
const { port } = serverConfig();
createApp().listen(port, '0.0.0.0', () => console.log(`Ro-Lang API listening on port ${port}.`));
