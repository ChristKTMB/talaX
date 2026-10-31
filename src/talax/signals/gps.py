"""Where the photo was taken, as recorded by the device."""

from __future__ import annotations

from talax.model import Context, Result, State

# Values of GPSProcessingMethod and what they mean for accuracy.
_METHODS = {
    "GPS": "satellite positioning",
    "CELLID": "the mobile network (cell towers); approximate, it can be off "
    "by hundreds of metres or more",
    "WLAN": "nearby Wi-Fi networks; approximate",
    "NETWORK": "the network (cell towers or Wi-Fi); approximate",
    "FUSED": "a mix of satellite and network positioning",
}


class GpsPosition:
    id = "gps"
    name = "GPS position"

    def is_relevant(self, ctx: Context) -> bool:
        return True

    def evaluate(self, ctx: Context) -> Result:
        tags = ctx.metadata
        lat = tags.get("Composite:GPSLatitude")
        lon = tags.get("Composite:GPSLongitude")
        has_gps_block = any(k.startswith("GPS:") for k in tags.tags)

        if not _is_number(lat) or not _is_number(lon):
            if has_gps_block:
                return Result(
                    self.id,
                    State.UNVERIFIABLE,
                    "The file has a GPS block, but its position fields are "
                    "blank. This matches how Android hides the location of a "
                    "photo shared through an app that is not allowed to see "
                    "it. The position cannot be recovered from this file; ask "
                    "the source for the original copied by cable.",
                    {"gps_block": True, "masked": True},
                )
            return Result(
                self.id,
                State.UNVERIFIABLE,
                "No position is recorded. Location was off on the device, or "
                "the metadata was removed afterwards.",
                {"gps_block": False},
            )

        assert isinstance(lat, int | float) and isinstance(lon, int | float)
        evidence: dict[str, object] = {
            "latitude": lat,
            "longitude": lon,
            "altitude_m": tags.get("Composite:GPSAltitude"),
            "method": tags.get("GPS:GPSProcessingMethod") or None,
            "error_m": tags.get("GPS:GPSHPositioningError"),
        }
        where = f"{lat:.5f}, {lon:.5f}"

        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return Result(
                self.id,
                State.TO_CHECK,
                f"The recorded position ({where}) is outside the valid range: "
                "the GPS data is corrupted or was written by hand.",
                evidence,
            )
        if lat == 0 and lon == 0:
            return Result(
                self.id,
                State.TO_CHECK,
                "The recorded position is exactly 0, 0 (in the Gulf of "
                "Guinea). Devices write this when they had no fix, so it is "
                "almost certainly not where the photo was taken.",
                evidence,
            )
        return Result(
            self.id,
            State.CONSISTENT,
            f"Position recorded: {where}. {_accuracy(evidence)} A recorded "
            "position says where the device placed itself, which can be "
            "edited like any metadata.",
            evidence,
        )


def _accuracy(evidence: dict[str, object]) -> str:
    error = evidence["error_m"]
    if _is_number(error):
        return f"The device estimated its accuracy at {error:.0f} m."
    method = str(evidence["method"] or "").strip().upper()
    if method in _METHODS:
        return f"It comes from {_METHODS[method]}."
    if method:
        return f"Positioning method: {method}; accuracy not recorded."
    return "Accuracy is not recorded."


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)
