from PIL import Image, ImageChops, ImageDraw

from nova_eink_display.character import Character
from nova_eink_display.config import INVERT_COLORS
from nova_eink_display.screens.base_screen import theme
from nova_eink_display.screens.main_screen import MainScreen


class UIRenderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.main_screen = MainScreen(width, height)
        self.character = Character()

    def render_frame(
        self, data, active_alerts, is_blinking=False, now=None, invert=None
    ):
        image = Image.new("1", (self.width, self.height), 255)
        draw = ImageDraw.Draw(image)

        stats = data.get("stats", {})
        sys_error = data.get("error")

        character_image, mood = self.character.get_current_image(
            stats, sys_error, active_alerts, is_blinking, now
        )

        if character_image:
            paste_x = self.width - character_image.width
            image.paste(character_image, (paste_x, 16))
        else:
            box = (136, 16, 295, 112)
            draw.rectangle(box, outline=0)
            cx = (box[0] + box[2]) // 2
            draw.text((cx, 52), "IMG MISSING", font=theme.mono_sm, fill=0, anchor="mm")
            draw.text((cx, 68), mood.upper(), font=theme.mono_sm, fill=0, anchor="mm")

        self.main_screen.draw(draw, data, active_alerts, now=now)

        if INVERT_COLORS if invert is None else invert:
            image = ImageChops.invert(image)

        return image
