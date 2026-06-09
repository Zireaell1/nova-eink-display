from PIL import Image, ImageDraw
from src.dashboard.screens import MainScreen, AlertScreen

class UIRenderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.main_screen = MainScreen(width, height)
        self.alert_screen = AlertScreen(width, height)

    def render_frame(self, data, active_alerts):
        image = Image.new('1', (self.width, self.height), 255)
        draw = ImageDraw.Draw(image)

        if active_alerts:
            self.alert_screen.draw(image, draw, active_alerts)
        else:
            self.main_screen.draw(image, draw, data)
            
        return image
