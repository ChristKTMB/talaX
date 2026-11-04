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
| `favicon-32.svg`, `favicon-16.svg` | Simplified marks drawn for each size: the 5×5 grid is unreadable below 40 px |
| `favicon.svg` | Scalable favicon, based on the 16 px mark |
| `favicon.ico` | Legacy favicon (16 px only for now) |

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

## Known gaps

- `favicon.ico` holds only the 16 px size; it should also hold 32 px.
- `favicon-32.svg` inverts the mark (filled cells, empty centre), unlike the
  symbol and the 16 px favicon (empty cells, filled centre).
- Tagline in English only; a French version ("Regardez au-delà du pixel") is
  needed for the French site.
