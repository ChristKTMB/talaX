# Tala X

> *See beyond the pixel*

[Français](README.fr.md)

Tala X tells you what can honestly be said about an image or a video: whether
it is an original camera file or a copy reprocessed by a platform, where and
when it was taken, and whether it went through an editor.

> **Status: early development.** There is no usable release yet.

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

## Install and try it (development version)

Tested on Linux (Ubuntu under WSL). Windows and macOS should work but have not
been tested yet: please report any problem.

**1. Install uv** (it also installs the right Python version for you):

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```
```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**2. Install ExifTool 13.0 or newer** — Tala X refuses to run with an older
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

Check with `exiftool -ver`.

**3. Get Tala X and analyse a photo:**

```bash
git clone https://github.com/ChristKTMB/talaX.git
cd talaX
uv sync
uv run talax analyze photo.jpg                     # report in the terminal
uv run talax analyze photo.jpg --sky day           # what the photo shows, for the solar check
uv run talax analyze photo.jpg --html report.html  # self-contained HTML report
uv run talax analyze photo.jpg --json              # machine-readable
```

The HTML report is a single file: opening it loads nothing from the network.
Nothing is ever sent anywhere by the command line tool.

**4. Run the tests** (contributors):

```bash
uv run pytest
uv run ruff check && uv run ruff format --check && uv run mypy
```

Tests that need the reference corpus are skipped when `corpus/files/` is
absent: those files are not published (see `corpus/README.md`).

## How you will use it

- **Python library** — `pip install talax`, to integrate into your own platform
- **CLI** — runs on your machine; your file never leaves it. Recommended for
  sensitive material.
- **Web app** — hosted, for quick checks. Files are analysed and deleted
  immediately, never stored.

Requires [ExifTool](https://exiftool.org/) and, for video,
[ffprobe](https://ffmpeg.org/).

## Contributing

The project is open to contributions. The most valuable one will be
**platform fingerprints**: measured characteristics of how a given platform
and app version reprocesses files. A contribution guide will come with the
first code.

## License

[Apache-2.0](LICENSE)
