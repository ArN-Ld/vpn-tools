import sys
import shutil
import subprocess
import threading
import time
from itertools import cycle
from typing import Optional, Protocol

# Try to import colorama for color support
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    COLOR_SUPPORT = True
except ImportError:  # pragma: no cover - fallback for missing colorama
    class DummyFore:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ''
        LIGHTGREEN_EX = LIGHTYELLOW_EX = LIGHTRED_EX = ''
    class DummyStyle:
        BRIGHT = DIM = NORMAL = RESET_ALL = ''
    class DummyBack:
        RED = GREEN = YELLOW = BLUE = RESET = ''
    Fore, Style, Back = DummyFore(), DummyStyle(), DummyBack()
    COLOR_SUPPORT = False

# UI symbols (Unicode and ASCII)
SYMBOLS = {
    'success': '✓', 'error': '✗', 'warning': '⚠', 'info': 'ℹ',
    'connecting': '→', 'testing': '⋯', 'bullet': '•',
    'right_arrow': '→', 'speedometer': '🔄', 'clock': '⏱', 'globe': '🌐',
    'server': '🖥', 'signal': '📶', 'download': '⬇', 'upload': '⬆',
    'ping': '📡', 'checkmark': '✓', 'cross': '✗',
}
ASCII_SYMBOLS = {k: v for k, v in zip(SYMBOLS.keys(),
                                     ['+', 'x', '!', 'i', '>', '...', '*', '->', 'O', 'T',
                                      'G', 'S', '^', 'D', 'U', 'P', 'V', 'X'])}

# Check if terminal supports Unicode
try:
    "\u2713".encode(sys.stdout.encoding)
    USE_UNICODE = True
except UnicodeEncodeError:
    USE_UNICODE = False


class ServerInfo(Protocol):
    """Minimal server information required for display formatting."""

    hostname: str
    city: str
    country: str
    distance_km: float


def colorize(text: str, color: str = "") -> str:
    """Return text wrapped in ANSI color codes if supported."""
    return f"{color}{text}{Style.RESET_ALL}" if COLOR_SUPPORT and color else text


def get_symbol(name: str) -> str:
    """Return a symbol by name, respecting Unicode support."""
    return SYMBOLS.get(name, '') if USE_UNICODE else ASCII_SYMBOLS.get(name, '')


STATUS_STYLES = {
    "success": (get_symbol("success"), Fore.GREEN),
    "error": (get_symbol("error"), Fore.RED),
    "warning": (get_symbol("warning"), Fore.YELLOW),
    "info": (get_symbol("info"), Fore.BLUE),
}


_cached_terminal_width = 0
_cached_terminal_width_time = float('-inf')


def get_terminal_width() -> int:
    global _cached_terminal_width, _cached_terminal_width_time
    now = time.monotonic()
    if now - _cached_terminal_width_time > 1.0:
        _cached_terminal_width = shutil.get_terminal_size().columns if hasattr(shutil, 'get_terminal_size') else 80
        _cached_terminal_width_time = now
    return _cached_terminal_width


def print_status(message: str, status: Optional[str] = None) -> None:
    """Unified function for printing status messages with colors and symbols."""
    prefix, color = STATUS_STYLES.get(status, (None, None))
    if prefix:
        print(
            f"{color}{prefix} {message}{Style.RESET_ALL}"
            if COLOR_SUPPORT
            else f"{prefix} {message}"
        )
    else:
        print(message)


def print_header(title: str, width: Optional[int] = None) -> None:
    width = width or get_terminal_width()
    if COLOR_SUPPORT:
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{title}\n{'-' * min(len(title), width)}{Style.RESET_ALL}")
    else:
        print(f"\n{title}\n{'-' * min(len(title), width)}")


def print_success(message: str) -> None:
    print_status(message, "success")


def print_error(message: str) -> None:
    print_status(message, "error")


def print_warning(message: str) -> None:
    print_status(message, "warning")


def print_info(message: str) -> None:
    print_status(message, "info")


