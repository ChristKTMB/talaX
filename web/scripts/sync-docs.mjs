// Copies what the front needs from the repository's docs/ folder, which stays
// the only source: Angular cannot read assets outside web/. Runs before every
// build, dev server and test run (see package.json). The output is not versioned.
import { copyFileSync, mkdirSync, readdirSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const web = join(dirname(fileURLToPath(import.meta.url)), '..');
const docs = join(web, '..', 'docs');

const brand = join(web, 'public', 'brand');
rmSync(brand, { recursive: true, force: true });
mkdirSync(brand, { recursive: true });
for (const file of readdirSync(join(docs, 'brand'))) {
  if (file.endsWith('.svg')) copyFileSync(join(docs, 'brand', file), join(brand, file));
}
for (const file of ['favicon.svg', 'favicon.ico']) {
  copyFileSync(join(docs, 'brand', file), join(web, 'public', file));
}
