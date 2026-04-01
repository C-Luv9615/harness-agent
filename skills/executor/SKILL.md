---
name: executor
description: "Manage persistent interactive CLI processes (REPLs, debuggers, database CLIs, NuttX simulator, QEMU). Use when process maintains state across commands. NOT for one-off commands - use Bash. Prefer over tmux for programmatic I/O without terminal emulation."
---

# Executor

Manage persistent interactive CLI processes with stateful stdin/stdout communication via MCP tools.

**Pattern:** Start → Send* → Read* → Stop

## Prerequisites

This skill requires the executor-mcp MCP server to be installed and configured.

**Installation:**
```bash
pip install executor-mcp
```

**Configuration:** Add to Claude Desktop config (`~/.config/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "executor": {
      "command": "executor-mcp"
    }
  }
}
```

## When to Use

| Scenario | Tool |
|----------|------|
| REPL / debugger / database CLI / NuttX sim / QEMU | **executor** |
| One-off command that completes immediately | Bash |
| Need terminal emulation (curses, colors, vi) | tmux |
| Multiple concurrent interactive sessions to monitor | tmux |

Use executor when:
- Process has a prompt and maintains state (Python REPL, gdb, psql, node)
- You need programmatic access to stdin/stdout without terminal complexity
- You want automatic buffering and logging of all I/O

## Core Tools

All tools return JSON responses. Parameters shown below.

### {EXECUTOR_MCP}_start

Launch a new interactive process.

**Parameters:**
```json
{
  "command": "python3",
  "args": ["-i"],
  "working_dir": "/optional/path"
}
```

**Returns:** `process_id` (unique identifier for subsequent operations)

### {EXECUTOR_MCP}_send

Send text to process stdin and optionally wait for output.

**Parameters:**
```json
{
  "process_id": "abc123",
  "text": "x = 42",
  "wait_time": 0.1,
  "add_newline": true,
  "tail_lines": 20,
  "full_buffer": false
}
```

**Key parameters:**
- `wait_time`: Seconds to wait before reading (default: 0.1)
  - `> 0`: Wait and return NEW output from this command
  - `0`: Send immediately, use `{EXECUTOR_MCP}_read_output` later
- `full_buffer`: If true, return full buffer instead of just new output (default: false)
- `tail_lines`: Lines to return when using `full_buffer=true` (default: 20)

**Returns:** New output lines if `wait_time > 0`, otherwise "Success"

### {EXECUTOR_MCP}_read_output

Read buffered output from stdout/stderr.

**Parameters:**
```json
{
  "process_id": "abc123",
  "tail_lines": 50,
  "stream": "both"
}
```

**Parameters:**
- `tail_lines`: Number of recent lines (default: all buffered, max 1000)
- `stream`: "both" (merged), "stdout", or "stderr" (default: "both")

**Returns:** Buffered output lines (last 1000 lines kept in memory)

### {EXECUTOR_MCP}_stop

Terminate a running process.

**Parameters:**
```json
{
  "process_id": "abc123",
  "force": false
}
```

- `force`: `true` = SIGKILL, `false` = SIGTERM graceful (default)

### {EXECUTOR_MCP}_list

List all active processes (no parameters).

**Returns:** Array of process info (process_id, command, status, buffer sizes)

### {EXECUTOR_MCP}_get_info

Get detailed information about a specific process.

**Parameters:**
```json
{
  "process_id": "abc123"
}
```

**Returns:** Full process state, buffer sizes, recent output preview

## Examples

### Python REPL

```python
# Start Python with unbuffered output
{EXECUTOR_MCP}_start(command="python3", args=["-i", "-u"])
# → Returns: {"process_id": "abc123", ...}

# Wait for startup banner (0.3s)
{EXECUTOR_MCP}_send(process_id="abc123", text="x = 42", wait_time=0.3)
# → Returns new output: [">>> ", "x = 42\n", ">>> "]

# Execute and read output
{EXECUTOR_MCP}_send(process_id="abc123", text="print(x * 2)")
# → Returns: ["print(x * 2)\n", "84\n", ">>> "]

# Stop when done
{EXECUTOR_MCP}_stop(process_id="abc123")
```

### GDB Debugging

```python
# Start debugger
{EXECUTOR_MCP}_start(command="gdb", args=["--quiet", "./binary"])
# → process_id: "def456"

# Disable pagination
{EXECUTOR_MCP}_send(process_id="def456", text="set pagination off", wait_time=0.2)

# Set breakpoint
{EXECUTOR_MCP}_send(process_id="def456", text="break main", wait_time=0.2)

# Run program
{EXECUTOR_MCP}_send(process_id="def456", text="run", wait_time=0.5)

# Examine variables
{EXECUTOR_MCP}_send(process_id="def456", text="info locals")

# Exit debugger
{EXECUTOR_MCP}_stop(process_id="def456")
```

### Database CLI (PostgreSQL)

```python
# Connect to database
{EXECUTOR_MCP}_start(command="psql", args=["dbname", "-U", "user"])
# → process_id: "ghi789"

# Run query (wait for results)
{EXECUTOR_MCP}_send(
    process_id="ghi789",
    text="SELECT * FROM users LIMIT 5;",
    wait_time=0.5
)
# → Returns query results

# List tables
{EXECUTOR_MCP}_send(process_id="ghi789", text="\\dt")

# Disconnect
{EXECUTOR_MCP}_send(process_id="ghi789", text="\\q", wait_time=0)
{EXECUTOR_MCP}_stop(process_id="ghi789")
```

### Fast Batch Commands (No Wait)

```python
# Start process
{EXECUTOR_MCP}_start(command="python3", args=["-i"])
# → process_id: "jkl012"

# Queue multiple commands without waiting
{EXECUTOR_MCP}_send(process_id="jkl012", text="import sys", wait_time=0)
{EXECUTOR_MCP}_send(process_id="jkl012", text="import os", wait_time=0)
{EXECUTOR_MCP}_send(process_id="jkl012", text="import json", wait_time=0)

# Read all output at once
output = {EXECUTOR_MCP}_read_output(process_id="jkl012", tail_lines=50)
```

### NuttX Simulator

```python
# Start NuttX simulator
{EXECUTOR_MCP}_start(command="./nuttx/nuttx", working_dir="/path/to/nuttx")
# → process_id: "mno345"

# Wait for NSH prompt
{EXECUTOR_MCP}_send(process_id="mno345", text="help", wait_time=0.5)

# Run NuttX commands
{EXECUTOR_MCP}_send(process_id="mno345", text="ps")
{EXECUTOR_MCP}_send(process_id="mno345", text="free")

# Exit simulator
{EXECUTOR_MCP}_send(process_id="mno345", text="exit", wait_time=0)
{EXECUTOR_MCP}_stop(process_id="mno345", force=true)
```

## Complete Workflow Example

Debugging a Python script that crashes:

```python
# 1. Start Python debugger with script
{EXECUTOR_MCP}_start(command="python3", args=["-i", "buggy_script.py"])
# → process_id: "debug001"

# 2. Script crashes, now inspect
{EXECUTOR_MCP}_send(process_id="debug001", text="import traceback")
{EXECUTOR_MCP}_send(process_id="debug001", text="traceback.print_exc()")

# 3. Inspect variables at crash point
{EXECUTOR_MCP}_send(process_id="debug001", text="print(locals())")

# 4. Test fix interactively
{EXECUTOR_MCP}_send(process_id="debug001", text="x = corrected_value")
{EXECUTOR_MCP}_send(process_id="debug001", text="retry_operation(x)")

# 5. Verify fix works
output = {EXECUTOR_MCP}_read_output(process_id="debug001", tail_lines=20)

# 6. Exit when done
{EXECUTOR_MCP}_stop(process_id="debug001")
```

## Error Handling

Common errors and solutions:

| Error Pattern | Cause | Solution |
|---------------|-------|----------|
| `FileNotFoundError` | Binary not found | Check path, use absolute path |
| `PermissionError` | Not executable | `chmod +x` the binary |
| `Process died` | Binary crashed | Check logs in `.executorlog/` |
| `No output` | Buffered output | Use `-u` flag for Python, wait longer |
| `BrokenPipeError` | Process stdin closed | Process may have exited, check status |

**Debugging steps:**
1. Check if process is still running: `{EXECUTOR_MCP}_get_info(process_id)`
2. Review complete I/O history in log files: `.executorlog/{process_id}_{timestamp}_{command}.log`
3. Verify process exit code and error stream
4. For slow processes, increase `wait_time` (0.3-0.5s)

## Best Practices

- **Always use unbuffered mode** for Python: `python3 -u` or `python3 -i`
- **Adjust wait_time** based on command complexity:
  - Fast commands (variable assignment): 0.1s (default)
  - Medium commands (queries, calculations): 0.3s
  - Slow commands (compilations, heavy queries): 0.5s+
- **Use wait_time=0 for batch operations** when you don't need immediate output
- **Always call {EXECUTOR_MCP}_stop** when done to prevent orphaned processes
- **Check logs** (`.executorlog/`) for debugging - all I/O is timestamped
- **Use {EXECUTOR_MCP}_list** periodically to audit running processes

## Logging

All I/O is automatically logged to:

**Location:** `.executorlog/{process_id}_{timestamp}_{command}.log`

**Format:**
```
=== Executor MCP Process Log ===
Process ID: abc123
Command: python3
Started: 2026-01-07T12:00:00
==================================================

[2026-01-07 12:00:00.123] COMMAND: python3 -i -u
[2026-01-07 12:00:00.456] STDOUT: Python 3.13.0 ...
[2026-01-07 12:00:01.789] STDIN: x = 42
[2026-01-07 12:00:01.890] STDOUT: >>>
[2026-01-07 12:00:02.012] STDIN: print(x * 2)
[2026-01-07 12:00:02.123] STDOUT: 84
[2026-01-07 12:00:05.567] TERMINATED: Method: SIGTERM, Return code: 0
```

Configure log directory:
```bash
export EXECUTOR_LOG_DIR="$HOME/.executor-mcp/logs"
```

## Architecture Notes

- **Buffer:** Last 1000 lines kept in memory per stream (stdout/stderr)
- **Concurrency:** Multiple processes can run simultaneously
- **Non-blocking:** All operations use async I/O
- **Transport:** MCP stdio (separate from managed process I/O)
- **Logging:** Complete history in files, circular buffer in memory
