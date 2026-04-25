#!/usr/bin/env python3
"""
Windows Local MCP Server for Claude Code
Provides tools for screenshots, clipboard, system info, and Windows notifications.
Runs as a stdio subprocess managed by Claude Code — no network port or auth needed.
"""

import base64
import ctypes
import os
import platform
import socket
from datetime import datetime, timedelta
from pathlib import Path

import win32clipboard
import win32con
import win32gui
from screeninfo import get_monitors
from winotify import Notification

from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent

# Screenshot directory — set WINDOWS_MCP_SCREENSHOT_DIR env var to override this default
SCREENSHOTS_DIR = Path(
    os.environ.get("WINDOWS_MCP_SCREENSHOT_DIR", "C:/Users/skip/Pictures/Screenshots")
)

mcp = FastMCP("windows-local")


def _sorted_screenshots() -> list[Path]:
    """Return PNG files in SCREENSHOTS_DIR sorted by mtime, newest first."""
    if not SCREENSHOTS_DIR.exists():
        return []
    return sorted(
        SCREENSHOTS_DIR.glob("*.png"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def _path_to_image(path: Path) -> ImageContent:
    """Read a PNG file and return it as MCP ImageContent."""
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return ImageContent(type="image", data=data, mimeType="image/png")


@mcp.tool()
def get_latest_screenshot() -> ImageContent:
    """Return the single most recent screenshot as image content."""
    shots = _sorted_screenshots()
    if not shots:
        raise ValueError(f"No screenshots found in {SCREENSHOTS_DIR}")
    return _path_to_image(shots[0])


@mcp.tool()
def get_recent_screenshots(n: int = 2) -> list[ImageContent]:
    """Return the N most recent screenshots as image content, newest first. Max 5."""
    n = min(max(1, n), 5)
    shots = _sorted_screenshots()[:n]
    if not shots:
        raise ValueError(f"No screenshots found in {SCREENSHOTS_DIR}")
    return [_path_to_image(p) for p in shots]


@mcp.tool()
def list_screenshots(n: int = 10) -> str:
    """
    Return a text list of the N most recent screenshot filenames with modification timestamps.
    No image data is loaded. Use this to identify which screenshot to fetch with get_screenshot.
    """
    shots = _sorted_screenshots()[:n]
    if not shots:
        return f"No screenshots found in {SCREENSHOTS_DIR}"
    lines = []
    for p in shots:
        mtime = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"{p.name}  ({mtime})")
    return "\n".join(lines)


@mcp.tool()
def get_screenshot(filename: str) -> ImageContent:
    """
    Return a specific screenshot by filename (basename only — no path components).
    Use list_screenshots first to identify available filenames.
    """
    # Strip all directory components — this is the primary path traversal defense
    safe_name = Path(filename).name
    if not safe_name:
        raise ValueError("Filename cannot be empty")

    target = (SCREENSHOTS_DIR / safe_name).resolve()
    resolved_dir = SCREENSHOTS_DIR.resolve()

    # Secondary check: ensure resolved path is inside the screenshots directory
    try:
        target.relative_to(resolved_dir)
    except ValueError:
        raise ValueError(f"Invalid filename: {filename!r}")

    if target.suffix.lower() != ".png":
        raise ValueError(f"Only .png files are supported, got: {target.suffix!r}")
    if not target.exists():
        raise FileNotFoundError(f"Screenshot not found: {safe_name}")

    return _path_to_image(target)


@mcp.tool()
def get_clipboard() -> str:
    """
    Return current clipboard text content.

    NOTE: Clipboard may contain sensitive data (passwords, API tokens, PII).
    This tool does not filter or sanitize output. Output is never logged by this server.
    """
    win32clipboard.OpenClipboard()
    try:
        if not win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            return "(clipboard is empty or contains non-text content)"
        return win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
    finally:
        win32clipboard.CloseClipboard()


@mcp.tool()
def get_active_window() -> str:
    """Return the title of the currently focused window."""
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd)
    return title or "(no active window or window has no title)"


@mcp.tool()
def send_notification(title: str, message: str) -> str:
    """
    Send a Windows toast notification. Useful for signaling completion of long-running tasks.
    Returns a confirmation string.
    """
    toast = Notification(
        app_id="Claude Code",
        title=title,
        msg=message,
        duration="short",
    )
    toast.show()
    return f"Notification sent: title={title!r}"


@mcp.tool()
def get_system_info() -> dict:
    """
    Return basic system information: OS version, hostname, uptime, current user,
    and per-monitor screen resolutions. No sensitive data (no env vars, no network config).
    """
    # GetTickCount64 avoids the 49.7-day rollover of GetTickCount
    uptime_ms = ctypes.windll.kernel32.GetTickCount64()
    uptime = str(timedelta(milliseconds=uptime_ms)).split(".")[0]

    monitors = [{"width": m.width, "height": m.height} for m in get_monitors()]

    return {
        "windows_version": platform.version(),
        "windows_release": platform.release(),
        "hostname": socket.gethostname(),
        "current_user": os.environ.get("USERNAME", "unknown"),
        "uptime": uptime,
        "monitor_count": len(monitors),
        "monitors": monitors,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
