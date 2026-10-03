import datetime
import textwrap
from collections.abc import Mapping

from PIL import ImageDraw

from nova_eink_display.checks import Check, State, evaluate_checks, summarise
from nova_eink_display.world import Screen

from .base_screen import BaseScreen, theme


class MainScreen(BaseScreen):
    PANEL_LINES = 4

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
    def format_ups(stats: Mapping[str, float]) -> str:
        on_battery = stats.get("ups_on_battery")
        runtime = stats.get("ups_runtime")
        charge = stats.get("ups_charge")

        if on_battery is None and charge is None:
            return "UPS:[ -- ]"

        state = "BATT" if on_battery else " OK "

        if runtime is not None and runtime >= 0:
            return f"UPS:[{state}] {int(runtime // 60)}m"

        if charge is not None:
            return f"UPS:[{state}] {charge:2.0f}%"

        return f"UPS:[{state}]"

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

    @staticmethod
    def status_banner(checks: list[Check]) -> str:
        bad, known = summarise(checks)
        total = len(checks)

        if not known:
            return "NO DATA"
        if bad:
            return f"{bad} OF {total} BAD"
        if known < total:
            return f"{known} OF {total} OK"
        return f"ALL {total} OK"

    def draw_status(self, draw: ImageDraw.ImageDraw, checks: list[Check]) -> None:
        layout = self.layout

        top = layout.status_top
        draw.rectangle((layout.column_start, top, layout.column_end, top + 11), fill=0)
        draw.text(
            (layout.column_start + layout.column_width // 2, top + 5),
            self.status_banner(checks),
            font=theme.mono,
            fill=255,
            anchor="mm",
        )

        y = top + 15
        for check in checks[: layout.status_rows]:
            draw.text(
                (layout.column_start, y),
                f"{'!' if check.state is State.BAD else '>'} {check.label}",
                font=theme.mono,
                fill=0,
            )
            draw.text(
                (layout.column_end, y),
                check.detail,
                font=theme.mono,
                fill=0,
                anchor="ra",
            )
            y += layout.status_stride

    def draw_panel(
        self, draw: ImageDraw.ImageDraw, title: str, lines: list[str]
    ) -> None:
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
            title,
            font=theme.mono,
            fill=255,
            anchor="mm",
        )

        y = layout.panel_top
        for line in lines[: self.PANEL_LINES]:
            draw.text((layout.margin, y), line, font=theme.mono, fill=0)
            y += layout.line_height

    @classmethod
    def error_lines(
        cls, sys_error: str, since: datetime.datetime | None, width: int
    ) -> list[str]:
        room = cls.PANEL_LINES - (1 if since else 0)
        lines = cls.alert_lines([sys_error], width, room)
        if since:
            lines.append(f"SINCE {since.strftime('%H:%M')}")
        return lines

    def draw_error_panel(
        self,
        draw: ImageDraw.ImageDraw,
        sys_error: str,
        since: datetime.datetime | None = None,
    ) -> None:
        lines = self.error_lines(sys_error, since, self.layout.wrap_columns)
        self.draw_panel(draw, "FETCH ERROR", lines)

    def draw_alert_panel(self, draw: ImageDraw.ImageDraw, alerts: list[str]) -> None:
        self.draw_panel(
            draw, "SYS FAULT", self.alert_lines(alerts, self.layout.wrap_columns)
        )

    @staticmethod
    def alert_lines(alerts: list[str], width: int, max_lines: int = 4) -> list[str]:
        blocks = [
            [f"> {line}" if i == 0 else f"  {line}" for i, line in enumerate(wrapped)]
            for wrapped in (textwrap.wrap(alert, width=width) for alert in alerts)
        ]

        if sum(len(block) for block in blocks) <= max_lines:
            return [line for block in blocks for line in block]

        lines: list[str] = []
        shown = 0
        for block in blocks:
            if len(lines) + len(block) > max_lines - 1:
                break
            lines.extend(block)
            shown += 1

        if not shown:
            lines = blocks[0][: max_lines - 1]
            shown = 1

        return [*lines, f"+ {len(blocks) - shown} MORE"]

    def draw_asleep(
        self, draw: ImageDraw.ImageDraw, now: datetime.datetime, wake_hour: int
    ) -> None:
        self.draw_header(draw, clock="--:--")
        self.draw_footer(draw)

        self.draw_panel(
            draw,
            "ASLEEP",
            [f"SINCE {now.strftime('%H:%M')}", f"UNTIL {wake_hour:02d}:00"],
        )

    def draw_offline(self, draw: ImageDraw.ImageDraw, now: datetime.datetime) -> None:
        self.draw_header(draw, now=now)
        self.draw_footer(draw)

        self.draw_panel(draw, "OFFLINE", [f"SINCE {now.strftime('%H:%M')}"])

    def draw(self, draw: ImageDraw.ImageDraw, screen: Screen) -> None:
        layout = self.layout
        stats = screen.stats
        sys_error = screen.error
        active_alerts = list(screen.alerts)

        self.draw_header(draw, now=screen.now)

        self.draw_footer(
            draw, self.format_ups(stats), self.format_uptime(stats.get("uptime"))
        )

        if sys_error:
            self.draw_error_panel(draw, sys_error, screen.error_since)
            return

        if active_alerts:
            self.draw_alert_panel(draw, active_alerts)
            return

        for row, (label, key) in enumerate((("CPU", "cpu"), ("MEM", "mem"))):
            value = stats.get(key)
            if value is None:
                text = f"{label} >  --"
            else:
                text = f"{label} > {max(0.0, min(100.0, value)):2.0f}%"

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

        self.draw_status(draw, evaluate_checks(stats))
