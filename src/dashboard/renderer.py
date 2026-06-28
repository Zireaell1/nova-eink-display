from PIL import Image, ImageDraw
from src.dashboard.screens import MainScreen
from src.dashboard.screens.base_screen import theme
from src.dashboard.character import Character

class UIRenderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.main_screen = MainScreen(width, height)
        self.character = Character()

    def render_frame(self, data, active_alerts, is_blinking=False):
        image = Image.new('1', (self.width, self.height), 255)
        draw = ImageDraw.Draw(image)

        stats = data.get('stats', {})
        sys_error = data.get('error')

        character_image = self.character.get_current_image(stats, sys_error, active_alerts, is_blinking)

        if character_image:
            paste_x = self.width - character_image.width
            image.paste(character_image, (paste_x, 16))
        else:
            draw.rectangle((136, 16, 295, 112), outline=0)
            draw.text((160, 60), "IMG MISSING", font=theme.mono_sm, fill=0)

        self.main_screen.draw(draw, data, active_alerts)

        return image
