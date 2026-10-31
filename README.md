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

## Try it (development version)

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/) and
[ExifTool](https://exiftool.org/) 13.0 or newer.

```bash
git clone https://github.com/ChristKTMB/talaX.git && cd talaX
uv sync
uv run talax analyze photo.jpg                  # report in the terminal
uv run talax analyze photo.jpg --sky day        # what the photo shows, for the solar check
uv run talax analyze photo.jpg --html report.html
uv run talax analyze photo.jpg --json           # machine-readable
```

The HTML report is a single self-contained file: opening it loads nothing from
the network.

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
