import logging
import os
import sys


class SafeRequestFormatter(logging.Formatter):
    """Formatter that won't crash if extra fields are missing."""

    def format(self, record: logging.LogRecord) -> str:
        # Default fields for non-request log records (or anything missing extras)
        for k, v in {
            "method": "-",
            "path": "-",
            "status_code": "-",
            "duration_ms": "-",
            "user_id": "-",
        }.items():
            if not hasattr(record, k):
                setattr(record, k, v)
        return super().format(record)


def configure_logging() -> None:
    """Configure ONLY our request logger so we don't break third-party logs."""
    level_name = os.getenv("LOG_LEVEL", "INFO").upper().strip()
    level = getattr(logging, level_name, logging.INFO)

    logger = logging.getLogger("mindgarden.request")
    logger.setLevel(level)
    logger.propagate = False  # critical: don't send to root handlers

    # Avoid adding duplicate handlers on reload
    if any(getattr(h, "_mindgarden_handler", False) for h in logger.handlers):
        return

    handler = logging.StreamHandler(sys.stdout)
    handler._mindgarden_handler = True  # marker to avoid duplicates
    handler.setLevel(level)

    handler.setFormatter(
        SafeRequestFormatter(
            "%(asctime)s %(levelname)s %(name)s "
            "method=%(method)s path=%(path)s status=%(status_code)s "
            "duration_ms=%(duration_ms)s user_id=%(user_id)s"
        )
    )

    logger.addHandler(handler)
