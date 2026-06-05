from PIL import Image
from .base_screen import BaseScreen, theme

class MainScreen(BaseScreen):
    def __init__(self, width, height):
        super().__init__(width, height)
        
        self.char_image = None
        image_path = "assets/icons/character_sleepy.png"
        
        try:
            self.char_image = Image.open(image_path).convert('1', dither=Image.Dither.NONE)
        except Exception as e:
            print(f"Warning: Could not load character image at {image_path}. {e}")

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
        # Background Art
        if self.char_image:
            base_image.paste(self.char_image, (136, 16))
        else:
            draw_buffer.rectangle((136, 16, 295, 112), outline=0)
            draw_buffer.text((160, 60), "IMG MISSING", font=theme.mono_sm, fill=0)

        # Header
        self.draw_header(draw_buffer)
        
        if data.get('error'):
            draw_buffer.text((10, 30), f"SYS_ERR: {data['error']}", font=theme.mono, fill=0)
            return

        stats = data.get('stats', {})
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
