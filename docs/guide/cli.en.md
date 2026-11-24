# The command line

`talax` runs the same analysis as the site, but **on your computer**: the file
never leaves it. It is the right choice for a sensitive file, and the only way
to analyse a whole folder.

## 1. Install

You need two things: **Tala X** and **ExifTool 13 or newer**, the program that
reads metadata. Tala X refuses to run with an older ExifTool, which would give
different results.

### Windows

Everything happens in **PowerShell** (Start menu, type "PowerShell").

**1. Install uv**, which installs Tala X and the right version of Python:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close PowerShell, open it again, then check: `uv --version`.

**2. Install ExifTool:**

1. On <https://exiftool.org/>, download the Windows 64-bit version (file
   `exiftool-XX.XX_64.zip`).
2. Unzip it into `C:\Tools\`, then rename the folder to `exiftool`.
3. In that folder, rename `exiftool(-k).exe` to `exiftool.exe`. Keep the
   `exiftool_files` folder next to it: ExifTool needs it.
4. Add the folder to your account's PATH:

   ```powershell
   $p = [Environment]::GetEnvironmentVariable("Path", "User")
   [Environment]::SetEnvironmentVariable("Path", "$p;C:\Tools\exiftool", "User")
   ```

5. Close PowerShell, open it again, then check: `exiftool -ver` (13 or more).

**3. Install Tala X:**

```powershell
uv tool install talax
talax version
```

### macOS

In the Terminal:

```bash
brew install exiftool uv
uv tool install talax
talax version
```

(Without Homebrew: install uv with `curl -LsSf https://astral.sh/uv/install.sh | sh`,
and ExifTool from the macOS package on <https://exiftool.org/>.)

### Linux

Distribution packages of ExifTool are often too old (Ubuntu 24.04 ships
12.76). Install the latest version in your home folder:

```bash
v=$(curl -fsS https://exiftool.org/ver.txt)
mkdir -p ~/.local/opt ~/.local/bin
curl -fsSL "https://sourceforge.net/projects/exiftool/files/Image-ExifTool-$v.tar.gz/download" | tar -xz -C ~/.local/opt
ln -sf ~/.local/opt/Image-ExifTool-$v/exiftool ~/.local/bin/exiftool
exiftool -ver
```

Then Tala X:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install talax
talax version
```

### With pip, if you prefer

Tala X needs Python 3.12 or newer:

```bash
python3 -m venv ~/talax-env
source ~/talax-env/bin/activate        # PowerShell: ~\talax-env\Scripts\Activate.ps1
pip install talax
```

### Update, uninstall

```bash
uv tool upgrade talax       # or: pip install --upgrade talax
uv tool uninstall talax     # or: pip uninstall talax
```

The installation weighs about 200 MB, mostly because of the libraries that
read C2PA credentials and find the time zone of a position without internet.

## 2. Analyse a photo: `talax analyze`

```bash
talax analyze photo.jpg
```

The report appears in the terminal: the integrity result, then each check with
its state and explanation. For a copy, the message to send to the source; for
every photo, the reverse image search links. See
[Reading a report](report.en.md).

All the options:

| Option | What it does |
| --- | --- |
| `--lang en` | Language of the report (`en` or `fr`); by default, your system's |
| `--sky day` | What the photo shows: `day`, `twilight` or `night`, for solar consistency |
| `--place "-1.68,29.22" --at "2026-06-14 10:00"` | The place (latitude, longitude) and local time the caption claims; both together |
| `--weather` | Ask Open-Meteo for the weather; **the only option that uses the network** (see below) |
| `--conditions rain` | The weather the photo shows, with `--weather`: `rain`, `snow`, `overcast`, `clear` (clear sky or sharp shadows) |
| `--html report.html` | Also write a self-contained HTML report |
| `--json` | Print the analysis as JSON, for another program |

Examples:

```bash
# The report in English, and as HTML to keep it
talax analyze photo.jpg --lang en --html report.html

# The photo shows night: is that possible at the recorded time?
talax analyze photo.jpg --sky night

# The caption says "Goma, 14 June 2026 at 10 am", the photo shows daylight
talax analyze photo.jpg --place "-1.68,29.22" --at "2026-06-14 10:00" --sky day

# The photo shows rain: what does the weather model say?
talax analyze photo.jpg --place "-1.68,29.22" --at "2026-06-14 10:00" --weather --conditions rain
```

About `--weather`: your computer sends Open-Meteo the position rounded to about
11 km and the date, with your IP address; Open-Meteo may keep them 90 days.
Without this option, **nothing goes over the network**.

For a PDF: open the HTML report, print it (Ctrl+P, or ⌘P on a Mac) and choose
"Save as PDF".

## 3. Analyse a folder: `talax batch`

```bash
talax batch photos/
```

Tala X analyses every file in the folder (not its subfolders), four at a time,
then shows:

- **a table**: each file, its integrity, its capture time, its position, and
  the checks to look at first;
- **Same picture**: identical files, copies of the same photo, and very close
  images (an edit, or photos taken a moment apart);
- **Timeline**: the photos in the order they were taken;
- **Places**: the positions, and the widest distance between two photos.

Files Tala X does not recognise as images are left out and listed. You can also
give several files or folders: `talax batch photos/ other.jpg`.

| Option | What it does |
| --- | --- |
| `--lang en` | Language |
| `--html batch.html` | An HTML report of the batch (each file's details folded inside) |
| `--csv batch.csv` | A table to open in Excel or LibreOffice, one row per file (the file is replaced each time) |
| `--json` | The batch as JSON |

Example:

```bash
talax batch photos/ --lang en --html batch.html --csv batch.csv
```

The CSV uses the standard format (comma, decimal point). If Excel puts
everything in one column, open it through Data → From Text, with the comma as
separator.

The resemblance between images is computed from the pixels: check it by eye.
A cropped copy is usually not found, and a nearly uniform picture (all black,
for example) is not compared.

## 4. Other commands

```bash
talax version             # versions of Tala X and ExifTool
talax --help              # all the commands
talax analyze --help      # all the options of a command
```

## 5. When something goes wrong

| Message | What to do |
| --- | --- |
| `talax` is not recognised | With uv: `uv tool update-shell`, then open the terminal again. With pip: activate the virtual environment. |
| `exiftool` is not recognised, or "ExifTool is required but was not found" | ExifTool is not installed or not on the PATH (see Install). |
| "ExifTool … is too old" | Install ExifTool 13 or newer. |
| `--place and --at go together` | Give both options together. |
| `expected LAT,LON` | Write the latitude then the longitude in decimal degrees, separated by a comma: `"-1.68,29.22"`. |
| The reports contain positions | That is expected: they are the photos' own. Share them knowingly. |
