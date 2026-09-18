import logging
import os

LOG_FORMAT = "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"


def setup_logging() -> None:
    level = logging.getLevelNamesMapping().get(
        os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO
    )
    logging.basicConfig(level=level, format=LOG_FORMAT)


setup_logging()
