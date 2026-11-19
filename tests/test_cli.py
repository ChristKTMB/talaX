import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from talax.cli import app

pytestmark = pytest.mark.skipif(
    shutil.which("exiftool") is None, reason="ExifTool needed"
)
runner = CliRunner()
HOSTILE = "[red]evil[/red]\x1b[2J<script>alert(1)</script>"


@pytest.fixture
def hostile_jpeg(tmp_path: Path) -> Path:
    path = tmp_path / "photo.jpg"
    Image.new("RGB", (64, 48), (120, 160, 200)).save(path, quality=90)
    subprocess.run(
        ["exiftool", "-q", "-overwrite_original", f"-IFD0:Software={HOSTILE}", path],
        check=True,
    )
    return path


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.output.startswith("talax ")


def test_text_output_neutralises_markup_and_control_codes(hostile_jpeg: Path) -> None:
    result = runner.invoke(app, ["analyze", str(hostile_jpeg)])
    assert result.exit_code == 0, result.output
    assert "\x1b[2J" not in result.output
    assert "[red]evil[/red]" in result.output  # shown literally, not as markup
    assert "never certifies" in result.output


def test_json_output_is_valid_and_has_no_banner(hostile_jpeg: Path) -> None:
    result = runner.invoke(app, ["analyze", str(hostile_jpeg), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["schema"] == 2
    assert data["lang"] == "en"
    assert all(r["message"] for r in data["results"])
    assert data["file"]["name"] == "photo.jpg"
    assert {r["signal"] for r in data["results"]} >= {"gps", "solar", "c2pa"}
    assert "See beyond" not in result.output


def test_sky_option_reaches_the_solar_signal(hostile_jpeg: Path) -> None:
    result = runner.invoke(
        app, ["analyze", str(hostile_jpeg), "--sky", "night", "--json"]
    )
    solar = next(
        r for r in json.loads(result.output)["results"] if r["signal"] == "solar"
    )
    assert solar["state"] == "unverifiable"  # no position in this file


def test_html_report_is_escaped_and_self_contained(
    hostile_jpeg: Path, tmp_path: Path
) -> None:
    report = tmp_path / "report.html"
    result = runner.invoke(app, ["analyze", str(hostile_jpeg), "--html", str(report)])
    assert result.exit_code == 0
    html = report.read_text()
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
    assert "default-src 'none'" in html
    # No external resource: every URL in the page is a data: URI.
    assert not re.search(r"(src|href)=\"(?!data:)", html)
    assert "Visual exploration" in html and "not conclusive" in html


def test_html_report_prints_to_pdf_without_any_script(
    hostile_jpeg: Path, tmp_path: Path
) -> None:
    report = tmp_path / "report.html"
    runner.invoke(app, ["analyze", str(hostile_jpeg), "--html", str(report)])
    html = report.read_text()
    # The way to a PDF is the browser's print dialog, explained on screen.
    assert "Save as PDF" in html
    assert "@media print" in html
    # Raw values are printed open, since closed <details> would print empty.
    assert html.count("Raw values") == 2 * html.count("<details>")
    # No script, not even for a print button: the report shows hostile metadata.
    assert "<script" not in html.lower()
    assert "onclick" not in html.lower()


def test_report_dates_are_written_in_words() -> None:
    from datetime import UTC, datetime, timedelta, timezone

    from talax.i18n import Language
    from talax.report import readable_date

    moment = datetime(2026, 11, 19, 13, 58, tzinfo=timezone(timedelta(hours=1)))
    assert readable_date(moment, Language.EN) == "19 November 2026, 12:58 UTC"
    assert readable_date(moment, Language.FR) == "19 novembre 2026 à 12:58 UTC"
    assert readable_date(datetime(2026, 8, 1, tzinfo=UTC), Language.FR).startswith(
        "1 août 2026"
    )


def test_bad_sky_value_is_a_usage_error(hostile_jpeg: Path) -> None:
    result = runner.invoke(app, ["analyze", str(hostile_jpeg), "--sky", "noon"])
    assert result.exit_code == 2


def test_missing_file_is_a_usage_error(tmp_path: Path) -> None:
    result = runner.invoke(app, ["analyze", str(tmp_path / "nope.jpg")])
    assert result.exit_code == 2


def test_french_everywhere(hostile_jpeg: Path, tmp_path: Path) -> None:
    report = tmp_path / "rapport.html"
    text_out = runner.invoke(
        app, ["analyze", str(hostile_jpeg), "--lang", "fr", "--html", str(report)]
    )
    assert text_out.exit_code == 0
    assert "Intégrité" in text_out.output and "ne certifie jamais" in text_out.output

    data = json.loads(
        runner.invoke(
            app, ["analyze", str(hostile_jpeg), "--lang", "fr", "--json"]
        ).output
    )
    assert data["lang"] == "fr"
    assert data["integrity"]["label"] in {
        "Original d'appareil",
        "Copie retraitée",
        "Indéterminé",
    }

    html = report.read_text(encoding="utf-8")
    assert '<html lang="fr">' in html and "Signaux" in html


def test_system_language_is_the_default(hostile_jpeg: Path) -> None:
    result = runner.invoke(
        app, ["analyze", str(hostile_jpeg)], env={"LANG": "fr_FR.UTF-8", "LC_ALL": ""}
    )
    assert "Intégrité" in result.output


def test_serve_without_the_server_extra_says_what_to_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import builtins

    real_import = builtins.__import__

    def no_uvicorn(name: str, *args: object, **kwargs: object) -> object:
        if name == "uvicorn":
            raise ImportError(name)
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", no_uvicorn)
    result = runner.invoke(app, ["serve"])
    assert result.exit_code == 1
    assert "pip install talax[server]" in result.output


def test_a_copy_comes_with_a_message_for_the_source(
    hostile_jpeg: Path, tmp_path: Path
) -> None:
    from dataclasses import replace

    from talax.analysis import analyze
    from talax.i18n import Language
    from talax.model import IntegrityVerdict
    from talax.report import source_request

    data = json.loads(
        runner.invoke(app, ["analyze", str(hostile_jpeg), "--json"]).output
    )
    assert data["integrity"]["verdict"] != "original"
    request = data["source_request"]
    assert '"Document"' in request["message"] and "serial number" in request["caution"]

    text_out = runner.invoke(app, ["analyze", str(hostile_jpeg), "--lang", "fr"]).output
    assert "Demander l'original" in text_out and "«\u00a0Document\u00a0»" in text_out

    report = tmp_path / "report.html"
    runner.invoke(app, ["analyze", str(hostile_jpeg), "--html", str(report)])
    assert "Ask for the original" in report.read_text()

    # A camera original needs nothing more from the source.
    analysis = analyze(hostile_jpeg)
    original = replace(
        analysis,
        integrity=replace(analysis.integrity, verdict=IntegrityVerdict.ORIGINAL),
    )
    assert source_request(original, Language.EN) is None
