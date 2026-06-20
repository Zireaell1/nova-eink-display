import os
import logging
from datetime import datetime
from PIL import Image
from src.dashboard.config import IMAGES_DIR

logger = logging.getLogger(__name__)

class Character:
    def __init__(self):
        self.default_char = "character_happy.png"
        self.image_cache = {}

    def _determine_reaction(self, stats, sys_error, active_alerts):
        if sys_error:
            return "disconnected"
        
        if active_alerts:
            return "concerned" # TODO: panicked

        if stats.get('cpu', 0) > 75 or stats.get('mem', 0) > 80:
            return "concerned"

        hour = datetime.now().hour
        if hour >= 22 or hour <= 6:
            return "sleep"

        return "happy"

    def _get_image(self, reaction_state):
        if reaction_state in self.image_cache:
            return self.image_cache[reaction_state]

        specific_path = os.path.join(IMAGES_DIR, f"character-{reaction_state}.png")
        default_path = os.path.join(IMAGES_DIR, self.default_char)

        path_to_load = specific_path if os.path.exists(specific_path) else default_path

        if path_to_load and os.path.exists(path_to_load):
            try:
                with Image.open(path_to_load) as temp_img:
                    img = temp_img.convert('1', dither=Image.Dither.NONE)
                    self.image_cache[reaction_state] = img
                    return img
            except Exception as e:
                logger.warning(f"Could not load image at {path_to_load}. {e}")

        self.image_cache[reaction_state] = None
        return None

    def get_current_image(self, stats, sys_error, active_alerts, is_blinking=False):
        mood = self._determine_reaction(stats, sys_error, active_alerts)

        if is_blinking and mood == "happy":
            blink_mood = "happy-eyes-closed"

            blink_img = self._get_image(blink_mood)
            if blink_img:
                return blink_img

        return self._get_image(mood)
