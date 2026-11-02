# Tala X

> *See beyond the pixel*

[Français](https://github.com/ChristKTMB/talaX/blob/main/README.fr.md)

Tala X tells you what can honestly be said about an image: whether it is an
original camera file or a copy reprocessed by a platform, where and when it was
taken, and whether it went through an editor. Video support (container
metadata) is planned.

> **Status: pre-alpha (0.2).** Usable, but rules and output may still change.

## The question Tala X asks first

Not *"is this image fake?"* — no technology answers that reliably today. But:

> **Is this file an original from a camera, or a copy reprocessed by a
> platform?**

Every major social platform (Instagram, X, TikTok, WhatsApp…) strips EXIF,
IPTC and C2PA metadata on upload. Tala X detects that, identifies which
platform the file went through when it can, and tells you to ask your source
for the original — explaining how to send it without damaging it.

## How it reports

Each signal returns one of four states, **always with a plain-language
explanation**:

| State | Meaning |
| --- | --- |
| Consistent | Checked, no contradiction found |
| To check | An anomaly that may have a legitimate explanation |
| Suspicious | A contradiction hard to explain otherwise |
| Unverifiable | The information needed is missing |

Tala X never says "this image is fake", and never certifies that an image is
authentic. An original camera file is not proof of truth: metadata can be
forged by anyone who knows how. Tala X is built against platform laundering
and recycled images, not against expert forgers.

## What it checks

- File integrity and platform pipeline (WhatsApp, Instagram, X…)
- Real file format vs extension
- **Solar consistency**: is the recorded time physically possible at the
  recorded place?
- Weather cross-check against historical records
- GPS position, date and time, editing software, embedded thumbnail
- C2PA provenance certificates

It also hands off to reverse image search (Google Lens, TinEye, Yandex), which
catches old photos recycled with a false caption — the most common form of
visual misinformation.

## What it deliberately does not do

- **No AI-image detection from pixels.** Independent measurements show these
  detectors fall to chance after the resizing and compression every platform
  applies, with false positives on up to a third of genuine press photos.
- No Error Level Analysis used as a verdict.
- No automatic visual geolocation.
- Video: container metadata only.

## Install

**1. Install Tala X** (Python 3.12 or newer):

```bash
pipx install talax        # or: uv tool install talax    or: pip install talax
```

**2. Install ExifTool 13.0 or newer.** Tala X refuses to run with an older
version, because it would miss manufacturer tags and give different results.

- **macOS**: `brew install exiftool`
- **Windows**: download the Windows executable from
  [exiftool.org](https://exiftool.org/), unzip it, rename
  `exiftool(-k).exe` to `exiftool.exe`, keep the `exiftool_files` folder next
  to it, and add that folder to your `PATH`.
- **Linux**: distribution packages are often too old (Ubuntu 24.04 ships
  12.76). Install the latest release in your home folder:

  ```bash
  v=$(curl -fsS https://exiftool.org/ver.txt)
  mkdir -p ~/.local/opt ~/.local/bin
  curl -fsSL "https://sourceforge.net/projects/exiftool/files/Image-ExifTool-$v.tar.gz/download" | tar -xz -C ~/.local/opt
  ln -sf ~/.local/opt/Image-ExifTool-$v/exiftool ~/.local/bin/exiftool
  ```

Check with `exiftool -ver`. Tested on Linux, macOS and Windows.

## Use it from the command line

```bash
talax analyze photo.jpg                     # report in the terminal
talax analyze photo.jpg --sky day           # what the photo shows, for the solar check
talax analyze photo.jpg --html report.html  # self-contained HTML report
talax analyze photo.jpg --json              # machine-readable
talax analyze photo.jpg --lang fr           # in French (default: your system language)
```

Reports are available in English and French.

Nothing is ever sent over the network. The HTML report is a single file:
opening it loads nothing from the network either.

## Use it as a Python library

```python
from pathlib import Path

from talax import Observation, Sky, analyze
from talax.i18n import Language

analysis = analyze(Path("photo.jpg"), observation=Observation(Sky.DAY))
print(analysis.integrity.verdict, analysis.integrity.explain(Language.EN))
for result in analysis.results:
    print(result.signal_id, result.state, result.explain(Language.FR))
```

Every result carries a state, a message (`result.message.key`, stable across
languages), its explanation in English or French, and the raw values behind
it (`result.evidence`). The JSON output of the command line follows a
versioned schema (`"schema": 2`).

## Develop

```bash
git clone https://github.com/ChristKTMB/talaX.git
cd talaX
uv sync
uv run pytest
uv run ruff check && uv run ruff format --check && uv run mypy
```

Tests that need the reference corpus are skipped when `corpus/files/` is
absent: those files are not published (see the
[corpus protocol](https://github.com/ChristKTMB/talaX/blob/main/corpus/README.md)).

## Three ways to use it

- **Python library** — `pip install talax`, to integrate into your own platform
- **CLI** — runs on your machine; your file never leaves it. Recommended for
  sensitive material.
- **Web app** (coming) — hosted, for quick checks. Files will be analysed and
  deleted immediately, never stored.

Requires [ExifTool](https://exiftool.org/) and, for video,
[ffprobe](https://ffmpeg.org/).

## Contributing

The project is open to contributions. The most valuable one will be
**platform fingerprints**: measured characteristics of how a given platform
and app version reprocesses files. A contribution guide will come with the
first code.

## License

[Apache-2.0](https://github.com/ChristKTMB/talaX/blob/main/LICENSE)

The package embeds the [C2PA Trust List](https://github.com/c2pa-org/conformance-public/tree/main/trust-list)
of the C2PA Conformance Program (© C2PA, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)),
used unchanged to recognise Content Credentials signers. Its date and origin
are in `src/talax/data/c2pa/source.yaml`.
