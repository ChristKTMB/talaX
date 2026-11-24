"""French versions of the horizontal logos: same mark and name, tagline
"Regardez au-delà du pixel" drawn from the same font (Liberation Mono), in
capitals and with the same spacing as the English one.

    uv run --no-project --with fonttools --with brotli \
        python scripts/brand_french_logos.py

Writes docs/brand/logo-*-fr.svg next to each English logo.
"""

from __future__ import annotations

import re
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "docs" / "brand"
FONT = ROOT / "web" / "public" / "fonts" / "liberation-mono-regular.woff2"
TAGLINE = "REGARDEZ AU-DELÀ DU PIXEL"
TITLE = "Tala X - Regardez au-delà du pixel"
_GLYPH = re.compile(
    r'<path transform="translate\(([\d.]+),0\) scale\(([\d.]+),-[\d.]+\)"'
)
_ENGLISH = "SEE BEYOND THE PIXEL"


def main() -> None:
    font = TTFont(FONT)
    cmap, glyphs = font.getBestCmap(), font.getGlyphSet()
    for english in sorted(BRAND.glob("logo-*.svg")):
        if english.stem.endswith("-fr"):
            continue
        svg = english.read_text(encoding="utf-8")
        # The tagline is the only group drawn at reduced opacity; it holds
        # glyph paths only, so it ends at the next closing tag.
        start = svg.index('opacity="0.72"')
        open_end = svg.index(">", start) + 1
        close = svg.index("</g>", open_end)
        found = _GLYPH.findall(svg[open_end:close])
        positions = [(float(x), float(s)) for x, s in found]
        scale = positions[0][1]
        step = (positions[-1][0] - positions[0][0]) / (len(_ENGLISH) - 1)
        advance = glyphs[cmap[ord("E")]].width * scale

        paths = []
        for i, char in enumerate(TAGLINE):
            if char == " ":
                continue
            pen = SVGPathPen(glyphs)
            glyphs[cmap[ord(char)]].draw(pen)
            place = f"translate({i * step:.2f},0) scale({scale:.6f},-{scale:.6f})"
            paths.append(f'<path transform="{place}" d="{pen.getCommands()}"/>')
        old_width = float(re.search(r'viewBox="0 0 ([\d.]+)', svg)[1])  # type: ignore[index]
        old_text = (len(_ENGLISH) - 1) * step + advance
        new_width = old_width - old_text + (len(TAGLINE) - 1) * step + advance
        french = svg[:open_end] + "\n".join(paths) + svg[close:]
        french = french.replace(f"{old_width:.2f}", f"{new_width:.2f}")
        french = re.sub(
            r'width="\d+" (height="\d+" role)',
            rf'width="{round(new_width)}" \1',
            french,
            count=1,
        )
        french = french.replace(
            "<title>Tala X - See beyond the pixel</title>", f"<title>{TITLE}</title>"
        )
        target = english.with_name(f"{english.stem}-fr.svg")
        target.write_text(french, encoding="utf-8")
        print(f"{target.name}: {new_width:.2f} wide")


if __name__ == "__main__":
    main()
