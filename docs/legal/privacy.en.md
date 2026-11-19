# Privacy policy — Tala X

Version of 2026-11-19.

This page explains what the Tala X web service (talax.online) does with the
files and data it receives. It describes how the software actually works;
its code is public: <https://github.com/ChristKTMB/talaX>.

**In short: your file is analysed, then deleted. Nothing is kept: not the
file, not its name, not its fingerprint, not the result.** The only
exception, and only if you ask for it: the weather lookup sends a rounded
place and a date to Open-Meteo, which may keep them for 90 days
(section 4).

## 1. Controller

Christ KATUMBA KATUMBA, Kinshasa, Democratic Republic of the Congo.
Contact: <contact@talax.online>

## 2. What we process, and why

| Data | Why | How long |
| --- | --- | --- |
| The file you upload (image and metadata, sometimes including a GPS position, a date, a device model) | To analyse it, at your request | For the time of the analysis, a few seconds, then deleted, errors included |
| What you add to the file, if you do: what the photo shows (day, twilight, night), and the place and time a caption claims | To complete the analysis, at your request | Like the file: for the time of the analysis, then forgotten |
| The place of the photo, rounded to about 11 km, and its date, if you ask for the weather | To cross-check with the weather, at your request | Not kept by us; passed on to Open-Meteo (section 4) |
| The analysis result and the HTML report | To send them back to you | Not kept: sent to your browser, then forgotten |
| Your IP address | To limit the number of analyses per minute, so the service stays available to everyone | Held in the server's memory only, never written to disk or to a log; replaced as new requests arrive and erased on restart |
| Your browser language | To show results in English or French | Not kept |

The file is processed in memory: it is never written to a disk. The
server's technical logs contain no file name, no coordinates, no IP address
and no text taken from the file: only the type of request, its answer and its
duration.

The message to send to your source is copied by your browser to your
clipboard: it is sent nowhere.

We use **no cookies**, no audience measurement, no advertising, and no
third-party service in the page (fonts, scripts).

## 3. Legal basis

- The file, and what you add to it (what the photo shows, the place and
  time of a caption, the weather lookup), are processed **at your request**,
  to provide the service you ask for (GDPR, Article 6(1)(b)).
- Limiting the number of requests relies on our **legitimate interest** in
  protecting the service from overload (GDPR, Article 6(1)(f)).
- In the Democratic Republic of the Congo: Digital Code (Ordinance-Law
  No. 23/010 of 13 March 2023), Title III.

## 4. Who else receives data

- **Contabo GmbH** (Germany), host of the server, data centre in the
  European Union. Your file passes through its machines for the time of the
  analysis.
- **OpenStreetMap Foundation** (United Kingdom), only if you ask to show the
  map. Map tiles are requested by our server, not by your browser:
  OpenStreetMap receives the area shown, but neither your IP address nor
  your file. The page warns you before showing the map.
- **OpenMeteo GmbH** (Switzerland), only if you ask for the weather. Our
  server sends it the position rounded to about 11 km (0.1 degree) and the
  date, never the exact time, nor your IP address, nor your file. Open-Meteo
  states that it keeps the requests it receives, coordinates included, in its
  technical logs for up to 90 days; it acts as an independent controller.
  The page warns you before sending. Switzerland benefits from an adequacy
  decision of the European Commission.
- **Google Lens, TinEye, Yandex**: only if you upload the photo there
  yourself, following the links of the report. Tala X sends them nothing,
  and the links do not pass on the page you come from; their own terms apply
  to what you upload.

No data is sold, shared for advertising, or used to train an artificial
intelligence model.

## 5. A sensitive file? Use the command-line tool

If you are protecting a source, or if the file must not leave your machine
for any reason, use the command-line tool (`pip install talax`): it runs the
same analysis on your computer and sends nothing. The only exception, if
you ask for it (`--weather`): the weather lookup, then made directly by your
computer, which sends Open-Meteo the rounded position and the date, with
your IP address.

## 6. Your rights

You have the rights of access, rectification, erasure, objection,
restriction and portability over your data. As we keep nothing, we will
usually have nothing to give you or to erase; write to us anyway with any
question: <contact@talax.online>.

You can also complain to a supervisory authority: the one of your country if
you live in the European Union, or the data protection authority provided
for by the Digital Code in the Democratic Republic of the Congo.

## 7. Security

Encrypted connection (HTTPS), files in memory only, read-only containers
without privileges, no data kept: what is not kept cannot leak.

## 8. Changes

Every change to this page is dated and visible in the history of the public
repository. If the versions differ, the French version prevails.
