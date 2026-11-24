// Raster images drawn from the SVG logo, written into docs/brand/ (the only
// source; sync-docs copies them into the site). Run by hand when the logo
// changes, then commit the result:
//
//   node scripts/brand-images.mjs
//
// - favicon.ico: the 16 px and 32 px marks, each drawn for its size.
// - og-en.png, og-fr.png: the picture shown when a link to the site is shared
//   (WhatsApp, LinkedIn...), 1200 x 630, in each language.
import { chromium } from '@playwright/test';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const web = join(dirname(fileURLToPath(import.meta.url)), '..');
const brand = join(web, '..', 'docs', 'brand');
const dataUri = (file, type) => `data:${type};base64,${readFileSync(file).toString('base64')}`;

const OG = {
  en: { logo: 'logo-horizontal-ink.svg', line: 'What can honestly be said about a photo.' },
  fr: {
    logo: 'logo-horizontal-ink-fr.svg',
    line: "Ce que l'on peut honnêtement dire d'une photo.",
  },
};

const browser = await chromium.launch();
const page = await browser.newPage();

async function render(html, width, height) {
  await page.setViewportSize({ width, height });
  await page.setContent(html);
  await page.evaluate(() => document.fonts.ready);
  return page.screenshot({ clip: { x: 0, y: 0, width, height } });
}

// --- favicon.ico ---------------------------------------------------------
const icons = [];
for (const size of [16, 32]) {
  const svg = dataUri(join(brand, `favicon-${size}.svg`), 'image/svg+xml');
  icons.push({
    size,
    png: await render(
      `<body style="margin:0"><img src="${svg}" width="${size}" height="${size}"></body>`,
      size,
      size,
    ),
  });
}
// An .ico holding PNG images: a 6-byte header, a 16-byte entry per image.
const header = Buffer.alloc(6 + 16 * icons.length);
header.writeUInt16LE(0, 0);
header.writeUInt16LE(1, 2);
header.writeUInt16LE(icons.length, 4);
let offset = header.length;
icons.forEach(({ size, png }, i) => {
  const entry = 6 + 16 * i;
  header.writeUInt8(size, entry);
  header.writeUInt8(size, entry + 1);
  header.writeUInt16LE(1, entry + 4); // colour planes
  header.writeUInt16LE(32, entry + 6); // bits per pixel
  header.writeUInt32LE(png.length, entry + 8);
  header.writeUInt32LE(offset, entry + 12);
  offset += png.length;
});
writeFileSync(join(brand, 'favicon.ico'), Buffer.concat([header, ...icons.map((i) => i.png)]));

// --- Open Graph pictures -------------------------------------------------
const mono = dataUri(join(web, 'public', 'fonts', 'liberation-mono-regular.woff2'), 'font/woff2');
for (const [lang, { logo, line }] of Object.entries(OG)) {
  const html = `<!DOCTYPE html><html lang="${lang}"><head><style>
    @font-face { font-family: Mono; src: url(${mono}) format('woff2'); }
    body { margin: 0; width: 1200px; height: 630px; background: #FAF8F2; color: #1B1A17;
           display: flex; flex-direction: column; justify-content: center; padding: 0 96px;
           box-sizing: border-box; font-family: system-ui, "DejaVu Sans", sans-serif; }
    img { width: 640px; height: auto; margin-left: -28px; }
    p { font-size: 40px; line-height: 1.3; margin: 40px 0 0; max-width: 960px; }
    .site { font-family: Mono, monospace; font-size: 28px; color: #5a574f; margin-top: 28px; }
  </style></head><body>
    <img src="${dataUri(join(brand, logo), 'image/svg+xml')}" alt="">
    <p>${line}</p>
    <p class="site">talax.online</p>
  </body></html>`;
  writeFileSync(join(brand, `og-${lang}.png`), await render(html, 1200, 630));
}

await browser.close();
console.log('favicon.ico, og-en.png, og-fr.png written to docs/brand/');
