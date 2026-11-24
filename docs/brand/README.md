# Tala X logo

The mark is a pixel grid inside viewfinder corners, with a single cell marked
in the centre: the tool points at a precise place in the file, it does not
deliver a verdict. It deliberately avoids anything that suggests a guarantee
(check mark, shield, seal, badge, padlock), because Tala X certifies nothing.

## Files

| File | Use |
| --- | --- |
| `logo-horizontal-ink.svg` / `logo-horizontal-paper.svg` | Full logo (mark, name, tagline), transparent background, for light / dark backgrounds |
| `logo-horizontal-light-bg.svg` / `logo-horizontal-dark-bg.svg` | Same, with a solid background |
| `symbol-ink.svg` / `symbol-paper.svg` | Mark alone, transparent background |
| `symbol-ink-on-paper.svg` / `symbol-paper-on-ink.svg` | Mark alone, solid background (app icon, README) |
| `logo-monochrome.svg` / `symbol-monochrome.svg` | One colour, `currentColor`, recolourable with CSS |
| `logo-*-fr.svg` | The same logos with the French tagline "Regardez au-delà du pixel" |
| `favicon-32.svg`, `favicon-16.svg` | Simplified marks drawn for each size: the 5×5 grid is unreadable below 40 px |
| `favicon.svg` | Scalable favicon, based on the 16 px mark |
| `favicon.ico` | Legacy favicon, 16 px and 32 px |
| `og-en.png`, `og-fr.png` | Picture shown when a link to the site is shared, 1200 x 630 |

All text is converted to paths: no font is loaded, and the files reference
no external resource.

## Colours

Two colours, no accent colour, so the logo never looks like one of the report
states (consistent, to check, suspicious, unverifiable):

- ink `#1B1A17`
- paper `#FAF8F2`

## Typeface

Liberation Mono (SIL Open Font License 1.1). A monospace face, consistent with
the ASCII banner of the CLI. Use it again if the text has to be redrawn.

## Regenerating

- French logos, from the English ones and the font hosted by the site:
  `uv run --no-project --with fonttools --with brotli python scripts/brand_french_logos.py`
- `favicon.ico` and the share pictures, drawn from the SVG files in Chromium
  (from `web/`): `node scripts/brand-images.mjs`

Run them again after any change to the logo, and commit the results.

## History

- 2026-11-24: `favicon-32.svg` read inverted at its real size (the cell
  borders, 6.5 units, filled the empty cells): borders thinned to 4.5.
  `favicon.ico` now holds 32 px too. French tagline added. Share pictures
  added.
