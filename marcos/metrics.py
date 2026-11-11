"""Per-turn latency measurement for the voice pipeline.

Voice assistants live or die by response time, so every turn records
how long each stage took and appends a row to ``logs/latency.csv``.
"""

from __future__ import annotations

import csv
import statistics
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, List

STAGES = ("stt", "llm", "tool", "tts")


class TurnTimer:
    def __init__(self) -> None:
        self.stages: Dict[str, float] = {}
        self._start = time.perf_counter()

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self.stages[name] = self.stages.get(name, 0.0) + (time.perf_counter() - t0) * 1000

    @property
    def total_ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000

    def row(self) -> Dict[str, float]:
        row = {s: round(self.stages.get(s, 0.0)) for s in STAGES}
        row["total"] = round(self.total_ms)
        return row


class LatencyLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.rows: List[Dict[str, float]] = []

    def add(self, timer: TurnTimer) -> Dict[str, float]:
        row = timer.row()
        self.rows.append(row)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        new_file = not self.path.exists()
        with self.path.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=[*STAGES, "total"])
            if new_file:
                writer.writeheader()
            writer.writerow(row)
        return row

    def summary(self) -> Dict[str, float]:
        """Median per stage over this session (empty if no turns)."""
        if not self.rows:
            return {}
        keys = [*STAGES, "total"]
        return {k: round(statistics.median(r[k] for r in self.rows)) for k in keys}
