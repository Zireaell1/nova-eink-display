import datetime
import logging

from PIL import Image, ImageChops, ImageDraw

from nova_eink_display.character import Character
from nova_eink_display.config import INVERT_COLORS
from nova_eink_display.layout import Layout
from nova_eink_display.screens.base_screen import theme
from nova_eink_display.screens.main_screen import MainScreen

logger = logging.getLogger(__name__)


class UIRenderer:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.layout = Layout(width, height)

        self.main_screen = MainScreen(width, height)
        self.character = Character()

        self._warned_sizes: set[str] = set()

    def _new_frame(self) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        image = Image.new("1", (self.width, self.height), 255)
        return image, ImageDraw.Draw(image)

    def _finish(self, image: Image.Image, invert: bool | None) -> Image.Image:
        if INVERT_COLORS if invert is None else invert:
            return ImageChops.invert(image)

        return image

    def _check_size(self, mood: str, image: Image.Image) -> None:
        max_width, max_height = self.layout.character_max_size
        if (
            image.width <= max_width
            and image.height <= max_height
            or mood in self._warned_sizes
        ):
            return

        self._warned_sizes.add(mood)
        logger.warning(
            "character-%s.png is %sx%s; at most %sx%s fits between the stats "
            "column and the footer, so it will be clipped",
            mood,
            image.width,
            image.height,
            max_width,
            max_height,
        )

    def _draw_character(
        self,
        image: Image.Image,
        draw: ImageDraw.ImageDraw,
        stats: dict[str, float],
        sys_error: str | None,
        alerts: list[str],
        is_blinking: bool,
        now: datetime.datetime | None,
    ) -> None:
        character_image, mood = self.character.get_current_image(
            stats, sys_error, alerts, is_blinking, now
        )

        if character_image:
            self._check_size(mood, character_image)
            paste_x = self.width - character_image.width
            image.paste(character_image, (paste_x, self.layout.header_bottom))
            return

        box = self.layout.character_box
        draw.rectangle(box, outline=0)

        cx = (box[0] + box[2]) // 2
        cy = (box[1] + box[3]) // 2
        draw.text((cx, cy - 12), "IMG MISSING", font=theme.mono, fill=0, anchor="mm")
        draw.text((cx, cy + 4), mood.upper(), font=theme.mono, fill=0, anchor="mm")

    def render_frame(
        self,
        data: dict,
        active_alerts: list[str],
        is_blinking: bool = False,
        now: datetime.datetime | None = None,
        invert: bool | None = None,
    ) -> Image.Image:
        image, draw = self._new_frame()

        self._draw_character(
            image,
            draw,
            data.get("stats", {}),
            data.get("error"),
            active_alerts,
            is_blinking,
            now,
        )
        self.main_screen.draw(draw, data, active_alerts, now=now)

        return self._finish(image, invert)

    def render_sleep_frame(
        self, now: datetime.datetime, wake_hour: int, invert: bool | None = None
    ) -> Image.Image:
        image, draw = self._new_frame()

        self._draw_character(image, draw, {}, None, [], False, now)
        self.main_screen.draw_asleep(draw, now, wake_hour)

        return self._finish(image, invert)

    def render_offline_frame(
        self, now: datetime.datetime, invert: bool | None = None
    ) -> Image.Image:
        image, draw = self._new_frame()

        self._draw_character(image, draw, {}, "OFFLINE", [], False, now)
        self.main_screen.draw_offline(draw, now)

        return self._finish(image, invert)
