from dataclasses import dataclass


@dataclass(frozen=True)
class Layout:
    width: int
    height: int

    margin: int = 4
    header_height: int = 16
    footer_height: int = 16
    line_height: int = 16

    character_width: int = 160

    column_width: int = 118

    bar_height: int = 6
    status_box: int = 12

    wrap_columns: int = 14

    stat_row_offset: int = 10
    stat_row_stride: int = 32
    stat_bar_offset: int = 12

    @property
    def header_bottom(self) -> int:
        return self.header_height

    @property
    def footer_top(self) -> int:
        return self.height - self.footer_height

    @property
    def header_middle(self) -> int:
        return self.header_height // 2

    @property
    def footer_middle(self) -> int:
        return self.footer_top + self.footer_height // 2

    @property
    def column_start(self) -> int:
        return self.margin

    @property
    def column_end(self) -> int:
        return self.margin + self.column_width

    @property
    def character_x(self) -> int:
        return self.width - self.character_width

    @property
    def character_box(self) -> tuple[int, int, int, int]:
        return (self.character_x, self.header_bottom, self.width - 1, self.footer_top)

    @property
    def character_size(self) -> tuple[int, int]:
        left, top, right, bottom = self.character_box
        return (right - left + 1, bottom - top)

    @property
    def panel_top(self) -> int:
        return self.header_bottom + 28

    def stat_row_y(self, index: int) -> int:
        return self.header_bottom + self.stat_row_offset + index * self.stat_row_stride

    def stat_bar_y(self, index: int) -> int:
        return self.stat_row_y(index) + self.stat_bar_offset
