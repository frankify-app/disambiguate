import re

from typer.testing import CliRunner

from disambiguate.cli import app

runner = CliRunner()

# Rich/Typer embeds ANSI escapes that vary by terminal;
# strip them for stable assertions.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    return _ANSI_RE.sub("", text)


def test_help() -> None:
    """The help message includes the CLI name."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage: " in _plain(result.stdout)
