from __future__ import annotations

import resource
from dataclasses import dataclass
from time import perf_counter


@dataclass(slots=True)
class PerformanceMeasurement:
    started: float

    @classmethod
    def start(cls) -> PerformanceMeasurement:
        return cls(perf_counter())

    def finish(self, pages: int) -> dict[str, float]:
        elapsed = perf_counter() - self.started
        return {
            "runtime_seconds": elapsed,
            "seconds_per_page": elapsed / pages if pages else 0.0,
            "max_rss_kb": float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        }
