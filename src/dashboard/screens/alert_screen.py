from .base_screen import BaseScreen, theme 

class AlertScreen(BaseScreen):
    def draw(self, base_image, draw_buffer, alerts):
        self.draw_header(draw_buffer, title="[!_SYS_FAULT_!]", invert=True)
        
        draw_buffer.text((4, 25), "CRITICAL ALERTS DETECTED:", font=theme.title, fill=0)
        draw_buffer.line((0, 45, self.width, 45), fill=0, width=2)

        y_offset = 50
        max_displayable = 4

        for i, alert in enumerate(alerts):
            if i >= max_displayable:
                remaining = len(alerts) - max_displayable
                draw_buffer.text(
                    (4, y_offset), 
                    f"... and {remaining} more faults", 
                    font=theme.mono, 
                    fill=0
                )
                break

            draw_buffer.text((4, y_offset), f"> {alert}", font=theme.mono, fill=0)
            y_offset += 16
