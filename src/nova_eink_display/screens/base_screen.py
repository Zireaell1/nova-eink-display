import datetime
import logging
import os
from zoneinfo import ZoneInfo

from PIL import ImageDraw, ImageFont

from nova_eink_display.config import FONT_DIR, TIMEZONE
from nova_eink_display.layout import Layout

logger = logging.getLogger(__name__)


class Theme:
    @staticmethod
    def load_font(name: str, size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
        path = os.path.join(FONT_DIR, name)
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            logger.warning(f"Font '{name}' not found. Falling back to default.")
            return ImageFont.load_default()

    def __init__(self) -> None:
        self.mono = self.load_font("slkscr.ttf", 8)


theme = Theme()


class BaseScreen:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.layout = Layout(width, height)

    def draw_header(
        self,
        draw: ImageDraw.ImageDraw,
        title: str = "root@nova:~#",
        invert: bool = False,
        now: datetime.datetime | None = None,
        clock: str | None = None,
    ) -> None:
        if clock is None:
            now = now or datetime.datetime.now(ZoneInfo(TIMEZONE))
            clock = now.strftime("%H:%M")

        layout = self.layout
        bg_color = 255 if invert else 0
        fg_color = 0 if invert else 255

        draw.rectangle((0, 0, layout.width, layout.header_bottom), fill=bg_color)

        draw.text(
            (layout.margin, layout.header_middle),
            title,
            font=theme.mono,
            fill=fg_color,
            anchor="lm",
        )
        draw.text(
            (layout.width - layout.margin, layout.header_middle),
            clock,
            font=theme.mono,
            fill=fg_color,
            anchor="rm",
        )

    def draw_footer(
        self,
        draw: ImageDraw.ImageDraw,
        ups_val: float | None,
        uptime: str = "--",
    ) -> None:
        if ups_val is None:
            left_text = "UPS:[ -- ]"
        else:
            status = "OK" if ups_val > 90 else "WARN"
            left_text = f"UPS:[{status}] {ups_val:2.0f}%"

        right_text = f"UP: {uptime}"

        layout = self.layout
        draw.rectangle((0, layout.footer_top, layout.width, layout.height), fill=255)
        draw.line(
            (0, layout.footer_top, layout.width, layout.footer_top), fill=0, width=1
        )

        draw.text(
            (layout.margin, layout.footer_middle),
            left_text,
            font=theme.mono,
            fill=0,
            anchor="lm",
        )
        draw.text(
            (layout.width - layout.margin, layout.footer_middle),
            right_text,
            font=theme.mono,
            fill=0,
            anchor="rm",
        )
