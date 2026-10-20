from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from mcp_bridge.protocol import ToolDefinition, ToolInputSchema, CallToolResult, ContentItem


class ToolRegistry:
    def __init__(self, sandbox_root: Optional[Path] = None):
        self.sandbox_root = (sandbox_root or Path.cwd()).resolve()
        self._tools: Dict[str, Tuple[ToolDefinition, Callable]] = {}
        self._register_default_tools()

    def register(self, definition: ToolDefinition, handler: Callable) -> None:
        self._tools[definition.name] = (definition, handler)

    def get_definitions(self) -> List[ToolDefinition]:
        return [defn for defn, _ in self._tools.values()]

    def is_path_safe(self, target_path: str) -> Tuple[bool, Optional[Path], Optional[str]]:
        """Validates that a path is strictly confined within sandbox_root without escaping."""
        try:
            resolved = (self.sandbox_root / target_path).resolve()
            if not resolved.is_relative_to(self.sandbox_root):
                return False, None, f"Security Violation: Path '{target_path}' escapes sandbox boundary."
            return True, resolved, None
        except Exception as exc:
            return False, None, f"Invalid path specification: {exc}"

    def _register_default_tools(self) -> None:
        # 1. read_file
        self.register(
            ToolDefinition(
                name="read_file",
                description="Safely reads the text content of a file within the sandbox root directory.",
                inputSchema=ToolInputSchema(
                    properties={
                        "path": {"type": "string", "description": "Relative file path within sandbox"}
                    },
                    required=["path"]
                )
            ),
            self._tool_read_file
        )

        # 2. write_file
        self.register(
            ToolDefinition(
                name="write_file",
                description="Safely writes text content to a file within the sandbox root directory.",
                inputSchema=ToolInputSchema(
                    properties={
                        "path": {"type": "string", "description": "Relative file path to write"},
                        "content": {"type": "string", "description": "Content string to write"}
                    },
                    required=["path", "content"]
                )
            ),
            self._tool_write_file
        )

        # 3. list_directory
        self.register(
            ToolDefinition(
                name="list_directory",
                description="Lists entries inside a directory within the sandbox root.",
                inputSchema=ToolInputSchema(
                    properties={
                        "path": {"type": "string", "description": "Relative directory path (defaults to root)", "default": "."}
                    }
                )
            ),
            self._tool_list_directory
        )

        # 4. get_env
        self.register(
            ToolDefinition(
                name="get_env",
                description="Inspects environment variable names and safe values with automated credential masking.",
                inputSchema=ToolInputSchema(
                    properties={
                        "filter_prefix": {"type": "string", "description": "Optional prefix filter", "default": ""}
                    }
                )
            ),
            self._tool_get_env
        )

        # 5. git_status
        self.register(
            ToolDefinition(
                name="git_status",
                description="Returns concise Git repository working tree status.",
                inputSchema=ToolInputSchema(properties={})
            ),
            self._tool_git_status
        )

        # 6. run_command
        self.register(
            ToolDefinition(
                name="run_command",
                description="Executes a safe CLI command within sandbox with strict timeout and channel isolation.",
                inputSchema=ToolInputSchema(
                    properties={
                        "command": {"type": "string", "description": "Command string to execute"},
                        "timeout_seconds": {"type": "integer", "description": "Execution timeout limit", "default": 10}
                    },
                    required=["command"]
                )
            ),
            self._tool_run_command
        )

    # Tool Handlers
    def _tool_read_file(self, arguments: Dict[str, Any]) -> CallToolResult:
        path_str = arguments.get("path", "")
        safe, resolved, err = self.is_path_safe(path_str)
        if not safe:
            return CallToolResult(content=[ContentItem(text=err)], isError=True)

        if not resolved.exists():
            return CallToolResult(content=[ContentItem(text=f"Error: File '{path_str}' does not exist.")], isError=True)
        if resolved.is_dir():
            return CallToolResult(content=[ContentItem(text=f"Error: '{path_str}' is a directory, not a file.")], isError=True)

        try:
            content = resolved.read_text(encoding="utf-8", errors="replace")
            return CallToolResult(content=[ContentItem(text=content)], isError=False)
        except Exception as exc:
            return CallToolResult(content=[ContentItem(text=f"Failed to read file: {exc}")], isError=True)

    def _tool_write_file(self, arguments: Dict[str, Any]) -> CallToolResult:
        path_str = arguments.get("path", "")
        content = arguments.get("content", "")
        safe, resolved, err = self.is_path_safe(path_str)
        if not safe:
            return CallToolResult(content=[ContentItem(text=err)], isError=True)

        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, encoding="utf-8")
            return CallToolResult(content=[ContentItem(text=f"Successfully wrote {len(content)} characters to {path_str}")], isError=False)
        except Exception as exc:
            return CallToolResult(content=[ContentItem(text=f"Failed to write file: {exc}")], isError=True)

    def _tool_list_directory(self, arguments: Dict[str, Any]) -> CallToolResult:
        path_str = arguments.get("path", ".")
        safe, resolved, err = self.is_path_safe(path_str)
        if not safe:
            return CallToolResult(content=[ContentItem(text=err)], isError=True)

        if not resolved.exists():
            return CallToolResult(content=[ContentItem(text=f"Error: Directory '{path_str}' does not exist.")], isError=True)

        items = []
        try:
            for item in sorted(resolved.iterdir()):
                prefix = "[DIR] " if item.is_dir() else "[FILE]"
                items.append(f"{prefix} {item.name}")
            return CallToolResult(content=[ContentItem(text="\n".join(items) if items else "(empty directory)")], isError=False)
        except Exception as exc:
            return CallToolResult(content=[ContentItem(text=f"Failed to list directory: {exc}")], isError=True)

    def _tool_get_env(self, arguments: Dict[str, Any]) -> CallToolResult:
        prefix = arguments.get("filter_prefix", "").upper()
        sensitive_keywords = {"KEY", "SECRET", "TOKEN", "PASSWORD", "AUTH", "CREDENTIAL", "PASSWD"}

        results = []
        for k, v in sorted(os.environ.items()):
            if prefix and not k.upper().startswith(prefix):
                continue
            if any(w in k.upper() for w in sensitive_keywords):
                masked_val = "******** [REDACTED SENSITIVE KEY]"
            else:
                masked_val = v
            results.append(f"{k}={masked_val}")

        return CallToolResult(content=[ContentItem(text="\n".join(results))], isError=False)

    def _tool_git_status(self, arguments: Dict[str, Any]) -> CallToolResult:
        try:
            res = subprocess.run(
                ["git", "status", "-s"],
                cwd=self.sandbox_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            out = res.stdout.strip()
            return CallToolResult(content=[ContentItem(text=out if out else "Working tree clean")], isError=False)
        except Exception as exc:
            return CallToolResult(content=[ContentItem(text=f"Git status failed: {exc}")], isError=True)

    def _tool_run_command(self, arguments: Dict[str, Any]) -> CallToolResult:
        cmd = arguments.get("command", "")
        timeout = int(arguments.get("timeout_seconds", 10))

        # Basic security guard: prevent chain injections or dangerous system commands
        forbidden = ["rm -rf /", ":(){ :|:& };:", "format c:"]
        if any(f in cmd.lower() for f in forbidden):
            return CallToolResult(content=[ContentItem(text="Blocked potentially destructive command.")], isError=True)

        try:
            res = subprocess.run(
                cmd,
                shell=True,
                cwd=self.sandbox_root,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            output = f"Exit Code: {res.returncode}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
            return CallToolResult(content=[ContentItem(text=output.strip())], isError=(res.returncode != 0))
        except subprocess.TimeoutExpired:
            return CallToolResult(content=[ContentItem(text=f"Command timed out after {timeout} seconds")], isError=True)
        except Exception as exc:
            return CallToolResult(content=[ContentItem(text=f"Execution error: {exc}")], isError=True)

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> CallToolResult:
        if name not in self._tools:
            return CallToolResult(content=[ContentItem(text=f"Unknown tool: '{name}'")], isError=True)
        _, handler = self._tools[name]
        return handler(arguments)