def print_connection_status(hostname: str, status: str, time_taken: Optional[float] = None) -> None:
    """Print connection status with color coding."""
    if status == "connecting":
        msg = f"{get_symbol('connecting')} Connecting to {hostname}..."
        if COLOR_SUPPORT:
            print(f"{Fore.YELLOW}{msg}{Style.RESET_ALL}", end="\r")
        else:
            print(msg, end="\r")
    elif status == "success":
        msg = f"{get_symbol('success')} Connected to {hostname}" + (f" in {time_taken:.2f}s" if time_taken else "")
        if COLOR_SUPPORT:
            print(f"{Fore.GREEN}{msg}{Style.RESET_ALL}")
        else:
            print(msg)
    elif status == "error":
        msg = f"{get_symbol('error')} Connection to {hostname} failed"
        if COLOR_SUPPORT:
            print(f"{Fore.RED}{msg}{Style.RESET_ALL}")
        else:
            print(msg)
    elif status == "timeout":
        msg = f"{get_symbol('clock')} Connection to {hostname} timed out"
        if COLOR_SUPPORT:
            print(f"{Fore.RED}{msg}{Style.RESET_ALL}")
        else:
            print(msg)


def format_server_info(server: ServerInfo) -> str:
    symbol = get_symbol('server')
    separator = "  " if USE_UNICODE and symbol == "🖥" else " "
    hostname_part = colorize(f"{symbol}{separator}{server.hostname}", Fore.CYAN)
    location_part = colorize(f"({server.city}, {server.country})", Fore.WHITE)
    distance_part = colorize(f"{server.distance_km:.0f} km", Fore.YELLOW)
    return f"{hostname_part} {location_part} {distance_part}"


def format_mtr_results(result) -> str:
    mode = "Ping" if result.hops == 0 else "MTR"
    msg = (
        f"{get_symbol('ping')} {mode} — Latency: {result.avg_latency:.2f} ms | "
        f"Loss: {result.packet_loss:.2f}%"
    )
    if result.hops > 0:
        msg += f" | Hops: {result.hops}"
    return colorize(msg, Fore.YELLOW)


def format_speedtest_results(result) -> str:
    download = colorize(f"{get_symbol('download')} {result.download_speed:.2f} Mbps", Fore.GREEN)
    upload = colorize(f"{get_symbol('upload')} {result.upload_speed:.2f} Mbps", Fore.BLUE)
    ping = colorize(f"{get_symbol('ping')} {result.ping:.2f} ms", Fore.YELLOW)
    return (
        f"{download} | {upload} | {ping} | "
        f"Jitter: {result.jitter:.2f} ms | Loss: {result.packet_loss:.2f}%"
    )


# Progress bar color thresholds (percentage -> color name)
PROGRESS_COLOR_THRESHOLDS = [
    (16, "GREEN"),
    (33, "LIGHTGREEN_EX"),
    (50, "YELLOW"),
    (66, "LIGHTYELLOW_EX"),
    (83, "LIGHTRED_EX"),
]

# Fallback thresholds when extended colors aren't available
FALLBACK_COLOR_THRESHOLDS = [
    (33, "GREEN"),
    (66, "YELLOW"),
]


def print_progress_bar(iteration: float, total: float, prefix: str = '',
                        suffix: str = '', length: int = 50, fill: str = '█') -> None:
    """Print a progress bar with gradient colors from green to red."""
    percent = 100 * (iteration / float(total))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + ' ' * (length - filled_length)

    if COLOR_SUPPORT:
        try:
            for threshold, color_name in PROGRESS_COLOR_THRESHOLDS:
                if percent <= threshold:
                    color = getattr(Fore, color_name)
                    break
            else:
                color = Fore.RED
        except AttributeError:  # pragma: no cover - limited color support
            for threshold, color_name in FALLBACK_COLOR_THRESHOLDS:
                if percent <= threshold:
                    color = getattr(Fore, color_name)
                    break
            else:
                color = Fore.RED
        print(
            f'\r{prefix} {color}{bar}{Style.RESET_ALL} {percent:.1f}% {suffix}',
            end='\r',
        )
    else:
        print(f'\r{prefix} {bar} {percent:.1f}% {suffix}', end='\r')
    if iteration == total:
        print()


