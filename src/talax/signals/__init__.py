from talax.signals.base import Signal, run_signals
from talax.signals.real_format import RealFormat

DEFAULT_SIGNALS: tuple[Signal, ...] = (RealFormat(),)

__all__ = ["DEFAULT_SIGNALS", "RealFormat", "Signal", "run_signals"]
