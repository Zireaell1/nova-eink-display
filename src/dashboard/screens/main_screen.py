import os
import logging

from datetime import datetime
from PIL import Image
from .base_screen import BaseScreen, theme
from src.dashboard.config import IMAGES_DIR

class MainScreen(BaseScreen):
    def __init__(self, width, height):
        super().__init__(width, height)

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

    def _get_character_image(self, reaction_state):
        if reaction_state in self.image_cache:
            return self.image_cache[reaction_state]

        specific_path = os.path.join(IMAGES_DIR, f"character-{reaction_state}.png")
        default_path = os.path.join(IMAGES_DIR, self.default_char)

        path_to_load = None

        if os.path.exists(specific_path):
            path_to_load = specific_path
        elif os.path.exists(default_path):
            path_to_load = default_path

        if path_to_load:
            try:
                with Image.open(path_to_load) as temp_img:
                    img = temp_img.convert('1', dither=Image.Dither.NONE)
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

    def draw_status_blocks(self, draw, x, y, services):
        box_size = 12
        spacing = 4
        current_x = x

        for label, is_healthy in services.items():
            if is_healthy:
                draw.rectangle((current_x, y, current_x + box_size, y + box_size), outline=0, fill=255)
                draw.text((current_x + 3, y + 0), label, font=theme.mono_sm, fill=0)
            else:
                draw.rectangle((current_x, y, current_x + box_size, y + box_size), outline=0, fill=0)
                draw.text((current_x + 3, y + 0), label, font=theme.mono_sm, fill=255)
            
            current_x += box_size + spacing

    def draw_alert_panel(self, draw_buffer, alerts):
        draw_buffer.rectangle((4, 24, 122, 36), fill=0)
        draw_buffer.text((63, 30), "SYS FAULT", font=theme.mono, fill=255, anchor="mm")

        y_offset = 44
        max_displayable = 3

        for i, alert in enumerate(alerts):
            if i >= max_displayable:
                remaining = len(alerts) - max_displayable
                draw_buffer.text((4, y_offset), f"+ {remaining} MORE...", font=theme.mono, fill=0)
                break
            
            draw_buffer.text((4, y_offset), f"> {alert[:18]}", font=theme.mono, fill=0)
            y_offset += 16

    def draw(self, base_image, draw_buffer, data, active_alerts=None, is_blinking=False):
        if active_alerts is None:
            active_alerts = []

        stats = data.get('stats', {})
        sys_error = data.get('error')

        current_mood = self._determine_reaction(stats, sys_error, active_alerts)

        if is_blinking and current_mood == "happy":
            current_mood = "happy-eyes-closed"

        char_image = self._get_character_image(current_mood)

        # Background Art
        if char_image:
            paste_x = self.width - char_image.width 
            base_image.paste(char_image, (paste_x, 16))
        else:
            draw_buffer.rectangle((136, 16, 295, 112), outline=0)
            draw_buffer.text((160, 60), "IMG MISSING", font=theme.mono_sm, fill=0)

        # Header
        self.draw_header(draw_buffer)

        # Footer
        ups_val = stats.get('ups_charge', 0)
        uptime_seconds = stats.get('uptime', 0)
        formatted_uptime = self.format_uptime(uptime_seconds)
        self.draw_footer(draw_buffer, ups_val, formatted_uptime)

        if sys_error:
            draw_buffer.text((10, 30), f"SYS_ERR: {sys_error}", font=theme.mono, fill=0)
            return

        if active_alerts:
            self.draw_alert_panel(draw_buffer, active_alerts)
        else:
            COL_START = 4

            # CPU Stats
            cpu_val = stats.get('cpu', 0)
            cpu_text = f"CPU > {int(cpu_val):02d}%"
            draw_buffer.text((COL_START, 26), cpu_text, font=theme.mono, fill=0)
            draw_buffer.text((COL_START + 1, 26), cpu_text, font=theme.mono, fill=0)
            self.draw_block_bar(draw_buffer, COL_START, 38, cpu_val, width=118)

            # RAM Stats
            mem_val = stats.get('mem', 0)
            mem_text = f"MEM > {int(mem_val):02d}%"
            draw_buffer.text((COL_START, 58), mem_text, font=theme.mono, fill=0)
            draw_buffer.text((COL_START + 1, 58), mem_text, font=theme.mono, fill=0)
            self.draw_block_bar(draw_buffer, COL_START, 70, mem_val, width=118)

            # Service Grid (TODO: test)
            service_health = {
                'P': stats.get('podman_up', 1) == 1,
                'F': stats.get('frigate_up', 1) == 1,
                'N': stats.get('node_up', 1) == 1
            }
            
            self.draw_status_blocks(draw_buffer, COL_START, 90, service_health)
