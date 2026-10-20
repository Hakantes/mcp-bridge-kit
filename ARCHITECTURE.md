# MCP-Bridge-Kit Architecture

## System Overview

MCP-Bridge-Kit provides two complementary tools for the Model Context Protocol ecosystem:
1. **A Hardened MCP Developer Server**: Exposing core developer tools with strict path-traversal sandboxing, secret masking, and isolated execution.
2. **An Automated Protocol Conformance Verifier (`mcp-verify`)**: Testing any third-party or local MCP server for JSON-RPC 2.0 conformance, stdout pollution, and error handling.

```
+-----------------------------------------------------------------------+
|                           MCP Host / Client                           |
|                  (Claude Desktop, Cursor, Agent Loop)                 |
+-----------------------------------+-----------------------------------+
                                    |
                    JSON-RPC 2.0 stdio (Framed Streams)
                                    |
                                    v
+-----------------------------------------------------------------------+
|                       Hardened MCP Server Core                        |
|   - Output Channel Shield: Redirects all diagnostic logs to stderr    |
|   - Request Router: initialize, tools/list, tools/call, ping          |
|   - Error Boundary: Catches uncaught tool exceptions into JSON-RPC   |
+-----------------------------------+-----------------------------------+
                                    |
        +---------------------------+---------------------------+
        |                           |                           |
        v                           v                           v
+-------------------+       +-------------------+       +-------------------+
|  Sandboxed Files  |       |  Masked Env Info  |       |  Execution Guard  |
| - Path Traversal  |       | - Auto-masks keys |       | - Strict timeouts |
|   Confinement     |       |   and auth tokens |       | - Stdio isolation |
| - Read/Write/List |       | - Read-only       |       | - Safe arguments  |
+-------------------+       +-------------------+       +-------------------+

                                   ***
+-----------------------------------------------------------------------+
|                 MCP Protocol Verifier Engine (mcp-verify)             |
|   - Spawns target server subprocess over stdio                        |
|   - Verifies 'initialize' handshake and server capabilities           |
|   - Confirms 'tools/list' JSON Schema compliance                      |
|   - Detects non-JSON-RPC stdout pollution (the 'stdio trap')          |
|   - Measures latency and evaluates error code responses               |
+-----------------------------------------------------------------------+
```

## Security & Protocol Integrity Guardrails

1. **Stdout Channel Shielding:** In standard stdio MCP servers, any stray `print("loading...")` or library warning writes to stdout, corrupting the JSON-RPC framing and causing clients to crash. MCP-Bridge-Kit strictly routes all application logs, warnings, and error messages to `sys.stderr`, reserving `sys.stdout` exclusively for clean JSON-RPC 2.0 packets.
2. **Filesystem Chroot Sandboxing:** The file tools enforce path normalization via `Path.resolve()`. Any path attempting to escape the configured root (e.g. `../../etc/passwd` or `../../Windows`) is blocked with a security violation error before any I/O occurs.
3. **Automatic Secret Masking:** The environment tool filters out any key containing `KEY`, `SECRET`, `TOKEN`, `PASSWORD`, `AUTH`, or `CREDENTIAL`, showing only masked placeholders.
