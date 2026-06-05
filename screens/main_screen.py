from .base_screen import BaseScreen, theme
from config import QUERIES, HISTORY_LENGTH

class MainScreen(BaseScreen):
    def __init__(self, width, height):
        super().__init__(width, height)
        self.history = {k: [] for k in QUERIES.keys()}

    def update_history(self, stats):
        for k in self.history.keys():
            val = stats.get(k, 0)
            self.history[k].append(val)
            if len(self.history[k]) > HISTORY_LENGTH:
                self.history[k].pop(0)

    def draw_block_bar(self, draw, x, y, value, max_val=100, blocks=20):
        ratio = max(0.0, min(1.0, value / max_val))
        filled_blocks = int(ratio * blocks)
        bar_str = "[" + ("■" * filled_blocks) + ("-" * (blocks - filled_blocks)) + "]"
        draw.text((x, y), bar_str, font=theme.mono, fill=0)

    def draw_sparkline(self, draw, x, y, w, h, data_key, max_val=100):
        points = self.history.get(data_key, [])
        if len(points) < 2: 
            return

        step = w / (len(points) - 1)
        coords = []
        
        for i, val in enumerate(points):
            py = y + h - (min(val, max_val) / max_val * h)
            coords.append((x + i * step, py))
        
        draw.line(coords, fill=0, width=2)
        draw.rectangle((x-1, y-1, x+w+1, y+h+1), outline=0)

    def draw(self, base_image, draw_buffer, data):
        # 1. Header
        self.draw_terminal_header(draw_buffer)
        
        # 2. Handle API Errors overlay
        if data.get('error'):
            draw_buffer.text((10, 30), f"SYS_ERR: {data['error']}", font=theme.mono, fill=0)
            return

        stats = data.get('stats', {})
        y_offset = 25
        
        # 3. CPU Bar
        cpu_val = stats.get('cpu', 0)
        draw_buffer.text((4, y_offset), f"CPU {int(cpu_val):02d}%", font=theme.mono, fill=0)
        self.draw_block_bar(draw_buffer, 75, y_offset, cpu_val, blocks=22)
        
        # 4. RAM Bar
        y_offset += 16
        mem_val = stats.get('mem', 0)
        draw_buffer.text((4, y_offset), f"MEM {int(mem_val):02d}%", font=theme.mono, fill=0)
        self.draw_block_bar(draw_buffer, 75, y_offset, mem_val, blocks=22)

        # 5. History Sparklines
        y_offset += 24
        draw_buffer.text((4, y_offset), "CPU_HIST", font=theme.mono_sm, fill=0)
        self.draw_sparkline(draw_buffer, 4, y_offset + 12, 135, 15, 'cpu')

        draw_buffer.text((150, y_offset), "MEM_HIST", font=theme.mono_sm, fill=0)
        self.draw_sparkline(draw_buffer, 150, y_offset + 12, 135, 15, 'mem')

        # 6. Status Footer
        y_offset += 38
        draw_buffer.line((0, y_offset, self.width, y_offset), fill=0, width=1) 
        y_offset += 4
        
        ups_val = stats.get('ups_charge', 0)
        ups_status = "OK " if ups_val > 90 else "WARN"
        draw_buffer.text((4, y_offset), f"UPS_PWR : [{ups_status}] {int(ups_val):03d}%", font=theme.mono, fill=0)
