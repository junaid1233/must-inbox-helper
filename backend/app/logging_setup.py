"""Application logging.

Policy: log ids, counts and error types only. Never log message text, candidate
names, context or drafts, since they may contain personal data. Tests in
tests/test_logging.py and tests/test_stress.py (S16) check this.
"""

import logging
import os

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging() -> None:
    logger = logging.getLogger("app")
    if any(getattr(h, "_inbox_helper", False) for h in logger.handlers):
        return  # already configured (e.g. module reloaded)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_FORMAT))
    handler._inbox_helper = True  # type: ignore[attr-defined]
    logger.addHandler(handler)
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
