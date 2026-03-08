import sys
import time

from vpn_tools.ui.display_manager import DisplayManager


def test_non_interactive_run_command_executes_process():
    dm = DisplayManager(interactive=False)
    stdout, stderr, returncode, timed_out, elapsed = dm.run_command_with_spinner(
        [sys.executable, "-c", "print('ok')"],
        "run",
        timeout=5,
    )

    assert returncode == 0
    assert timed_out is False
    assert "ok" in stdout
    assert stderr == ""
    assert elapsed >= 0


def test_non_interactive_spinner_executes_action():
    dm = DisplayManager(interactive=False)

    def action(_stop_event):
        time.sleep(0.05)
        return 42

    value, timed_out, elapsed = dm.spinner("spin", action, timeout=1)
    assert value == 42
    assert timed_out is False
    assert elapsed >= 0
