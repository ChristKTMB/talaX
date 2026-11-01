# Tala X web API

The API serves the Tala X web front. It is not a public service for other
sites (no CORS): to integrate Tala X, use the Python library
(`pip install talax`). The machine-readable schema is at
`/api/openapi.json`.

Run it locally:

```sh
pip install "talax[server]"   # or: uv sync --all-extras
talax serve                    # http://127.0.0.1:8000
```

or the whole service, as deployed (API behind nginx, read-only containers,
temporary files in memory):

```sh
docker compose up --build      # http://127.0.0.1:8088 (port: TALAX_PORT)
```

Real responses for every situation are in [`api-examples/`](api-examples/).

## What the server keeps

Nothing. An uploaded file is written to a temporary directory for the time of
its analysis (ExifTool needs a file) and deleted afterwards, errors included.
The server logs one line per request — method, route, status, duration — and
never a file name, a position, an error text or a client address. Every
response carries `Cache-Control: no-store`.

## `POST /api/analyze`

Multipart form:

| Field | Required | Values |
| --- | --- | --- |
| `file` | yes | the image (50 MB at most) |
| `lang` | no | `en` or `fr`; default: the `Accept-Language` header (`fr*` → French, otherwise English) |
| `sky` | no | `day`, `twilight` or `night`: what the user sees in the photo, for the solar check |

Query: `format=json` (default) or `format=html`.

### The JSON answer

The same view as `talax analyze --json` (`schema: 2`), plus one field:

- `thumbnail`: the preview embedded in the file, as a `data:` URI, upright,
  or `null`. The browser already has the image itself: the server does not
  send it back. Showing the two side by side is a visual exploration, **not
  conclusive**, and must be labelled as such.
- `file.name` is always `null`: the browser knows the name, the server does
  not keep it.

Top-level fields:

| Field | Meaning |
| --- | --- |
| `integrity.verdict` | `original`, `reprocessed` or `undetermined` — the headline of the report |
| `integrity.pipeline` | id of the platform fingerprint matched (`whatsapp-gallery`…), or `null` |
| `integrity.label`, `integrity.explanation` | ready-to-display text, in `lang` |
| `results[]` | one entry per check, in a stable order |
| `results[].state` | `consistent`, `to_check`, `suspicious` or `unverifiable` |
| `results[].name`, `label`, `explanation` | ready-to-display text, in `lang` |
| `results[].message` | stable key of the explanation, for code (never parse the text) |
| `results[].evidence` | the raw values behind the state |
| `results[].confidence` | a probability where one really exists, otherwise `null` |
| `disclaimer` | must be shown with every report |

Display rules that come with the data:

- Every state is shown **with its explanation**. A flag without its
  explanation is never displayed.
- `unverifiable` results are shown, not hidden: the reader must see what
  could *not* be checked.
- Never present a verdict as "certified", "authenticated" or "verified
  true". `original` means "camera original", not "authentic".
- A GPS result in state `consistent` gives `evidence.latitude` and
  `evidence.longitude`: that is when the map can be offered.

### Asking for the sky

Without `sky`, the solar check is `unverifiable` and its explanation
describes what the photo should show. The front then asks the user what they
see and **sends the same file again** with `sky`. The server keeps nothing
between the two requests; each answer is a new analysis.

### `format=html`

The self-contained HTML report, as a download
(`Content-Disposition: attachment; filename="talax-<hash>.html"`). It loads
nothing from the network.

## `GET /api/tiles/{z}/{x}/{y}.png`

Map tiles (zoom 0 to 19) relayed from OpenStreetMap, so that OpenStreetMap
never sees the user. For Leaflet:
`L.tileLayer("/api/tiles/{z}/{x}/{y}.png", { maxZoom: 19, attribution: … })`.

- The map must show `© OpenStreetMap contributors`, visibly (OSM policy).
- The page must not send `Referrer-Policy: no-referrer`: the relay passes
  our site's origin on to OSM, as its policy requires.
- Show the map only after the user asks for it, saying that the area will be
  requested from OpenStreetMap through our server.

## `GET /api/health`

`{"status": "ok", "schema": 2, "tools": {"talax": "…", "exiftool": "…"}}`

## Errors

Every error has the same body; `message` is in the `Accept-Language`
language:

```json
{"error": {"code": "busy", "message": "The service is busy. Please try again in a few seconds."}}
```

| Status | `code` | When |
| --- | --- | --- |
| 404 | `not_found` | unknown address, impossible tile |
| 413 | `file_too_large` | more than 50 MB |
| 422 | `invalid_request` | missing file or invalid value; `fields` lists the names, never the values |
| 500 | `analysis_failed` | the file could not be analysed (damaged, unsupported) |
| 500 | `internal` | unexpected error; nothing can be concluded about the file |
| 502 | `tiles_unavailable` | OpenStreetMap did not answer and the tile is not cached |
| 503 | `busy` | four analyses already running; retry in a few seconds |
| 429 | `rate_limited` | more than 10 analyses per minute from one address (a burst of 5 is allowed), or too many tiles at once; sent by nginx |
