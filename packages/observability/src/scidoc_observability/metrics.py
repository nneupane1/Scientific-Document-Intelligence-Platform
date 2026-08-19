from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field


@dataclass(slots=True)
class PipelineMetrics:
    counters: Counter[str] = field(default_factory=Counter)
    timings: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))

    def increment(self, name: str, value: int = 1) -> None:
        self.counters[name] += value

    def observe(self, name: str, seconds: float) -> None:
        self.timings[name].append(seconds)

    def snapshot(self) -> dict[str, object]:
        averages = {
            name: sum(values) / len(values) for name, values in self.timings.items() if values
        }
        return {"counters": dict(self.counters), "average_seconds": averages}
