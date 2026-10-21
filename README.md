# MCP-Bridge-Kit

[![CI Status](https://github.com/Hakantes/mcp-bridge-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/Hakantes/mcp-bridge-kit/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.12+](https://img.shields.io/badge/python-3.12%2B-brightgreen.svg)](https://www.python.org/)

**Hardened Model Context Protocol (MCP) developer server and automated JSON-RPC protocol compliance verifier.**

---

## The Problem

The Model Context Protocol (MCP) has rapidly emerged as the open industry standard connecting LLMs and agentic assistants (like Claude Desktop, Cursor, and autonomous agent loops) with tools, data sources, and dev environments. 

However, building and maintaining custom Python MCP servers surfaces severe friction:
1. **The "stdio Trap":** When local desktop hosts launch Python MCP servers over stdio, any stray `print()`, package initialization log, or warning output to stdout corrupts JSON-RPC 2.0 framing, crashing the client connection silently.
2. **Security Sandboxing Gaps:** Custom file tools frequently lack path-traversal guards, exposing local systems to arbitrary path traversal (`../../etc/passwd` or `../../Windows`).
3. **Absence of Compliance Tooling:** Developers have lacked a fast, automated test harness to verify whether their server correctly implements the MCP handshake (`initialize`), error codes (`-32601`), and schema definitions.

## The Solution: MCP-Bridge-Kit

**MCP-Bridge-Kit** delivers a dual-capability toolkit for the MCP ecosystem:
- **Hardened MCP Developer Server:** Pre-configured with essential developer tools (`read_file`, `write_file`, `list_directory`, `get_env`, `git_status`, `run_command`).
- **Path-Traversal Guardrails:** Strict chroot containment blocks any access outside the designated sandbox root directory.
- **Stdout Channel Shielding:** All diagnostics, logs, and warnings are strictly redirected to `sys.stderr`, preserving 100% protocol cleanliness on stdout.
- **Automatic Secret Scrubbing:** Environment variable inspections automatically mask sensitive tokens (`KEY`, `SECRET`, `PASSWORD`, `TOKEN`).
- **Automated Conformance Verifier (`mcp-verify`):** A standalone CLI harness that launches any target MCP server, executes the complete handshake lifecycle, validates tool schemas, detects stdout pollution, and benchmarks latency.

---

## Architecture Overview

```
                          +------------------------+
                          |   Agent Host (Client)  |
                          +-----------+------------+
                                      |
                      JSON-RPC 2.0 stdio (Clean Stream)
                                      |
                                      v
                          +------------------------+
                          |  Hardened MCP Server   |
                          |  - stderr logging only |
                          |  - JSON-RPC 2.0 router |
                          +-----------+------------+
                                      |
              +-----------------------+-----------------------+
              |                       |                       |
              v                       v                       v
     +-----------------+     +-----------------+     +-----------------+
     | Sandboxed Files |     | Masked Env Info |     | Command Guard   |
     | (Path traversal |     | (Auto-scrubbed  |     | (Isolated pipes |
     |  prevention)    |     |  tokens)        |     |  with timeout)  |
     +-----------------+     +-----------------+     +-----------------+

                                     ***
                          +------------------------+
                          |   mcp-verify Harness   |
                          | (Tests ANY MCP Server) |
                          +------------------------+
```

---

## Installation

### From Source (Local Development)
```bash
git clone https://github.com/Hakantes/mcp-bridge-kit.git
cd mcp-bridge-kit
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

---

## Quick-Start Guide

### 1. Run the Hardened Server in Claude Desktop / Cursor
Add the following to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "mcp-bridge": {
      "command": "mcp-bridge",
      "args": ["serve", "--sandbox", "/path/to/your/project"]
    }
  }
}
```

### 2. Verify an MCP Server with `mcp-verify`
Test any local or third-party MCP server for specification compliance and stdout cleanliness:
```bash
mcp-verify --command "python -m mcp_bridge.cli serve"
```

---

## Tools Provided by MCP Server

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `read_file` | `path: string` | Safely reads text content within sandbox root |
| `write_file` | `path: string, content: string` | Safely writes text content within sandbox root |
| `list_directory`| `path: string` (optional) | Lists files and directories within sandbox |
| `get_env` | `filter_prefix: string` (optional) | Inspects environment variables with automatic credential masking |
| `git_status` | None | Returns concise git working tree status |
| `run_command` | `command: string, timeout_seconds: int` | Executes command with strict timeouts and separate stderr |

---

## CLI Reference

| Command | Option | Description |
| :--- | :--- | :--- |
| `mcp-bridge serve` | `--sandbox, -s <dir>` | Start MCP stdio server confined to target directory |
| `mcp-verify` | `--command, -c <cmd>` | Run automated JSON-RPC conformance check against target command |

---

## Testing

Run unit and integration tests using pytest:
```bash
pytest -v
```

---

## Security and Privacy Notes

- **Path Escape Confinement:** Target paths are resolved to their canonical paths and validated using `Path.is_relative_to(sandbox_root)`. Any `../` attempt escaping the root immediately triggers an error without file access.
- **Credential Masking:** Environment inspection matches against sensitive keywords and redacts values as `******** [REDACTED SENSITIVE KEY]`.
- **Subprocess Isolation:** Commands run with explicit timeout limits, preventing un-reaped zombie processes.

---

## Known Limitations

- Supported transport in v0.1.0 is stdio. Streamable HTTP / Server-Sent Events (SSE) remote transport is scheduled for v0.2.0.
- Prompts and Resources capabilities are parsed in initialization but tool execution is the primary vertical slice in v0.1.0.

---

## Contributing and License

Contributions are welcome! Please check [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.
