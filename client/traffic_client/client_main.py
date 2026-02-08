"""
client_main.py - Main entry point
Initializes all modules and starts the main loop.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.service_manager import ServiceManager
from utils.logger import setup_logger
from config.settings import Settings


def main():
    """Main entry point for the traffic client."""
    settings = Settings()
    logger = setup_logger()
    logger.info("Traffic client starting...")

    service_manager = ServiceManager(settings)
    service_manager.run()


if __name__ == "__main__":
    main()