def run_with_spinner(message, action, timeout=None):
    """Display a spinner while running an action."""
    spinner = cycle(['|', '/', '-', '\\'])
    stop_event = threading.Event()
    result = {'value': None, 'error': None}

    def runner():
        try:
            result['value'] = action(stop_event)
        except Exception as e:  # pragma: no cover - pass through errors
            result['error'] = e
        finally:
            stop_event.set()

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    start_time = time.time()
    timed_out = False

    try:
        while thread.is_alive():
            elapsed = time.time() - start_time
            if timeout is not None and elapsed >= timeout:
                timed_out = True
                stop_event.set()
            if timeout is not None:
                time_info = f"({max(0, timeout - elapsed):.0f}s remaining)"
            else:
                time_info = f"({elapsed:.1f}s)"
            print(f"\r{message} {next(spinner)} {time_info} ", end='', flush=True)
            time.sleep(0.1)
    finally:
        thread.join()
        print(f"\r{' ' * get_terminal_width()}\r", end='')
        print()

    elapsed_total = time.time() - start_time
    if result['error'] and not timed_out:
        raise result['error']
    return result.get('value'), timed_out, elapsed_total


class DisplayManager:
    """Simple wrapper around printing utilities aware of interactivity."""

    def __init__(self, interactive: bool):
        self.interactive = interactive
        if not self.interactive:
            noop = lambda *args, **kwargs: None
            self.success = noop
            self.error = noop
            self.warning = noop
            self.info = noop
            self.header = noop
            self.connection_status = noop
            self.progress_bar = noop
            # Keep execution methods active in non-interactive mode.
            self.spinner = self._run_action_silently
            self.run_command_with_spinner = self._run_command_silently

    def _run_action_silently(self, message, action, timeout=None):
        """Run an action without terminal animation in non-interactive mode."""
        stop_event = threading.Event()
        result = {'value': None, 'error': None}

        def runner():
            try:
                result['value'] = action(stop_event)
            except Exception as e:  # pragma: no cover - pass through errors
                result['error'] = e

        thread = threading.Thread(target=runner, daemon=True)
        start_time = time.time()
        thread.start()
        thread.join(timeout=timeout)

        timed_out = thread.is_alive()
        if timed_out:
            stop_event.set()
            thread.join()

        elapsed = time.time() - start_time
        if result['error'] and not timed_out:
            raise result['error']
        return result.get('value'), timed_out, elapsed

    def _run_command_silently(self, cmd, message, timeout=None):
        """Run a subprocess command without spinner in non-interactive mode."""
        start_time = time.time()
        try:
            completed = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                check=False,
            )
            elapsed = time.time() - start_time
            return completed.stdout, completed.stderr, completed.returncode, False, elapsed
        except subprocess.TimeoutExpired as exc:
            elapsed = time.time() - start_time
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            return stdout, stderr, 124, True, elapsed

    def success(self, message: str) -> None:
        print_success(message)

    def error(self, message: str) -> None:
        print_error(message)

    def warning(self, message: str) -> None:
        print_warning(message)

    def info(self, message: str) -> None:
        print_info(message)

    def header(self, title: str, width: Optional[int] = None) -> None:
        print_header(title, width)

    def connection_status(self, hostname: str, status: str, time_taken: Optional[float] = None) -> None:
        print_connection_status(hostname, status, time_taken)

    def progress_bar(self, *args, **kwargs) -> None:
        print_progress_bar(*args, **kwargs)

    def spinner(self, message, action, timeout=None):
        return run_with_spinner(message, action, timeout)

    def run_command_with_spinner(self, cmd, message, timeout=None):
        """Run a subprocess command while displaying a spinner.

        Returns (stdout, stderr, returncode, timed_out, elapsed)."""

        def action(stop_event):
            process = subprocess.Popen(
                cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            while process.poll() is None and not stop_event.is_set():
                time.sleep(0.1)
            if process.poll() is None:
                process.terminate()
            stdout, stderr = process.communicate()
            return stdout, stderr, process.returncode

        (stdout, stderr, returncode), timed_out, elapsed = self.spinner(
            message, action, timeout=timeout
        )
        return stdout, stderr, returncode, timed_out, elapsed
