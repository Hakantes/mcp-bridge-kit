# Changelog

All notable changes to MCP-Bridge-Kit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-21

### Added
- JSON-RPC 2.0 protocol engine implementing Model Context Protocol (MCP) spec (2024-11-05 revision).
- Handshake handlers for `initialize`, `notifications/initialized`, and `ping`.
- Safe sandboxed file operations (`read_file`, `write_file`, `list_directory`) with chroot containment.
- Masked environmental inspector tool (`get_env`).
- Read-only Git status tool (`git_status`).
- Safe process runner with timeout and separated error pipes (`run_command`).
- Output shielding: routing all server logs to `sys.stderr` to prevent stdio pipe crashes.
- Standalone protocol verifier CLI (`mcp-verify`) testing external servers for JSON-RPC compliance, stdout pollution, and latency.
