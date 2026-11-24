# Reading a report

This guide explains what each part of a Tala X report says, on the site as on
the command line, and what to do with it.

## 1. What Tala X says, and what it does not

**Tala X never says that an image is true or fake, and certifies nothing.** It
says what can honestly be said about a file, and what cannot.

- "Original camera file" means the file carries the marks of a camera. Not that
  what it shows is true: someone who knows how can forge metadata.
- Tala X is built against **platform laundering** (a recycled photo,
  recompressed, out of context, with a false caption), not against an expert
  forger.
- Never present a Tala X result as a certification.

## 2. The integrity result

It is the first answer of the report: **where does the file come from?** There
are three possible results.

| Result | What it means | What to do |
| --- | --- | --- |
| **Original camera file** | The file carries the marks of a camera: make and model, capture time, manufacturer data, original dimensions, no known editing software. | Read the checks: they have something to work with. |
| **Reprocessed copy** | The file was saved again by an app or a platform that removed the metadata. When Tala X recognises the fingerprint (WhatsApp, for example), it says so. | This is not a failure: ask your source for the original, check the caption, run a reverse image search. |
| **Undetermined** | Some camera marks, but not all: export from an editor, format conversion, screenshot… | Be careful: the file is no longer the camera's. Ask for the original. |

The explanation under the result always says what decided it.

## 3. The four states

Each check returns a state, **always with its explanation**:

| State | What it means |
| --- | --- |
| **Consistent** | The check could be done, and nothing contradicts. |
| **To check** | An anomaly that may have a legitimate explanation (a wrongly set clock, editing software). |
| **Suspicious** | A contradiction hard to explain otherwise (night in the photo, the sun high in the sky at the time given). |
| **Unverifiable** | The information needed is missing, often because a platform removed it. **This is not a bad sign**: it is what could not be checked. |

An "Unverifiable" check stays visible on purpose: you need to know what was
**not** checked.

## 4. The checks, one by one

| Check | What it checks |
| --- | --- |
| **Real file format** | Whether the extension (`.jpg`, `.png`…) matches the content. A renamed photo (a `.png` holding JPEG data) is "To check": often innocent, but the file was handled. |
| **GPS position** | Where the device was, and how precisely. A position masked (often by Android when sharing) is called "masked", not "absent". |
| **Date and time** | When the photo was taken, and whether the device's clocks agree. A capture time that does not match the manufacturer's internal clock is "Suspicious": it is the trace of a changed date. |
| **Time zone** | Whether the time zone recorded by the device matches the one of the place (daylight saving included). |
| **Solar consistency** | Where the sun was at the place and time of the photo, and whether that matches what you see (day, twilight, night). Also describes the expected direction and length of shadows. |
| **Declared place and time** | Only if you entered a caption: how far, and how far apart in time, it is from the file. More than 100 km: "Suspicious"; a date gap: at most "To check", since clocks are often wrongly set. |
| **Weather** | Only if you asked for it: the weather given by the Open-Meteo model, compared with what you see. At most "To check", never "Suspicious": the model works on squares of 9 to 25 km. |
| **Editing software** | Whether an image editor is recorded in the file (Photoshop, Lightroom, GIMP…). "Unverifiable" when nothing is recorded: many programs write nothing. |
| **C2PA Content Credentials** | A digital signature that says who produced or changed the file, and sometimes that AI was used. "Consistent" only if the signature is intact and comes from an organisation on the official C2PA list; "Suspicious" if the signature is broken; "To check" if the file was changed after signing or the signer is not recognised. Most photos have none. |

Under each check, **Raw values** shows the data that led to the state.

## 5. The image and its embedded preview

Many files hold a small preview of the image. The report shows both side by
side. Some programs change the image but leave the old preview, which may then
show what was there before.

It is a **visual exploration, not conclusive**: on genuine photos the two can
also differ slightly (framing, colours). No state is drawn from it: look for
yourself.

## 6. What Tala X does not do, on purpose

- **It does not detect AI-generated images by analysing pixels.** Such
  detectors are wrong too often: after the resizing and compression every
  platform applies, they fall to chance level, with up to a third of false
  alarms on real press photos. Only AI **declared** in a C2PA credential is
  reported.
- It draws no verdict from Error Level Analysis (ELA).
- It does not guess a place from what the image shows: that is human
  investigation work.
- For a video, it reads the container metadata only.

## 7. What next?

- **Ask your source for the original**, with the message offered, sent "as a
  document" or as an e-mail attachment.
- **Check the caption**: enter the place and time claimed.
- **Look for earlier copies of the photo** (Google Lens, TinEye, Yandex): most
  visual misinformation is real old photos with a new caption.
- **Keep the report**: HTML, or PDF through printing.

## 8. The report of a batch

`talax batch` adds:

- **Same picture**: identical files ("same file"), copies of the same photo
  ("same image"), and very close images ("the same photo edited, or photos
  taken a moment apart"). It is a computed resemblance, to check by eye; it
  says nothing about whether an image is true. A cropped copy is usually not
  found.
- **Timeline**: the photos in the real order they were taken when every time
  zone is known; otherwise in the order of the time shown by the devices, and
  the total duration is said to be approximate.
- **Places**: the positions of the photos and the widest distance between two
  of them.
