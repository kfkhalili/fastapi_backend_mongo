# logging_config.py

import logging
from app.utils import get_pyproject_data

def setup_logging() -> None:
    """Configure logging for the project"""
    project_name = get_pyproject_data()["project"]["name"]

    # Option 1: Configure the root logger
    logger = logging.getLogger()  # get the root logger
    logger.setLevel(logging.INFO)

    # Optionally clear existing handlers so we don’t keep default ones
    logger.handlers.clear()

    # Create handlers
    file_handler = logging.FileHandler("myapp.log")
    console_handler = logging.StreamHandler()

    file_handler.setLevel(logging.INFO)
    console_handler.setLevel(logging.INFO)

    # Create a formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(filename)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Attach handlers to the root logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Optionally, log that we’ve set things up
    logger.info(f"Logging configured for project: {project_name}")
