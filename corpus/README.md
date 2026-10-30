# Reference corpus

Without a corpus whose ground truth is known, no signal can be tested and every
threshold is tuned blind. This folder holds the **descriptions** of the corpus
files. The files themselves are never committed (size, rights): they live in
`corpus/files/`, which is git-ignored.

## The one rule

**The truth about every reference file is known**: which device produced it,
which platforms it went through, how, and when. A file whose history you did
not witness is not a reference file.

Images found on the web have unknown provenance. They go in a separate
`unknown-provenance` set, used only to check that Tala X does not crash and
answers "unverifiable" cleanly. They are never used to measure reliability.

## Layout

```
corpus/
├── README.md              this protocol
├── sets/
│   ├── _template.yaml     copy it to start a new set
│   └── <set-id>.yaml      one set = one original and all its derivatives
└── files/                 git-ignored
    └── <set-id>/
        ├── original.jpg
        ├── whatsapp-gallery.jpg
        └── ...
```

A **set** is one original shot and every copy derived from it. Set ids look
like `2026-11-02-pixel8-street-01`: date, device, short subject, number.

## Capture protocol

1. Shoot the original. Copy it off the device **as a file**, never through a
   messaging app: USB cable, AirDrop, or a cloud sync that keeps originals
   (Google Photos "original quality", iCloud with "Download and Keep
   Originals").
2. Save it as `files/<set-id>/original.<ext>`, untouched. Never open and
   re-save it.
3. Send the original through each platform **yourself**, one at a time, and
   retrieve what comes out. Name each output after its route
   (`whatsapp-gallery.jpg`, `instagram-post-web.jpg`...).
4. Record every step in the set file: app version, send mode, how the copy was
   retrieved, date. Retrieval matters: downloading from a website and saving
   from an app are two different pipelines.
5. Compute the SHA-256 of each file and write it in the set file. This binds
   the description to the exact bytes.

```bash
sha256sum corpus/files/<set-id>/*
```

## Routes to cover

For each device, aim for:

| Route | Notes |
| --- | --- |
| WhatsApp, gallery, standard quality | the most common case |
| WhatsApp, gallery, HD | |
| WhatsApp, sent as document | should keep metadata |
| Telegram, compressed | |
| Telegram, sent as file | should keep metadata |
| Instagram post | retrieve from web and from app separately if possible |
| Instagram story | |
| X | |
| Facebook | |
| E-mail attachment | should keep metadata |
| Edited in an editor and exported | name the editor and its version |
| Screenshot of the photo | |

## Devices

Fingerprints learned from a single phone would describe that phone, not the
platform. Aim for at least three or four devices from different makers
(iPhone, Samsung, Pixel, a dedicated camera if available). Borrow them; only
the person holding the device needs to follow the protocol.

## Rights and privacy

- Only include photos you took, or that their author gave you explicit
  permission to use.
- Avoid recognisable faces of people who did not consent.
- GPS positions in originals reveal where you were. Shoot in places you are
  comfortable disclosing, since measured characteristics may be published.
