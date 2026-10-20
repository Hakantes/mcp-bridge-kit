# Contributing to MCP-Bridge-Kit

We welcome contributions to MCP-Bridge-Kit!

## Local Development Setup

1. Clone repo:
   ```bash
   git clone https://github.com/Hakantes/mcp-bridge-kit.git
   cd mcp-bridge-kit
   ```
2. Virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   ```
3. Run test suite:
   ```bash
   pytest -v
   ```

## Development Rule: Stdio Cleanliness

- **NEVER** use `print()` in server code; all diagnostic output must go through `sys.stderr.write()` or standard logging configured to `sys.stderr`.
- `sys.stdout` is exclusively reserved for JSON-RPC 2.0 messages.
