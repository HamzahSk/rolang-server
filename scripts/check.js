import { readdir } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
async function checkDirectory(directory) {
  for (const entry of await readdir(new URL('../' + directory + '/', import.meta.url), { withFileTypes: true })) {
    const path = directory + '/' + entry.name;
    if (entry.isDirectory()) await checkDirectory(path);
    else if (entry.name.endsWith('.js')) {
      const result = spawnSync(process.execPath, ['--check', path], { stdio: 'inherit' });
      if (result.status) process.exit(result.status);
    }
  }
}
for (const directory of ['src', 'api', 'scripts', 'test']) await checkDirectory(directory);
