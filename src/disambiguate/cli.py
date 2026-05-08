import logging

import typer
from colorama import Fore, Style
from pydantic_settings import BaseSettings, SettingsConfigDict

from . import __author__, __email__, __version__
from .Calculator import Calculator

logger = logging.getLogger(__name__)


class AppConfig(BaseSettings):
    """Configuration settings for the application."""

    log_level: int | str

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.secret"),
        env_file_encoding="utf-8",
    )


app = typer.Typer(
    epilog=__doc__,
    help=f"{__package__} version {__version__} by {__author__} <{__email__}>",
    name="memoria",
)


VERBOSITY_LEVELS = {0: logging.ERROR, 1: logging.WARNING, 2: logging.INFO}


def setup_logging(
    log_level: int | str | None = None, verbosity: int | None = None
) -> int:
    """
    Configure logging based on provided log level or verbosity.

    log_level: Specific log level (int or str).
    verbosity: Verbosity level to determine log level.

    Returns
    -------
        int: Effective log level.

    """
    level: int | str
    if verbosity is not None:
        level = VERBOSITY_LEVELS.get(verbosity, logging.DEBUG)
    elif log_level is not None:
        level = log_level.upper() if isinstance(log_level, str) else log_level
    else:
        level = logging.WARNING

    format_str = (
        f"{Style.BRIGHT}{Fore.CYAN}%(asctime)s{Style.RESET_ALL}"
        f" {Style.BRIGHT}{Fore.MAGENTA}%(levelname)s{Style.RESET_ALL}"
        f" %(message)s"
    )
    logging.basicConfig(level=level, force=True, format=format_str)

    return logging.getLogger().getEffectiveLevel()


MAIN_ARG_LOG_LEVEL_OPTION = typer.Option(
    None,
    "--log-level",
    help="Set the specific log level (e.g., 10 or DEBUG, 20 or INFO, etc.).",
    envvar="LOG_LEVEL",
)
MAIN_ARG_VERBOSITY_OPTION = typer.Option(
    0,
    "--verbosity",
    "-v",
    count=True,
    help="Increase verbosity if no log-level is defined.",
)


@app.callback()
def main(
    ctx: typer.Context,
    log_level: str | None = MAIN_ARG_LOG_LEVEL_OPTION,
    verbosity: int | None = MAIN_ARG_VERBOSITY_OPTION,
) -> None:
    """
    Main entry point for the CLI, handling global options.

    ctx: Typer context object.
    log_level: Specific log level to set.
    verbosity: Verbosity level for logging.
    """
    ctx.obj = AppConfig(log_level=setup_logging(log_level, verbosity))


ARG_ADD_A: int = typer.Argument(..., help="The first number.")
ARG_ADD_B: int = typer.Argument(..., help="The second number.")


@app.command("add")
def add(
    ctx: typer.Context,
    a: int = ARG_ADD_A,
    b: int = ARG_ADD_B,
) -> None:
    """
    Add command for the calculator.

    a: The first number.
    b: The second number.
    """
    config = ctx.obj
    logger.info("Starting app with log_level=%s", config.log_level)

    calculator = Calculator(a, b)
    result = calculator.add()
    print(f"The result is: {result}")


if __name__ == "__main__":
    app()
