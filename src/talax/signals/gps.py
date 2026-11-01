"""Where the photo was taken, as recorded by the device."""

from __future__ import annotations

from talax.i18n import Message
from talax.model import Context, Result, State

# Values of GPSProcessingMethod with a message explaining their accuracy.
_METHODS = {"GPS", "CELLID", "WLAN", "NETWORK", "FUSED"}


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
                    Message("gps.masked"),
                    {"gps_block": True, "masked": True},
                )
            return Result(
                self.id,
                State.UNVERIFIABLE,
                Message("gps.absent"),
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
        # Coordinates keep a decimal point in every language.
        where = {"lat": f"{lat:.5f}", "lon": f"{lon:.5f}"}

        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return Result(
                self.id,
                State.TO_CHECK,
                Message("gps.out_of_range", where),
                evidence,
            )
        if lat == 0 and lon == 0:
            return Result(
                self.id,
                State.TO_CHECK,
                Message("gps.null_island"),
                evidence,
            )
        return Result(
            self.id,
            State.CONSISTENT,
            Message("gps.consistent", {**where, "accuracy": _accuracy(evidence)}),
            evidence,
        )


def _accuracy(evidence: dict[str, object]) -> Message:
    error = evidence["error_m"]
    if _is_number(error):
        return Message("gps.accuracy.error", {"metres": float(error)})  # type: ignore[arg-type]
    method = str(evidence["method"] or "").strip().upper()
    if method in _METHODS:
        return Message(f"gps.accuracy.{method.lower()}")
    if method:
        return Message("gps.accuracy.other_method", {"method": method})
    return Message("gps.accuracy.unknown")


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)
