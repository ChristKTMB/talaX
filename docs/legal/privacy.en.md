# Privacy policy — Tala X

> **Draft of 2026-11-02, not yet in force.** To be reviewed by a lawyer
> before going live (see the points marked "To check").

This page explains what the Tala X web service (talax.online) does with the
files and data it receives. It describes how the software actually works;
its code is public: <https://github.com/ChristKTMB/talaX>.

**In short: your file is analysed, then deleted. Nothing is kept: not the
file, not its name, not its fingerprint, not the result.**

## 1. Controller

Christ KATUMBA KATUMBA, Kinshasa, Democratic Republic of the Congo.
Contact: <contact@talax.online>

To check: representative in the European Union (GDPR, Article 27).
[EU_REPRESENTATIVE]

## 2. What we process, and why

| Data | Why | How long |
| --- | --- | --- |
| The file you upload (image and metadata, sometimes including a GPS position, a date, a device model) | To analyse it, at your request | For the time of the analysis, a few seconds, then deleted, errors included |
| The analysis result and the HTML report | To send them back to you | Not kept: sent to your browser, then forgotten |
| Your IP address | To limit the number of analyses per minute, so the service stays available to everyone | Held in the server's memory only, never written to disk or to a log; replaced as new requests arrive and erased on restart |
| Your browser language | To show results in English or French | Not kept |

The file is processed in memory: it is never written to a disk. The
server's technical logs contain no file name, no coordinates, no IP address
and no text taken from the file: only the type of request, its answer and its
duration.

We use **no cookies**, no audience measurement, no advertising, and no
third-party service in the page (fonts, scripts).

## 3. Legal basis

- The file is processed **at your request**, to provide the service you ask
  for (GDPR, Article 6(1)(b)).
- Limiting the number of requests relies on our **legitimate interest** in
  protecting the service from overload (GDPR, Article 6(1)(f)).
- In the Democratic Republic of the Congo: Digital Code (Ordinance-Law
  No. 23/010 of 13 March 2023), Title III. To check: declaration or
  authorisation formalities with the data protection authority.

## 4. Who else receives data

- **Contabo GmbH** (Germany), host of the server, data centre in the
  European Union. Your file passes through its machines for the time of the
  analysis.
- **OpenStreetMap Foundation** (United Kingdom), only if you ask to show the
  map. Map tiles are requested by our server, not by your browser:
  OpenStreetMap receives the area shown, but neither your IP address nor
  your file. The page warns you before showing the map.

No data is sold, shared for advertising, or used to train an artificial
intelligence model.

## 5. A sensitive file? Use the command-line tool

If you are protecting a source, or if the file must not leave your machine
for any reason, use the command-line tool (`pip install talax`): it runs the
same analysis on your computer and sends nothing.

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
