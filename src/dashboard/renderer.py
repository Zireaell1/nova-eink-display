from PIL import Image, ImageDraw
from src.dashboard.screens import MainScreen

class UIRenderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.main_screen = MainScreen(width, height)

    def render_frame(self, data, active_alerts, is_blinking=False):
        image = Image.new('1', (self.width, self.height), 255)
        draw = ImageDraw.Draw(image)

        self.main_screen.draw(image, draw, data, active_alerts, is_blinking)
            
        return image
