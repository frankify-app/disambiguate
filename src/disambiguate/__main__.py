"""Make the CLI runnable via `python -m disambiguate`."""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit("\nERROR: Interrupted by user")
