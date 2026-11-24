# Using Tala X online

Tala X online (<https://talax.online>) analyses a photo in your browser, with
nothing to install. This guide shows, screen by screen, everything you can do
there.

A sensitive file (a source to protect, a photo that must not leave your
computer for any reason)? Use the [command line](cli.en.md) instead: it runs
the same analysis on your machine and sends nothing.

## 1. Upload a photo

1. Open <https://talax.online>.
2. Drag the photo into the "Drop a photo here" area, or click
   **Choose a file**.
3. Click **Analyse the photo**.

Good to know:

- **One photo at a time, 50 MB at most.** To analyse a whole folder, use
  `talax batch` on the [command line](cli.en.md).
- **Formats**: JPEG, PNG, HEIC, WebP, TIFF… Tala X recognises the format from
  the file's content, not from its extension. Some browsers cannot display
  HEIC: the analysis still covers the file.
- **Use the file as you received it.** A screenshot of the photo, or a photo
  "saved as" from a social network, is no longer the same file: it has lost
  what we are looking for.
- **10 analyses per minute at most** from one connection. Beyond that, a
  countdown says when to try again.

## 2. The report

In a few seconds the report appears, from top to bottom:

1. **The integrity result**: original camera file, reprocessed copy or
   undetermined, with its explanation. This is the most important answer.
   See [Reading a report](report.en.md).
2. **A banner for each "Suspicious" check**, if any, leading to the check.
3. **Ask for the original**, if the file is not an original camera file (see
   below).
4. **Check the caption** (see below).
5. **Cross-check with the weather** (see below).
6. **The image and its embedded preview**, side by side: a visual exploration,
   not conclusive.
7. **The checks**, each with its state and its explanation.
8. **Has this photo been seen before?**: reverse image search.
9. **Warning**, **download** of the report and **technical details** (the
   file's SHA-256 fingerprint, size, time of the analysis, tools).

The report is kept nowhere: **if you reload the page, it is gone.** Download
it if you want to keep it (section 8).

## 3. "What does the photo show?": the sky question

When the file says **where and when** the photo was taken, Tala X computes
where the sun was at that moment. It does not look at the image: you say what
it shows.

1. A black banner at the top of the report asks the question; click
   **Answer**.
2. Choose **Day**, **Twilight** or **Night**.
3. The file is analysed again with your answer. The "Solar consistency" check
   then compares the sky you see with the computed sun.

Example: the photo shows night, but the sun was 50° above the horizon at the
recorded time and place: the check becomes "Suspicious". If a mere clock
error (3 hours at most) could explain it, it becomes "To check".

The check also describes where shadows should fall. To change your mind:
**Change the answer**.

## 4. Check the caption

A photo often travels with a caption: "Goma, this morning". Tala X can
confront that place and date with the sun and with the file.

- **If the file does not say where or when** the photo was taken (the usual
  case for a photo received on WhatsApp), the section is already open.
- **Otherwise**, click **Enter the place and time claimed**.

Then:

1. **The place**, in one of two ways:
   - type or paste the coordinates, for example `-1.67920, 29.22280`
     (latitude then longitude, in decimal degrees; this is what a map service
     gives when you click a point);
   - or click **Pick on the map**, then on the place claimed. A few kilometres
     off barely change the position of the sun.
2. **The date** and **the time**, in local time at that place.
3. Click **Check**.

The report is made again with that place and time:

- **solar consistency** uses the caption; then answer "What does the photo
  show?";
- a **Declared place and time** check appears if the file has its own
  position or time: it says how far and how far apart in time the caption is.
  More than 100 km between the caption and the file's GPS: "Suspicious".

To correct it: **Change the claim**; to go back to the file alone:
**Remove the claim**.

## 5. Cross-check with the weather

Once a place and a time are known (from the file or from the caption), Tala X
can ask the Open-Meteo weather model what the weather was.

1. Read the warning: **the place, rounded to about 11 km, and the date are
   sent to Open-Meteo**, which may keep them in its logs for 90 days. Neither
   your address nor your file. For a sensitive file, do not do it.
2. Click **Look up the weather**.
3. Answer **What weather does the photo show?**: rain falling, snow falling,
   overcast sky, clear sky or sharp shadows.

The "Weather" check gives the model's values (rain, snow, clouds) and is at
best "Consistent", at worst "To check". **Never "Suspicious"**: the model
works on squares of 9 to 25 km, and a local shower can escape it.

## 6. Ask for the original

If the file is a reprocessed copy or undetermined, the **Ask for the
original** section offers a message ready to send to your source. It explains
how to send the photo again without damaging it (WhatsApp or Telegram "as a
document", or as an e-mail attachment).

- Click **Copy the message**, then paste it into your conversation.
- Read the caution: the original can reveal where your source was and their
  phone's serial number. Ask for it only if they can send it safely, and
  analyse it with the command line.

## 7. The map

When the file holds a valid GPS position, the "GPS position" check offers
**Show on the map**. The map loads only then: the area is requested from
OpenStreetMap **by our server**, which passes on neither your address nor your
file.

## 8. Keep the report

- **Download the report (HTML)**: a single file that opens offline and loads
  nothing from the internet. To make it, the file is sent to the server again,
  then deleted.
- **As a PDF**: open the downloaded report, print it (Ctrl+P, or ⌘P on a Mac)
  and choose "Save as PDF".

## 9. Reverse image search

A real photo with a false caption is more common than a doctored one, and no
analysis of the file can catch it. The **Has this photo been seen before?**
section links to Google Lens, TinEye and Yandex.

1. Open one of the services.
2. Upload the photo there yourself.
3. Look for the oldest copy and compare its date and place with the caption.
   If nothing comes up, try again with a crop of the most distinctive part.

Tala X sends them nothing. They receive the photo you upload and may keep it:
do not do it with a confidential photo.

## 10. Language

The **FR / EN** buttons at the bottom of the page switch the whole site. If a
report is shown, it is asked again in the other language: the file is sent
again, with your answers.

## 11. What is sent, what is kept

- **Your file** is sent to our server (in the European Union), analysed in
  memory, then deleted. Nothing is kept: not the file, not its name, not its
  fingerprint, not the result.
- **Your answers** (sky, caption, weather) go the same way.
- **Nothing is written on your device**: no cookie, no audience measurement.
- **The only exceptions, at your request**: the weather (Open-Meteo, rounded
  place and date) and the map (OpenStreetMap, area shown, through our server).

The details are in the [privacy policy](../legal/privacy.en.md).
