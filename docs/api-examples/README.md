# API response examples

Real answers of `POST /api/analyze`, in English (`.en.json`) and French
(`.fr.json`), for designing and testing the front. Only `created_at` is
fixed, to keep diffs readable.

**Every file analysed is synthetic**, built by
[`scripts/api_examples.py`](../../scripts/api_examples.py) with Pillow and
ExifTool ("Generic Camera 1", a position in Paris). No photo of the corpus is
used: they carry real positions and device serial numbers. That a few
ExifTool commands make a "camera original" is the limit stated in the
threat model: Tala X does not protect against someone who forges metadata.

| Example | Situation |
| --- | --- |
| `camera-original` | camera original with GPS; the user said "day" |
| `camera-original-no-sky` | same file, sky not given yet: the solar check describes what the photo should show |
| `solar-contradiction` | same file, the user said "night" at 13:50 in June in Paris |
| `gps-masked` | the GPS block is there but emptied (seen on Android after sharing) |
| `edited` | an image editor is recorded |
| `platform-copy` | matches the WhatsApp fingerprint |
| `wrong-extension` | the same copy, named `.png` |
| `png-without-metadata` | a PNG with no metadata at all |
| `weather-asked` | the camera original, weather lookup asked, the photo's weather not given yet (the model answer is fixed: no call to Open-Meteo) |
| `weather-to-check` | same, the user said "rain" while the model has none |
| `declared-copy` | the WhatsApp copy, with the place and time the caption claims (manual mode) and "day" |
| `declared-elsewhere` | the camera original, with a caption that places it in Lyon, about 390 km from its GPS |
| `error-*` | one example of each error a user can meet |

Regenerate after any change to the API or the messages:

```sh
uv run python scripts/api_examples.py
```

`tests/test_api_examples.py` fails when these files no longer match what the
API answers.
