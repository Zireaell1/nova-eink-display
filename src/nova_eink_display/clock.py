import time
from datetime import datetime, tzinfo


class Clock:
    """Wall-clock time, injectable."""

    def __init__(self, tz: tzinfo) -> None:
        self.tz = tz

    def time(self) -> float:
        return time.time()

    def now(self) -> datetime:
        return datetime.fromtimestamp(self.time(), self.tz)
