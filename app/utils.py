# utils.py

import logging
import tomllib

from pathlib import Path
 
logger = logging.getLogger(__name__)

def get_pyproject_data() -> dict:
    """
    Load and return the pyproject.toml data as a dict (Python 3.11+ with tomllib).
    Adjust if you need a different path or Python version.
    """
    # This assumes pyproject.toml is at the parent level of fastapi-backend-mongo/
    pyproject_file = Path(__file__).parent / "pyproject.toml"
    with pyproject_file.open("rb") as f:
        pyproject_data = tomllib.load(f)

    return pyproject_data