"""Structured run logger — writes JSONL execution log."""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Generator

from src.agent.state import AgentPhase


@dataclass
class RunLogEntry:
    step: int
    timestamp: str
    phase: str
    action: str
    target: str
    result: str  # "success", "failed", "skipped", "retry"
    reason: str
    duration_ms: int


class RunLogger:
    """Appends structured log entries to a JSONL file."""

    def __init__(self, log_path: Path):
        self._path = log_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self._path, "w", encoding="utf-8")
        self._step = 0

    def log(self, phase: AgentPhase, action: str, target: str,
            result: str, reason: str, duration_ms: int = 0) -> RunLogEntry:
        self._step += 1
        entry = RunLogEntry(
            step=self._step,
            timestamp=datetime.now().isoformat(),
            phase=phase.value,
            action=action,
            target=target,
            result=result,
            reason=reason,
            duration_ms=duration_ms,
        )
        self._file.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
        self._file.flush()
        return entry

    @contextmanager
    def timed(self, phase: AgentPhase, action: str, target: str = "") -> Generator[dict, None, None]:
        """Context manager that auto-logs with timing. Caller sets result/reason on the dict."""
        ctx = {"result": "success", "reason": ""}
        start = time.monotonic()
        try:
            yield ctx
        except Exception as e:
            ctx["result"] = "failed"
            ctx["reason"] = str(e)
            raise
        finally:
            elapsed = int((time.monotonic() - start) * 1000)
            self.log(phase, action, target, ctx["result"], ctx["reason"], elapsed)

    def close(self) -> None:
        if self._file and not self._file.closed:
            self._file.close()

    @property
    def step_count(self) -> int:
        return self._step
