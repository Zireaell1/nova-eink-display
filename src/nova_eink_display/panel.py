import logging

from PIL import Image

from nova_eink_display.display import DisplayDriver
from nova_eink_display.metrics import METRICS, Metrics
from nova_eink_display.state import WearState

logger = logging.getLogger(__name__)


class Panel:
    """The only code that refreshes the glass. Callers hand it complete
    frames; it decides partial or full, keeps the ghosting budget, sleeps and
    wakes the panel, and records every refresh and the wear it costs."""

    def __init__(
        self,
        driver: DisplayDriver,
        wear: WearState,
        max_partials: int,
        metrics: Metrics = METRICS,
    ) -> None:
        self.driver = driver
        self.wear = wear
        self.max_partials = max_partials
        self.metrics = metrics

        self.partials = 0
        self.asleep = False

    @property
    def partials_left(self) -> int:
        return self.max_partials - self.partials

    def start(self) -> None:
        self.driver.init()
        self.partials = 0
        self.asleep = False

    def show(self, image: Image.Image, full: bool = False) -> None:
        if self.asleep:
            logger.debug("Waking panel")
            full = True

        if self.partials >= self.max_partials:
            full = True

        if full:
            self.driver.full(image)
            self.partials = 0
        else:
            self.driver.partial(image)
            self.partials += 1

        self.asleep = False

        self.metrics.record_refresh("full" if full else "partial", self.partials)
        self.metrics.record_frame(image)
        self.wear.save(self.metrics.snapshot())

    def sleep(self) -> None:
        if self.asleep:
            return

        self.driver.sleep()
        self.asleep = True
