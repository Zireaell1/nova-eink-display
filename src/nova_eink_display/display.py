import logging

logger = logging.getLogger(__name__)


class DisplayDriver:
    partial_count = 0

    def init(self):
        raise NotImplementedError

    def render(self, image, full_refresh=False):
        raise NotImplementedError

    def sleep(self):
        raise NotImplementedError

    def cleanup(self):
        raise NotImplementedError

    @property
    def dimensions(self):
        raise NotImplementedError


class SimulatedDisplay(DisplayDriver):
    def __init__(self, width=296, height=128):
        self.w = width
        self.h = height
        self.partial_count = 0
        self.asleep = False

    @property
    def dimensions(self):
        return self.w, self.h

    def init(self):
        logger.info("Initialized Simulated Display")

    def render(self, image, full_refresh=False):
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

    def sleep(self):
        if not self.asleep:
            logger.info("Simulated display asleep")
            self.asleep = True

    def cleanup(self):
        logger.info("Cleaned up simulated display.")


class EPDDisplay(DisplayDriver):
    def __init__(self):
        from nova_eink_display.lib import epd2in9

        self.epd = epd2in9.EPD()
        self.partial_count = 0
        self.asleep = False

    @property
    def dimensions(self):
        return self.epd.height, self.epd.width

    def init(self):
        self.epd.init()
        self.epd.Clear(0xFF)
        self.partial_count = 0
        self.asleep = False

    def render(self, image, full_refresh=False):
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

    def sleep(self):
        if self.asleep:
            return

        logger.info("Putting panel into deep sleep")
        self.epd.sleep()
        self.asleep = True

    def cleanup(self):
        if self.asleep:
            self.epd.init()
            self.asleep = False

        self.epd.Clear(0xFF)
        self.epd.sleep()
        self.asleep = True
