import subprocess
import sys


def test_can_run_as_python_module() -> None:
    """Run the CLI as a Python module."""
    # sys.executable and module args are fixed, trusted values.
    result = subprocess.run(
        [sys.executable, "-m", "disambiguate", "--help"],
        check=True,
        capture_output=True,
    )
    assert result.returncode == 0
    assert b"disambiguate [OPTIONS]" in result.stdout
