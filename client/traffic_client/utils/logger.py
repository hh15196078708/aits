"""
logger.py - Global Logging Configuration
(To be developed)
"""

import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logger(
    name: str = "traffic_client",
    log_dir: str = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """Configure and return the global logger with rotating file handler."""
    if log_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(base_dir, "log")

    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "client_run.log")

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        # Rotating file handler: 5MB per file, keep 5 backups
        fh = RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        fh.setLevel(level)

        ch = logging.StreamHandler()
        ch.setLevel(level)

        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger
