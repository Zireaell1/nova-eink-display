import datetime
import textwrap

from PIL import ImageDraw

from .base_screen import BaseScreen, theme


class MainScreen(BaseScreen):
    @staticmethod
    def format_uptime(seconds: float | None) -> str:
        if seconds is None or seconds < 0:
            return "--"

        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)

        if days > 0:
            return f"{days}d {hours}h"

        return f"{hours}h"

    @staticmethod
    def _dotted_rectangle(
        draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], step: int = 2
    ) -> None:
        x0, y0, x1, y1 = box

        for px in range(x0, x1 + 1, step):
            draw.point((px, y0), fill=0)
            draw.point((px, y1), fill=0)

        for py in range(y0, y1 + 1, step):
            draw.point((x0, py), fill=0)
            draw.point((x1, py), fill=0)

    def draw_block_bar(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        value: float | None,
        max_val: float = 100,
        width: int | None = None,
    ) -> None:
        height = self.layout.bar_height
        width = self.layout.column_width if width is None else width

        draw.rectangle((x, y, x + width, y + height), outline=0)

        if value is None:
            for px in range(x + 3, x + width, 4):
                draw.point((px, y + height // 2), fill=0)
            return

        ratio = max(0.0, min(1.0, value / max_val))
        filled_width = int(ratio * width)

        if filled_width > 0:
            draw.rectangle((x + 1, y + 1, x + filled_width, y + height - 1), fill=0)

    def draw_status_blocks(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        services: dict[str, float | None],
    ) -> None:
        box_size = self.layout.status_box
        current_x = x

        for label, state in services.items():
            box = (current_x, y, current_x + box_size, y + box_size)

            if state is None:
                self._dotted_rectangle(draw, box)
                draw.text((current_x + 3, y), label, font=theme.mono, fill=0)
            elif state:
                draw.rectangle(box, outline=0, fill=255)
                draw.text((current_x + 3, y), label, font=theme.mono, fill=0)
            else:
                draw.rectangle(box, outline=0, fill=0)
                draw.text((current_x + 3, y), label, font=theme.mono, fill=255)

            current_x += box_size + self.layout.margin

    def _draw_wrapped(
        self, draw: ImageDraw.ImageDraw, lines: list[str], y: int
    ) -> None:
        for line in lines:
            draw.text((self.layout.margin, y), line, font=theme.mono, fill=0)
            y += self.layout.line_height

    def draw_error_panel(self, draw: ImageDraw.ImageDraw, sys_error: str) -> None:
        lines = textwrap.wrap(f"SYS_ERR: {sys_error}", width=self.layout.wrap_columns)
        self._draw_wrapped(draw, lines, self.layout.header_bottom + 14)

    def draw_alert_panel(self, draw: ImageDraw.ImageDraw, alerts: list[str]) -> None:
        layout = self.layout

        draw.rectangle(
            (
                layout.margin,
                layout.header_bottom + 8,
                layout.column_end,
                layout.header_bottom + 20,
            ),
            fill=0,
        )
        draw.text(
            (layout.margin + layout.column_width // 2, layout.header_bottom + 14),
            "SYS FAULT",
            font=theme.mono,
            fill=255,
            anchor="mm",
        )

        y_offset = layout.panel_top
        max_lines = 4

        display_lines = []
        for alert in alerts:
            wrapped_text = textwrap.wrap(alert, width=layout.wrap_columns)
            for i, line in enumerate(wrapped_text):
                display_lines.append(f"> {line}" if i == 0 else f"  {line}")

        for i, line in enumerate(display_lines):
            if i == max_lines - 1 and len(display_lines) > max_lines:
                draw.text(
                    (layout.margin, y_offset), "+ MORE...", font=theme.mono, fill=0
                )
                break

            draw.text((layout.margin, y_offset), line, font=theme.mono, fill=0)
            y_offset += layout.line_height

    def draw_offline(self, draw: ImageDraw.ImageDraw, now: datetime.datetime) -> None:
        self.draw_header(draw, now=now)
        self.draw_footer(draw, None, "--")

        self._draw_wrapped(
            draw, ["OFFLINE", f"SINCE {now.strftime('%H:%M')}"], self.layout.panel_top
        )

    def draw(
        self,
        draw: ImageDraw.ImageDraw,
        data: dict,
        active_alerts: list[str] | None = None,
        now: datetime.datetime | None = None,
    ) -> None:
        if active_alerts is None:
            active_alerts = []

        layout = self.layout
        stats = data.get("stats", {})
        sys_error = data.get("error")

        self.draw_header(draw, now=now)

        self.draw_footer(
            draw, stats.get("ups_charge"), self.format_uptime(stats.get("uptime"))
        )

        if sys_error:
            self.draw_error_panel(draw, sys_error)
            return

        if active_alerts:
            self.draw_alert_panel(draw, active_alerts)
            return

        for row, (label, key) in enumerate((("CPU", "cpu"), ("MEM", "mem"))):
            value = stats.get(key)
            text = f"{label} > {value:2.0f}%" if value is not None else f"{label} >  --"

            draw.text(
                (layout.column_start, layout.stat_row_y(row)),
                text,
                font=theme.mono,
                fill=0,
            )
            draw.text(
                (layout.column_start + 1, layout.stat_row_y(row)),
                text,
                font=theme.mono,
                fill=0,
            )
            self.draw_block_bar(
                draw, layout.column_start, layout.stat_bar_y(row), value
            )

        self.draw_status_blocks(
            draw,
            layout.column_start,
            layout.stat_row_y(2),
            {"B": stats.get("backup_status")},
        )
