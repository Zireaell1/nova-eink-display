import logging

from PIL import Image

logger = logging.getLogger(__name__)


class DisplayDriver:
    partial_count = 0

    asleep = False

    def init(self) -> None:
        raise NotImplementedError

    def render(self, image: Image.Image, full_refresh: bool = False) -> None:
        raise NotImplementedError

    def sleep(self) -> None:
        """Power the panel down, leaving the current frame on screen."""
        raise NotImplementedError

    @property
    def dimensions(self) -> tuple[int, int]:
        raise NotImplementedError


class SimulatedDisplay(DisplayDriver):
    def __init__(self, width: int = 296, height: int = 128) -> None:
        self.w = width
        self.h = height
        self.partial_count = 0
        self.asleep = False

    @property
    def dimensions(self) -> tuple[int, int]:
        return self.w, self.h

    def init(self) -> None:
        logger.info("Initialized Simulated Display")

    def render(self, image: Image.Image, full_refresh: bool = False) -> None:
        if self.asleep:
            logger.debug("Waking simulated display")
            self.asleep = False
            full_refresh = True

        if full_refresh:
            self.partial_count = 0
        else:
            self.partial_count += 1

        image.save("preview.png")
        logger.debug(
            "Preview updated -> preview.png (%s, %d partials since full)",
            "full" if full_refresh else "partial",
            self.partial_count,
        )

    def sleep(self) -> None:
        if not self.asleep:
            logger.info("Simulated display asleep")
            self.asleep = True


class EPDDisplay(DisplayDriver):
    def __init__(self) -> None:
        from nova_eink_display.lib import epd2in9

        self.epd = epd2in9.EPD()
        self.partial_count = 0
        self.asleep = False

    @property
    def dimensions(self) -> tuple[int, int]:
        return self.epd.height, self.epd.width

    def init(self) -> None:
        self.epd.init()
        self.epd.Clear(0xFF)
        self.partial_count = 0
        self.asleep = False

    def render(self, image: Image.Image, full_refresh: bool = False) -> None:
        if self.asleep:
            logger.debug("Waking panel from deep sleep")
            self.asleep = False
            full_refresh = True

        buffer = self.epd.getbuffer(image)

        if full_refresh:
            self.epd.init()
            self.epd.display_Base(buffer)
            self.partial_count = 0
        else:
            self.epd.display_Partial(buffer)
            self.partial_count += 1

    def sleep(self) -> None:
        if self.asleep:
            return

        logger.info("Putting panel into deep sleep")
        self.epd.sleep()
        self.asleep = True
