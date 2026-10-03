import logging

from PIL import Image

logger = logging.getLogger(__name__)


class DisplayDriver:
    """Draws what it is told. When to refresh, and how, is Panel's call."""

    def init(self) -> None:
        raise NotImplementedError

    def full(self, image: Image.Image) -> None:
        raise NotImplementedError

    def partial(self, image: Image.Image) -> None:
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

    @property
    def dimensions(self) -> tuple[int, int]:
        return self.w, self.h

    def init(self) -> None:
        logger.info("Initialized Simulated Display")

    def _save(self, image: Image.Image, kind: str) -> None:
        image.save("preview.png")
        logger.debug("Preview updated -> preview.png (%s)", kind)

    def full(self, image: Image.Image) -> None:
        self._save(image, "full")

    def partial(self, image: Image.Image) -> None:
        self._save(image, "partial")

    def sleep(self) -> None:
        logger.info("Simulated display asleep")


class EPDDisplay(DisplayDriver):
    def __init__(self) -> None:
        from nova_eink_display.lib import epd2in9

        self.epd = epd2in9.EPD()

    @property
    def dimensions(self) -> tuple[int, int]:
        return self.epd.height, self.epd.width

    def init(self) -> None:
        self.epd.init()
        self.epd.Clear(0xFF)

    def full(self, image: Image.Image) -> None:
        self.epd.init()
        self.epd.display_Base(self.epd.getbuffer(image))

    def partial(self, image: Image.Image) -> None:
        self.epd.display_Partial(self.epd.getbuffer(image))

    def sleep(self) -> None:
        logger.info("Putting panel into deep sleep")
        self.epd.sleep()
