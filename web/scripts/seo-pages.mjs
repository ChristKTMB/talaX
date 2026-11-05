// Runs after `ng build`: writes one HTML file per page and language, each with
// its own language, title, description and links to the other language, plus
// the sitemap and the "not found" page. Search engines and link previews read
// them without running JavaScript; nginx serves them (deploy/nginx.conf).
// The texts come from the front's catalogues, the addresses from pages.json:
// PageHead writes the same head when the visitor moves around the site.
import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const web = join(dirname(fileURLToPath(import.meta.url)), '..');
const out = join(web, 'dist', 'talax-web', 'browser');
const read = (path) => JSON.parse(readFileSync(join(web, path), 'utf8'));
const { site, paths } = read('src/app/core/i18n/pages.json');
const catalogs = { en: read('src/app/core/i18n/en.json'), fr: read('src/app/core/i18n/fr.json') };
const locales = { en: 'en_US', fr: 'fr_FR' };
const template = readFileSync(join(out, 'index.html'), 'utf8');

const escape = (text) =>
  text.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const fileOf = (path) => (path === '/' ? 'index.html' : `${path.slice(1)}.html`);

function page(name, lang) {
  const text = (key) => {
    const value = catalogs[lang][key];
    if (!value) throw new Error(`missing text ${key} (${lang})`);
    return escape(value);
  };
  const title = text(`page.${name}.title`);
  const description = text(`page.${name === 'not-found' ? 'home' : name}.description`);
  const head = [`<title>${title}</title>`, `<meta name="description" content="${description}" />`];
  if (name === 'not-found') {
    head.push('<meta name="robots" content="noindex" />');
  } else {
    const url = (at) => site + paths[name][at];
    head.push(
      `<link rel="canonical" href="${url(lang)}" />`,
      `<link rel="alternate" hreflang="en" href="${url('en')}" />`,
      `<link rel="alternate" hreflang="fr" href="${url('fr')}" />`,
      `<link rel="alternate" hreflang="x-default" href="${url('en')}" />`,
      `<meta property="og:url" content="${url(lang)}" />`,
    );
  }
  head.push(
    `<meta property="og:title" content="${title}" />`,
    `<meta property="og:description" content="${description}" />`,
    `<meta property="og:locale" content="${locales[lang]}" />`,
  );
  if (!/<title>[^<]*<\/title>/.test(template) || !/<html lang="en">/.test(template)) {
    throw new Error('index.html no longer has the expected <html lang> and <title>');
  }
  return template
    .replace('<html lang="en">', `<html lang="${lang}">`)
    .replace(/<title>[^<]*<\/title>/, head.join('\n    '));
}

const written = [];
for (const [name, byLang] of Object.entries(paths)) {
  for (const [lang, path] of Object.entries(byLang)) {
    const file = join(out, fileOf(path));
    mkdirSync(dirname(file), { recursive: true });
    writeFileSync(file, page(name, lang));
    written.push(path);
  }
}
writeFileSync(join(out, '404.html'), page('not-found', 'en'));

const alternates = (name) =>
  Object.entries(paths[name])
    .map(
      ([lang, path]) =>
        `    <xhtml:link rel="alternate" hreflang="${lang}" href="${site}${path}"/>`,
    )
    .concat(
      `    <xhtml:link rel="alternate" hreflang="x-default" href="${site}${paths[name].en}"/>`,
    )
    .join('\n');
const urls = Object.entries(paths).flatMap(([name, byLang]) =>
  Object.values(byLang).map(
    (path) => `  <url>\n    <loc>${site}${path}</loc>\n${alternates(name)}\n  </url>`,
  ),
);
writeFileSync(
  join(out, 'sitemap.xml'),
  '<?xml version="1.0" encoding="UTF-8"?>\n' +
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" ' +
    'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' +
    urls.join('\n') +
    '\n</urlset>\n',
);
console.log(`seo-pages: ${written.join(', ')}, 404, sitemap.xml`);
