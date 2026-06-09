import logging

class DisplayDriver:
    def init(self): raise NotImplementedError
    def render(self, image, full_refresh=False): raise NotImplementedError
    def cleanup(self): raise NotImplementedError
    @property
    def dimensions(self): raise NotImplementedError

class SimulatedDisplay(DisplayDriver):
    def __init__(self, width=296, height=128):
        self.w = width
        self.h = height

    @property
    def dimensions(self):
        return self.w, self.h

    def init(self):
        logging.info("Initialized Simulated Display")

    def render(self, image, full_refresh=False):
        image.save("preview.png")
        logging.info("Preview updated -> preview.png")

    def cleanup(self):
        logging.info("Cleaned up simulated display.")

class EPDDisplay(DisplayDriver):
    def __init__(self):
        from lib import epd2in9_V2
        self.epd = epd2in9_V2.EPD()

    @property
    def dimensions(self):
        return self.epd.height, self.epd.width

    def init(self):
        self.epd.init()
        self.epd.Clear(0xFF)

    def render(self, image, full_refresh=False):
        if full_refresh:
            self.epd.init()
            self.epd.display_Base(self.epd.getbuffer(image))
        else:
            self.epd.display_Partial(self.epd.getbuffer(image))

    def cleanup(self):
        self.epd.init()
        self.epd.Clear(0xFF)
        self.epd.sleep()
