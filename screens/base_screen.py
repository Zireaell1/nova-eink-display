import os
import datetime
import logging
from PIL import ImageFont

from config import FONT_DIR

class Theme:
    @staticmethod
    def load_font(name: str, size: int):
        path = os.path.join(FONT_DIR, name)
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            logging.warning(f"Font '{name}' not found. Falling back to default.")
            return ImageFont.load_default()

    def __init__(self):
        self.title = self.load_font("DejaVuSans-Bold.ttf", 16)
        self.mono = self.load_font("DejaVuSansMono.ttf", 12)
        self.mono_sm = self.load_font("DejaVuSansMono.ttf", 10)
        self.mono_lg = self.load_font("DejaVuSansMono.ttf", 18)

theme = Theme()

class BaseScreen:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height

    def draw_terminal_header(self, draw, title: str = "root@homelab:~#", invert: bool = False):
        now = datetime.datetime.now().strftime("%H:%M")

        bg_color = 255 if invert else 0
        fg_color = 0 if invert else 255

        draw.rectangle((0, 0, self.width, 18), fill=bg_color)

        draw.text((4, 2), title, font=theme.mono, fill=fg_color)

        tw = draw.textlength(now, font=theme.mono)
        draw.text((self.width - tw - 4, 2), now, font=theme.mono, fill=fg_color)
