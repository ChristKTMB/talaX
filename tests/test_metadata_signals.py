import dataclasses
from typing import Any

import pytest

from talax import Context, Metadata, State
from talax.signals import CaptureTime, EditingSoftware, GpsPosition


def with_tags(ctx: Context, **tags: Any) -> Context:
    return dataclasses.replace(
        ctx, metadata=Metadata({k.replace("__", ":"): v for k, v in tags.items()})
    )


# --- GPS -------------------------------------------------------------------


def test_gps_valid_position_names_its_accuracy(ctx: Context) -> None:
    result = GpsPosition().evaluate(
        with_tags(
            ctx,
            Composite__GPSLatitude=-4.39,
            Composite__GPSLongitude=15.37,
            GPS__GPSProcessingMethod="CELLID",
        )
    )
    assert result.state is State.CONSISTENT
    assert "cell towers" in result.explanation
    assert result.evidence["latitude"] == -4.39


def test_gps_positioning_error_wins_over_method(ctx: Context) -> None:
    result = GpsPosition().evaluate(
        with_tags(
            ctx,
            Composite__GPSLatitude=48.8,
            Composite__GPSLongitude=2.3,
            GPS__GPSHPositioningError=12.0,
        )
    )
    assert "12 m" in result.explanation


def test_gps_masked_fields_are_unverifiable_not_missing(ctx: Context) -> None:
    result = GpsPosition().evaluate(
        with_tags(
            ctx,
            GPS__GPSVersionID="0 0 0 0",
            GPS__GPSLatitude="",
            Composite__GPSLatitude="",
        )
    )
    assert result.state is State.UNVERIFIABLE
    assert result.evidence["masked"] is True
    assert "Android" in result.explanation


def test_gps_absent(ctx: Context) -> None:
    result = GpsPosition().evaluate(with_tags(ctx))
    assert result.state is State.UNVERIFIABLE
    assert result.evidence == {"gps_block": False}


@pytest.mark.parametrize(("lat", "lon"), [(0, 0), (95.0, 10.0), (10.0, -200.0)])
def test_gps_impossible_positions_are_to_check(
    ctx: Context, lat: float, lon: float
) -> None:
    result = GpsPosition().evaluate(
        with_tags(ctx, Composite__GPSLatitude=lat, Composite__GPSLongitude=lon)
    )
    assert result.state is State.TO_CHECK


# --- Date and time ----------------------------------------------------------

BASE = {
    "ExifIFD__DateTimeOriginal": "2026:10:31 09:58:41",
    "ExifIFD__SubSecTimeOriginal": "696",
    "ExifIFD__CreateDate": "2026:10:31 09:58:41",
    "IFD0__ModifyDate": "2026:10:31 09:58:41",
    "Samsung__TimeStamp": "2026:10:31 09:58:40.256+01:00",
    "Composite__GPSDateTime": "2026:10:31 08:58:31Z",
}


def capture(ctx: Context, **changes: Any) -> Any:
    tags = {k: v for k, v in {**BASE, **changes}.items() if v is not None}
    return CaptureTime().evaluate(with_tags(ctx, **tags))


def test_agreeing_clocks_are_consistent_and_offset_comes_from_vendor(
    ctx: Context,
) -> None:
    result = capture(ctx)
    assert result.state is State.CONSISTENT
    assert result.evidence["offset"] == "+01:00"
    assert result.evidence["offset_source"] == "vendor"
    assert "5 clocks" in result.explanation


def test_exif_offset_is_preferred(ctx: Context) -> None:
    result = capture(ctx, ExifIFD__OffsetTimeOriginal="+02:00", Samsung__TimeStamp=None)
    assert result.evidence["offset"] == "+02:00"


def test_capture_time_differing_from_vendor_clock_is_suspicious(
    ctx: Context,
) -> None:
    result = capture(ctx, ExifIFD__DateTimeOriginal="2025:06:01 21:00:00")
    assert result.state is State.SUSPICIOUS
    assert "changed after" in result.explanation


def test_small_vendor_gap_is_tolerated(ctx: Context) -> None:
    result = capture(ctx, Samsung__TimeStamp="2026:10:31 09:58:47+01:00")
    assert result.state is State.CONSISTENT


def test_later_modification_is_to_check(ctx: Context) -> None:
    result = capture(ctx, IFD0__ModifyDate="2026:11:02 18:00:00")
    assert result.state is State.TO_CHECK
    assert "saved again" in result.explanation


def test_gps_clock_far_from_capture_is_to_check(ctx: Context) -> None:
    result = capture(ctx, Composite__GPSDateTime="2026:10:31 06:00:00Z")
    assert result.state is State.TO_CHECK
    assert "GPS clock" in result.explanation


def test_without_offset_gps_must_differ_by_a_whole_time_zone(ctx: Context) -> None:
    ok = capture(ctx, Samsung__TimeStamp=None)
    assert ok.state is State.CONSISTENT
    assert "time zone not recorded" in ok.explanation
    off = capture(
        ctx, Samsung__TimeStamp=None, Composite__GPSDateTime="2026:10:31 08:21:00Z"
    )
    assert off.state is State.TO_CHECK


@pytest.mark.parametrize("value", [None, "", "0000:00:00 00:00:00", "garbage"])
def test_missing_or_unreadable_capture_time(ctx: Context, value: Any) -> None:
    result = capture(ctx, ExifIFD__DateTimeOriginal=value)
    assert result.state is State.UNVERIFIABLE


def test_masked_gps_clock_is_ignored(ctx: Context) -> None:
    result = capture(ctx, Composite__GPSDateTime=" 00:00:00Z")
    assert result.state is State.CONSISTENT


# --- Editing software -------------------------------------------------------


def test_known_editor_is_to_check(ctx: Context) -> None:
    # XMP group names contain a dash, so the key is built explicitly.
    result = EditingSoftware().evaluate(
        dataclasses.replace(
            ctx,
            metadata=Metadata({"XMP-xmp:CreatorTool": "Adobe Photoshop 25.0"}),
        )
    )
    assert result.state is State.TO_CHECK
    assert "Photoshop" in result.explanation


def test_photoshop_block_alone_is_to_check(ctx: Context) -> None:
    result = EditingSoftware().evaluate(with_tags(ctx, Photoshop__IPTCDigest="x"))
    assert result.state is State.TO_CHECK


def test_camera_firmware_is_consistent_but_says_the_list_is_limited(
    ctx: Context,
) -> None:
    result = EditingSoftware().evaluate(with_tags(ctx, IFD0__Software="A346BXXSHFZJ4"))
    assert result.state is State.CONSISTENT
    assert "limited" in result.explanation


def test_no_software_is_unverifiable(ctx: Context) -> None:
    result = EditingSoftware().evaluate(with_tags(ctx))
    assert result.state is State.UNVERIFIABLE
