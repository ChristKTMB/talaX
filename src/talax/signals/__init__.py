from talax.signals.base import Signal, run_signals
from talax.signals.c2pa_credentials import C2paCredentials
from talax.signals.capture_time import CaptureTime
from talax.signals.gps import GpsPosition
from talax.signals.real_format import RealFormat
from talax.signals.software import EditingSoftware

DEFAULT_SIGNALS: tuple[Signal, ...] = (
    RealFormat(),
    GpsPosition(),
    CaptureTime(),
    EditingSoftware(),
    C2paCredentials(),
)

__all__ = [
    "DEFAULT_SIGNALS",
    "C2paCredentials",
    "CaptureTime",
    "EditingSoftware",
    "GpsPosition",
    "RealFormat",
    "Signal",
    "run_signals",
]
