import os
import logging

from datetime import datetime
from PIL import Image
from .base_screen import BaseScreen, theme
from config import IMAGES_DIR

class MainScreen(BaseScreen):
    def __init__(self, width, height):
        super().__init__(width, height)

        self.default_char = "character_default.png"

        self.image_cache = {}

    def _determine_reaction(self, stats, sys_error):
        if sys_error:
            return "panicked"

        if stats.get('ups_charge', 100) < 40 or stats.get('cpu', 0) >= 95:
            return "panicked"

        if stats.get('cpu', 0) > 75 or stats.get('mem', 0) > 80:
            return "concerned"

        hour = datetime.now().hour
        if hour >= 22 or hour <= 6:
            return "sleep"

        return "default"

    def _get_character_image(self, reaction_state):
        if reaction_state in self.image_cache:
            return self.image_cache[reaction_state]

        specific_path = os.path.join(IMAGES_DIR, f"character_{reaction_state}.png")
        default_path = os.path.join(IMAGES_DIR, self.default_char)

        path_to_load = None

        if os.path.exists(specific_path):
            path_to_load = specific_path
        elif os.path.exists(default_path):
            path_to_load = default_path

        if path_to_load:
            try:
                img = Image.open(path_to_load).convert('1', dither=Image.Dither.NONE)
                self.image_cache[reaction_state] = img
                return img
            except Exception as e:
                logging.warning(f"Could not load image at {path_to_load}. {e}")

        self.image_cache[reaction_state] = None
        return None

    def format_uptime(self, seconds):
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)

        if days > 0:
            return f"{days}d {hours}h"
        else:
            return f"{hours}h"


    def draw_block_bar(self, draw, x, y, value, max_val=100, width=112):
        draw.rectangle((x, y, x + width, y + 6), outline=0)

        ratio = max(0.0, min(1.0, value / max_val))
        filled_width = int(ratio * width)

        draw.rectangle((x + 1, y + 1, x + filled_width, y + 5), fill=0)

    def draw(self, base_image, draw_buffer, data):
        stats = data.get('stats', {})
        sys_error = data.get('error')

        current_mood = self._determine_reaction(stats, sys_error)
        char_image = self._get_character_image(current_mood)

        # Background Art
        if char_image:
            base_image.paste(char_image, (130, 16))
        else:
            draw_buffer.rectangle((136, 16, 295, 112), outline=0)
            draw_buffer.text((160, 60), "IMG MISSING", font=theme.mono_sm, fill=0)

        # Header
        self.draw_header(draw_buffer)

        if sys_error:
            draw_buffer.text((10, 30), f"SYS_ERR: {sys_error}", font=theme.mono, fill=0)
            return

        COL_START = 4

        # CPU Stats
        cpu_val = stats.get('cpu', 0)
        cpu_text = f"CPU > {int(cpu_val):02d}%"
        draw_buffer.text((COL_START, 26), cpu_text, font=theme.mono, fill=0)
        draw_buffer.text((COL_START + 1, 26), cpu_text, font=theme.mono, fill=0)
        self.draw_block_bar(draw_buffer, COL_START, 38, cpu_val)

        # RAM Stats
        mem_val = stats.get('mem', 0)
        mem_text = f"MEM > {int(mem_val):02d}%"
        draw_buffer.text((COL_START, 66), mem_text, font=theme.mono, fill=0)
        draw_buffer.text((COL_START + 1, 66), mem_text, font=theme.mono, fill=0)
        self.draw_block_bar(draw_buffer, COL_START, 78, mem_val)

        # Footer
        ups_val = stats.get('ups_charge', 0)
        uptime_seconds = stats.get('uptime', 0)
        formatted_uptime = self.format_uptime(uptime_seconds)
        self.draw_footer(draw_buffer, ups_val, formatted_uptime)
