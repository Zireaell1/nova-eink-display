import os
import datetime
import logging
from PIL import ImageFont

from src.dashboard.config import FONT_DIR

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
        self.title = self.load_font("slkscr.ttf", 16)
        self.mono = self.load_font("slkscr.ttf", 8)
        self.mono_sm = self.load_font("slkscr.ttf", 8)
        self.mono_lg = self.load_font("slkscr.ttf", 8)

theme = Theme()

class BaseScreen:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height

    def draw_header(self, draw, title: str = "root@nova:~#", invert: bool = False):
        now = datetime.datetime.now().strftime("%H:%M")

        bg_color = 255 if invert else 0
        fg_color = 0 if invert else 255

        draw.rectangle((0, 0, self.width, 16), fill=bg_color)

        draw.text((4, 8), title, font=theme.mono_sm, fill=fg_color, anchor="lm")

        draw.text((self.width - 4, 8), now, font=theme.mono_sm, fill=fg_color, anchor="rm")

    def draw_footer(self, draw, ups_val: float, uptime: str = ""):
        ups_status = "OK" if ups_val > 90 else "WARN"
        left_text = f"UPS:[{ups_status}] {int(ups_val)}%"
        right_text = f"UP: {uptime}"

        draw.rectangle((0, 112, self.width, 128), fill=255)
        draw.line((0, 112, self.width, 112), fill=0, width=1) 

        draw.text((4, 120), left_text, font=theme.mono_sm, fill=0, anchor="lm")
        
        draw.text((self.width - 4, 120), right_text, font=theme.mono_sm, fill=0, anchor="rm")
