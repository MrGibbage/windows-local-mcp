# windows-local-mcp

A local Windows MCP server for Claude Code. Runs as a stdio subprocess managed by Claude Code — no network port, no service, no auth tokens.

## Tools

| Tool | Description |
|------|-------------|
| `get_latest_screenshot()` | Returns the most recent `.png` from the screenshots directory as image content |
| `get_recent_screenshots(n=2)` | Returns the N most recent screenshots as image content, newest first (max 5) |
| `list_screenshots(n=10)` | Returns filenames + timestamps of the N most recent screenshots (no image data loaded) |
| `get_screenshot(filename)` | Returns a specific screenshot by basename — use after `list_screenshots` |
| `get_clipboard()` | Returns current clipboard text — may contain sensitive data, never logged |
| `get_active_window()` | Returns the title of the currently focused window |
| `send_notification(title, message)` | Sends a Windows toast notification |
| `get_system_info()` | Returns OS version, hostname, uptime, user, monitor resolutions |

## Setup

### 1. Install dependencies

```
pip install -r requirements.txt
```

> **Note:** After installing `pywin32`, run the post-install script once:
> ```
> python -m pywin32_postinstall -install
> ```

### 2. Wire into Claude Code

Add the following entry to `~/.claude.json` under the `mcpServers` key:

```json
"windows-local": {
  "command": "python",
  "args": ["C:/Users/skip/windows-local-mcp/server.py"],
  "env": {
    "WINDOWS_MCP_SCREENSHOT_DIR": "C:/Users/skip/Pictures/Screenshots"
  }
}
```

Replace the path in `args` with the actual location of `server.py` on your machine. Adjust `WINDOWS_MCP_SCREENSHOT_DIR` if your screenshots are stored elsewhere. Omit the `env` block entirely to use the compiled-in default (`C:/Users/skip/Pictures/Screenshots`).

### 3. Restart Claude Code

The MCP server starts automatically on the next Claude Code session.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WINDOWS_MCP_SCREENSHOT_DIR` | `C:/Users/skip/Pictures/Screenshots` | Directory scanned for screenshots |

## Security notes

- **No credentials or secrets** are stored in this project.
- `get_screenshot` validates that the resolved file path stays inside the screenshots directory — path traversal attempts (`../`, absolute paths) are rejected.
- `get_clipboard` output is never logged; callers should treat it as potentially sensitive.
- File access is limited to the screenshots directory — no arbitrary filesystem reads.
- No shell commands or subprocesses are executed by any tool.
- Toast notifications via `winotify` use the Windows Runtime API directly, not PowerShell.

## Dependencies

- **mcp** — MCP server SDK with FastMCP
- **pywin32** — Win32 API bindings (clipboard, active window)
- **winotify** — Windows toast notifications via Windows Runtime
- **screeninfo** — Cross-platform monitor resolution enumeration
