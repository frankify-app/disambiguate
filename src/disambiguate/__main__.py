"""Make the CLI runnable using python -m disambiguate."""

import sys

from .cli import app

if "__main__" == __name__:
    try:
        exit(app(prog_name="disambiguate"))
    except KeyboardInterrupt:  # Avoid traceback on Ctrl+C
        sys.exit("\nERROR: Interrupted by user")
