import logging

from PIL import Image, ImageChops, ImageDraw

from nova_eink_display.config import INVERT_COLORS
from nova_eink_display.layout import Layout
from nova_eink_display.poses import PoseImages
from nova_eink_display.screens.base_screen import theme
from nova_eink_display.screens.main_screen import MainScreen
from nova_eink_display.world import Mode, Screen, World

logger = logging.getLogger(__name__)


class Composer:
    """compose(world) -> image. Holds only loaded assets; given the same World
    it always returns the same pixels."""

    def __init__(
        self, width: int, height: int, poses: PoseImages | None = None
    ) -> None:
        self.width = width
        self.height = height
        self.layout = Layout(width, height)
        self.main_screen = MainScreen(width, height)
        self.poses = poses or PoseImages()
        self._warned_sizes: set[str] = set()

    def __call__(self, world: World, invert: bool | None = None) -> Image.Image:
        screen = world.screen
        image = Image.new("1", (self.width, self.height), 255)
        draw = ImageDraw.Draw(image)

        self._draw_character(image, draw, screen)

        match screen.mode:
            case Mode.DASHBOARD:
                self.main_screen.draw(draw, screen)
            case Mode.ASLEEP:
                self.main_screen.draw_asleep(draw, screen.now, screen.wake_hour or 0)
            case Mode.OFFLINE:
                self.main_screen.draw_offline(draw, screen.now)

        if INVERT_COLORS if invert is None else invert:
            return ImageChops.invert(image)
        return image

    def _check_size(self, pose: str, image: Image.Image) -> None:
        max_width, max_height = self.layout.character_max_size
        if (
            image.width <= max_width
            and image.height <= max_height
            or pose in self._warned_sizes
        ):
            return

        self._warned_sizes.add(pose)
        logger.warning(
            "character-%s.png is %sx%s; at most %sx%s fits between the stats "
            "column and the footer, so it will be clipped",
            pose,
            image.width,
            image.height,
            max_width,
            max_height,
        )

    def _draw_character(
        self, image: Image.Image, draw: ImageDraw.ImageDraw, screen: Screen
    ) -> None:
        character = self.poses.frame(screen.pose, screen.frame)

        if character:
            self._check_size(screen.pose, character)
            image.paste(
                character, (self.width - character.width, self.layout.header_bottom)
            )
            return

        box = self.layout.character_box
        draw.rectangle(box, outline=0)

        cx = (box[0] + box[2]) // 2
        cy = (box[1] + box[3]) // 2
        draw.text((cx, cy - 12), "IMG MISSING", font=theme.mono, fill=0, anchor="mm")
        draw.text(
            (cx, cy + 4), screen.pose.upper(), font=theme.mono, fill=0, anchor="mm"
        )
