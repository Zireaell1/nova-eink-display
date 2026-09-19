import contextlib
import json
import logging
import os
import tempfile
from typing import Any

logger = logging.getLogger(__name__)

FILENAME = "wear.json"


def state_path(state_directory: str) -> str | None:
    if not state_directory:
        return None

    return os.path.join(state_directory.split(":")[0], FILENAME)


class WearState:
    def __init__(self, path: str | None) -> None:
        self.path = path
        self.writable = path is not None

    def load(self) -> dict[str, Any]:
        if self.path is None:
            logger.info("Wear state is not persisted (STATE_DIRECTORY is unset)")
            return {}

        try:
            with open(self.path, encoding="utf-8") as handle:
                data = json.load(handle)
        except FileNotFoundError:
            logger.info("No wear state at %s yet; counting from zero", self.path)
            return {}
        except OSError, ValueError:
            logger.exception("Unusable wear state at %s; counting from zero", self.path)
            return {}

        if not isinstance(data, dict):
            logger.warning("Wear state at %s is not an object; ignoring", self.path)
            return {}

        logger.info("Restored wear state from %s", self.path)
        return data

    def save(self, payload: dict[str, Any]) -> None:
        if self.path is None or not self.writable:
            return

        directory = os.path.dirname(self.path)
        temporary = None

        try:
            descriptor, temporary = tempfile.mkstemp(
                dir=directory, prefix=".wear-", suffix=".tmp"
            )

            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
                handle.flush()
                os.fsync(handle.fileno())

            os.replace(temporary, self.path)
        except OSError:
            logger.exception("Could not persist wear state to %s", self.path)
            self.writable = False

            if temporary is not None:
                with contextlib.suppress(OSError):
                    os.unlink(temporary)
