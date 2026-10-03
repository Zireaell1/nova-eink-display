import logging
import os

from PIL import Image

from nova_eink_display.config import IMAGES_DIR

logger = logging.getLogger(__name__)

DEFAULT_POSE = "happy"

FRAME_SUFFIX = {"blink": "eyes-closed"}


class PoseImages:
    """Loads character frames. A missing pose falls back to the default pose;
    a missing frame falls back to its own pose's base, never to another pose."""

    def __init__(self, images_dir: str = IMAGES_DIR) -> None:
        self.images_dir = images_dir
        self._cache: dict[str, Image.Image | None] = {}

    def _load(self, name: str) -> Image.Image | None:
        if name in self._cache:
            return self._cache[name]

        path = os.path.join(self.images_dir, f"character-{name}.png")
        image = None
        if os.path.exists(path):
            try:
                with Image.open(path) as raw:
                    image = raw.convert("1", dither=Image.Dither.NONE)
            except (OSError, ValueError) as error:
                logger.warning("Could not load image at %s. %s", path, error)

        self._cache[name] = image
        return image

    def base(self, pose: str) -> Image.Image | None:
        return self._load(pose) or self._load(DEFAULT_POSE)

    def frame(self, pose: str, frame: str = "base") -> Image.Image | None:
        suffix = FRAME_SUFFIX.get(frame)
        if suffix:
            variant = self._load(f"{pose}-{suffix}")
            if variant:
                return variant

        return self.base(pose)
