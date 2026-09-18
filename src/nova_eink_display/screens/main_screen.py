import logging
import textwrap

from .base_screen import BaseScreen, theme

logger = logging.getLogger(__name__)


class MainScreen(BaseScreen):
    def __init__(self, width, height):
        super().__init__(width, height)

    @staticmethod
    def format_uptime(seconds):
        if seconds is None:
            return "--"

        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)

        if days > 0:
            return f"{days}d {hours}h"
        else:
            return f"{hours}h"

    @staticmethod
    def _dotted_rectangle(draw, box, step=2):
        x0, y0, x1, y1 = box

        for px in range(x0, x1 + 1, step):
            draw.point((px, y0), fill=0)
            draw.point((px, y1), fill=0)

        for py in range(y0, y1 + 1, step):
            draw.point((x0, py), fill=0)
            draw.point((x1, py), fill=0)

    def draw_block_bar(self, draw, x, y, value, max_val=100, width=112):
        draw.rectangle((x, y, x + width, y + 6), outline=0)

        if value is None:
            for px in range(x + 3, x + width, 4):
                draw.point((px, y + 3), fill=0)
            return

        ratio = max(0.0, min(1.0, value / max_val))
        filled_width = int(ratio * width)

        if filled_width > 0:
            draw.rectangle((x + 1, y + 1, x + filled_width, y + 5), fill=0)

    def draw_status_blocks(self, draw, x, y, services):
        box_size = 12
        spacing = 4
        current_x = x

        for label, state in services.items():
            box = (current_x, y, current_x + box_size, y + box_size)

            if state is None:
                self._dotted_rectangle(draw, box)
                draw.text((current_x + 3, y), label, font=theme.mono_sm, fill=0)
            elif state:
                draw.rectangle(box, outline=0, fill=255)
                draw.text((current_x + 3, y), label, font=theme.mono_sm, fill=0)
            else:
                draw.rectangle(box, outline=0, fill=0)
                draw.text((current_x + 3, y), label, font=theme.mono_sm, fill=255)

            current_x += box_size + spacing

    def draw_alert_panel(self, draw_buffer, alerts):
        draw_buffer.rectangle((4, 24, 122, 36), fill=0)
        draw_buffer.text((63, 30), "SYS FAULT", font=theme.mono, fill=255, anchor="mm")

        y_offset = 44
        max_lines = 4

        display_lines = []
        for alert in alerts:
            wrapped_text = textwrap.wrap(alert, width=14)
            for i, line in enumerate(wrapped_text):
                if i == 0:
                    display_lines.append(f"> {line}")
                else:
                    display_lines.append(f"  {line}")

        for i, line in enumerate(display_lines):
            if i == max_lines - 1 and len(display_lines) > max_lines:
                draw_buffer.text((4, y_offset), "+ MORE...", font=theme.mono, fill=0)
                break

            draw_buffer.text((4, y_offset), line, font=theme.mono, fill=0)
            y_offset += 16

    def draw(self, draw_buffer, data, active_alerts=None):
        if active_alerts is None:
            active_alerts = []

        stats = data.get("stats", {})
        sys_error = data.get("error")

        # Header
        self.draw_header(draw_buffer)

        # Footer
        ups_val = stats.get("ups_charge")
        formatted_uptime = self.format_uptime(stats.get("uptime"))
        self.draw_footer(draw_buffer, ups_val, formatted_uptime)

        if sys_error:
            draw_buffer.text((10, 30), f"SYS_ERR: {sys_error}", font=theme.mono, fill=0)
            return

        if active_alerts:
            self.draw_alert_panel(draw_buffer, active_alerts)
        else:
            COL_START = 4

            # CPU Stats
            cpu_val = stats.get("cpu")
            cpu_text = f"CPU > {cpu_val:2.0f}%" if cpu_val is not None else "CPU >  --"
            draw_buffer.text((COL_START, 26), cpu_text, font=theme.mono, fill=0)
            draw_buffer.text((COL_START + 1, 26), cpu_text, font=theme.mono, fill=0)
            self.draw_block_bar(draw_buffer, COL_START, 38, cpu_val, width=118)

            # RAM Stats
            mem_val = stats.get("mem")
            mem_text = f"MEM > {mem_val:2.0f}%" if mem_val is not None else "MEM >  --"
            draw_buffer.text((COL_START, 58), mem_text, font=theme.mono, fill=0)
            draw_buffer.text((COL_START + 1, 58), mem_text, font=theme.mono, fill=0)
            self.draw_block_bar(draw_buffer, COL_START, 70, mem_val, width=118)

            # Service Grid
            service_health = {"B": stats.get("backup_status")}

            self.draw_status_blocks(draw_buffer, COL_START, 90, service_health)
