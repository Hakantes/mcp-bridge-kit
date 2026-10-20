# Security Policy

MCP-Bridge-Kit provides hardened execution environments for AI agents.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting Security Vulnerabilities

Please report security concerns to `163651512+Hakantes@users.noreply.github.com`.

## Sandboxing Guarantees

- **Path Escape Prevention:** File tools strictly verify that all target canonical paths are relative to or inside `MCP_SANDBOX_ROOT`.
- **Environment Scrubbing:** Environmental credentials matching common API key naming patterns are redacted in tool outputs.
- **Subprocess Safety:** Command tools execute with strict timeouts and without shell variable expansion.
