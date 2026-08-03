"""Central logging configuration for Patty application services."""

import logging


LOGGER_NAME = "patty_bot"


def configure_application_logging() -> None:
    """Configure one local handler without replacing a host application's logging policy."""

    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
