from PIL import Image, ImageChops, ImageDraw

from nova_eink_display.character import Character
from nova_eink_display.config import INVERT_COLORS
from nova_eink_display.screens.base_screen import theme
from nova_eink_display.screens.main_screen import MainScreen

CHARACTER_BOX = (136, 16, 295, 112)


class UIRenderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.main_screen = MainScreen(width, height)
        self.character = Character()

    def _new_frame(self):
        image = Image.new("1", (self.width, self.height), 255)
        return image, ImageDraw.Draw(image)

    def _finish(self, image, invert):
        if INVERT_COLORS if invert is None else invert:
            return ImageChops.invert(image)

        return image

    def _draw_character(self, image, draw, stats, sys_error, alerts, is_blinking, now):
        character_image, mood = self.character.get_current_image(
            stats, sys_error, alerts, is_blinking, now
        )

        if character_image:
            paste_x = self.width - character_image.width
            image.paste(character_image, (paste_x, 16))
            return

        draw.rectangle(CHARACTER_BOX, outline=0)
        cx = (CHARACTER_BOX[0] + CHARACTER_BOX[2]) // 2
        draw.text((cx, 52), "IMG MISSING", font=theme.mono_sm, fill=0, anchor="mm")
        draw.text((cx, 68), mood.upper(), font=theme.mono_sm, fill=0, anchor="mm")

    def render_frame(
        self, data, active_alerts, is_blinking=False, now=None, invert=None
    ):
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

    def render_offline_frame(self, now, invert=None):
        image, draw = self._new_frame()

        self._draw_character(image, draw, {}, "OFFLINE", [], False, now)
        self.main_screen.draw_offline(draw, now)

        return self._finish(image, invert)
