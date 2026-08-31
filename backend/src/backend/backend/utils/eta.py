"""Shared "time remaining" estimator for long-running jobs (HLS conversion, plugin runs).

The backend never gets a per-iteration tick from ffmpeg or the analyser -- only a
coarse 0..1 progress fraction every second or so. This turns that into a smoothed
seconds-remaining number the same way tqdm does: keep an exponential moving average of
the progress *rate* and extrapolate it over the remaining fraction. Feed it whenever
progress moves; it returns ``None`` until the estimate is meaningful, so callers can
persist ``eta_seconds = None`` and the frontend knows to keep showing the
indeterminate ("starting up") bar.
"""

import time


class EtaEstimator:
    """Extrapolates seconds-to-completion from progress observations.

    ``smoothing`` is the weight of the most recent sample in the moving average
    (tqdm's default is 0.3): higher reacts faster, lower is steadier.
    """

    def __init__(self, smoothing: float = 0.3, clock=time.monotonic):
        self._smoothing = smoothing
        self._clock = clock
        self._last_t = clock()
        self._last_progress = None  # set by the first update() -- it's the baseline
        self._rate = None  # progress fraction per second, smoothed

    def update(self, progress) -> float | None:
        """Record a new progress value (0..1) and return the current estimate."""
        if progress is None:
            return self.seconds_remaining()
        progress = max(0.0, min(1.0, float(progress)))
        now = self._clock()
        if self._last_progress is None:
            # First observation is only a starting point -- a rate needs two.
            self._last_t = now
            self._last_progress = progress
            return None
        dt = now - self._last_t
        dp = progress - self._last_progress
        # Only learn from genuine forward motion -- progress is monotonic upstream, and
        # a zero/negative delta would just be noise from an unchanged poll.
        if dt > 0 and dp > 0:
            inst_rate = dp / dt
            if self._rate is None:
                self._rate = inst_rate
            else:
                self._rate = (
                    self._smoothing * inst_rate + (1.0 - self._smoothing) * self._rate
                )
        self._last_t = now
        self._last_progress = progress
        return self.seconds_remaining(progress)

    def seconds_remaining(self, progress=None) -> float | None:
        if progress is None:
            progress = self._last_progress
        if progress is None:
            return None
        if progress >= 1.0:
            return 0.0
        if not self._rate or self._rate <= 0.0:
            return None
        return (1.0 - progress) / self._rate
