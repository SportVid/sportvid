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
            self._last_t = now
            self._last_progress = progress
            return None
        dt = now - self._last_t
        dp = progress - self._last_progress

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
