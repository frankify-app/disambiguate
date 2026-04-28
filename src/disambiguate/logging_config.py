"""
Stdlib logging configuration.

Logging is for diagnostics — "loaded N terms", "walking from root X",
"skipping non-md link". The tool's primary output (rendered markdown, lint
findings) goes to stdout via `print`, not through the logger.

Configured exactly once from `cli.main`, based on the `-v` / `--verbose`
flag count. Anything below WARNING is silenced by default to keep stdout
pipelines uncluttered.
"""

from __future__ import annotations

import logging

DEFAULT_LEVEL = logging.WARNING
INFO_LEVEL = logging.INFO
DEBUG_LEVEL = logging.DEBUG

_VERBOSE_FORMAT = "%(levelname)s %(name)s: %(message)s"
_QUIET_FORMAT = "%(levelname)s: %(message)s"


def configure_logging(verbosity: int) -> int:
    """
    Configure root logging.

    verbosity: 0 = WARNING, 1 = INFO, 2+ = DEBUG. Negative values clamp to 0.

    Returns
    -------
    The effective root logger level after configuration.

    The format depends on level: at WARNING and above the logger name is
    omitted (most messages at that level are user-facing warnings); at INFO
    and below the logger name is included to make tracing easier.

    """
    if verbosity <= 0:
        level = DEFAULT_LEVEL
        fmt = _QUIET_FORMAT
    elif verbosity == 1:
        level = INFO_LEVEL
        fmt = _VERBOSE_FORMAT
    else:
        level = DEBUG_LEVEL
        fmt = _VERBOSE_FORMAT

    logging.basicConfig(level=level, format=fmt, force=True)
    return logging.getLogger().getEffectiveLevel()
