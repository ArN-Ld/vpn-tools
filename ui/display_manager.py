import sys
import shutil
import subprocess
import threading
import time
from typing import Optional

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


def colorize(text: str, color: str = "") -> str:
    """Return text wrapped in ANSI color codes if supported."""
    return f"{color}{text}{Style.RESET_ALL}" if COLOR_SUPPORT and color else text


def get_symbol(name: str) -> str:
    """Return a symbol by name, respecting Unicode support."""
    return SYMBOLS.get(name, '') if USE_UNICODE else ASCII_SYMBOLS.get(name, '')


def get_terminal_width() -> int:
    return shutil.get_terminal_size().columns if hasattr(shutil, 'get_terminal_size') else 80


def print_status(message: str, status: Optional[str] = None) -> None:
    """Unified function for printing status messages with colors and symbols."""
    if status == "success":
        prefix, color = get_symbol('success'), Fore.GREEN
    elif status == "error":
        prefix, color = get_symbol('error'), Fore.RED
    elif status == "warning":
        prefix, color = get_symbol('warning'), Fore.YELLOW
    elif status == "info":
        prefix, color = get_symbol('info'), Fore.BLUE
    else:
        print(message)
        return
    print(f"{color}{prefix} {message}{Style.RESET_ALL}" if COLOR_SUPPORT else f"{prefix} {message}")


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


def format_server_info(server) -> str:
    hostname_part = colorize(f"{get_symbol('server').rstrip()} {server.hostname}", Fore.CYAN)
    location_part = colorize(f"({server.city}, {server.country})", Fore.WHITE)
    distance_part = colorize(f"{server.distance_km:.0f} km", Fore.YELLOW)
    return f"{hostname_part} {location_part} {distance_part}"


def format_mtr_results(result) -> str:
    msg = (
        f"{get_symbol('ping')} Latency: {result.avg_latency:.2f} ms | "
        f"Loss: {result.packet_loss:.2f}% | Hops: {result.hops}"
    )
    return colorize(msg, Fore.YELLOW)


def format_speedtest_results(result) -> str:
    download = colorize(f"{get_symbol('download')} {result.download_speed:.2f} Mbps", Fore.GREEN)
    upload = colorize(f"{get_symbol('upload')} {result.upload_speed:.2f} Mbps", Fore.BLUE)
    ping = colorize(f"{get_symbol('ping')} {result.ping:.2f} ms", Fore.YELLOW)
    return (
        f"{download} | {upload} | {ping} | "
        f"Jitter: {result.jitter:.2f} ms | Loss: {result.packet_loss:.2f}%"
    )


def print_progress_bar(iteration: float, total: float, prefix: str = '',
                        suffix: str = '', length: int = 50, fill: str = '█') -> None:
    """Print a progress bar with gradient colors from green to red."""
    percent = 100 * (iteration / float(total))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + ' ' * (length - filled_length)

    if COLOR_SUPPORT:
        try:
            if percent <= 16:
                color = Fore.GREEN
            elif percent <= 33:
                color = Fore.LIGHTGREEN_EX
            elif percent <= 50:
                color = Fore.YELLOW
            elif percent <= 66:
                color = Fore.LIGHTYELLOW_EX
            elif percent <= 83:
                color = Fore.LIGHTRED_EX
            else:
                color = Fore.RED
        except AttributeError:  # pragma: no cover - limited color support
            if percent <= 33:
                color = Fore.GREEN
            elif percent <= 66:
                color = Fore.YELLOW
            else:
                color = Fore.RED
        print(f'\r{prefix} {color}{bar}{Style.RESET_ALL} {percent:.1f}% {suffix}', end='\r')
    else:
        print(f'\r{prefix} {bar} {percent:.1f}% {suffix}', end='\r')
    if iteration == total:
        print()


def run_with_spinner(message, action, timeout=None):
    """Display a spinner while running an action."""
    spinner_chars = ['|', '/', '-', '\\']
    spinner_idx = 0
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
            print(f"\r{message} {spinner_chars[spinner_idx]} {time_info} ", end='', flush=True)
            spinner_idx = (spinner_idx + 1) % len(spinner_chars)
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

    def success(self, message: str) -> None:
        if self.interactive:
            print_success(message)

    def error(self, message: str) -> None:
        if self.interactive:
            print_error(message)

    def warning(self, message: str) -> None:
        if self.interactive:
            print_warning(message)

    def info(self, message: str) -> None:
        if self.interactive:
            print_info(message)

    def header(self, title: str, width: Optional[int] = None) -> None:
        if self.interactive:
            print_header(title, width)

    def connection_status(self, hostname: str, status: str, time_taken: Optional[float] = None) -> None:
        if self.interactive:
            print_connection_status(hostname, status, time_taken)

    def progress_bar(self, *args, **kwargs) -> None:
        if self.interactive:
            print_progress_bar(*args, **kwargs)

    def spinner(self, message, action, timeout=None):
        if self.interactive:
            return run_with_spinner(message, action, timeout)
        # Non-interactive: run action directly
        stop_event = threading.Event()
        start = time.time()
        value = action(stop_event)
        elapsed = time.time() - start
        return value, False, elapsed

    def run_command_with_spinner(self, cmd, message, timeout=None):
        """Run a subprocess command while displaying a spinner.

        Returns (stdout, stderr, returncode, timed_out, elapsed)."""
        if self.interactive:
            def action(stop_event):
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
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

        start = time.time()
        try:
            completed = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout
            )
            return (
                completed.stdout,
                completed.stderr,
                completed.returncode,
                False,
                time.time() - start,
            )
        except subprocess.TimeoutExpired:
            return "", "", None, True, time.time() - start
        except Exception as e:  # pragma: no cover - unexpected errors
            return "", str(e), 1, False, time.time() - start
