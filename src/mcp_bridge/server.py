from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from mcp_bridge.protocol import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    InitializeResult,
    ServerInfo,
    ServerCapabilities,
    PARSE_ERROR,
    METHOD_NOT_FOUND,
    INVALID_PARAMS,
    INTERNAL_ERROR
)
from mcp_bridge.tools import ToolRegistry


class MCPServer:
    def __init__(self, sandbox_root: Optional[Path] = None):
        self.registry = ToolRegistry(sandbox_root=sandbox_root)
        self.server_info = ServerInfo(name="mcp-bridge-kit", version="0.1.0")

    def handle_request(self, raw_line: str) -> Optional[str]:
        """Processes a single line of JSON-RPC and returns formatted JSON-RPC response string."""
        raw_line = raw_line.strip()
        if not raw_line:
            return None

        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            err_resp = JSONRPCResponse(
                error=JSONRPCError(code=PARSE_ERROR, message=f"Parse error: {exc.msg}")
            )
            return err_resp.model_dump_json()

        req_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params", {}) or {}

        # Handle notifications (requests without an id)
        if req_id is None and method == "notifications/initialized":
            sys.stderr.write("[mcp-bridge] Received notifications/initialized\n")
            sys.stderr.flush()
            return None

        # Route methods
        if method == "initialize":
            res = InitializeResult(
                protocolVersion="2024-11-05",
                capabilities=ServerCapabilities(),
                serverInfo=self.server_info
            )
            resp = JSONRPCResponse(id=req_id, result=res.model_dump())
            return resp.model_dump_json()

        elif method == "ping":
            resp = JSONRPCResponse(id=req_id, result={})
            return resp.model_dump_json()

        elif method == "tools/list":
            tools_list = [t.model_dump() for t in self.registry.get_definitions()]
            resp = JSONRPCResponse(id=req_id, result={"tools": tools_list})
            return resp.model_dump_json()

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {}) or {}
            if not tool_name:
                resp = JSONRPCResponse(
                    id=req_id,
                    error=JSONRPCError(code=INVALID_PARAMS, message="Missing required parameter: 'name'")
                )
                return resp.model_dump_json()

            try:
                call_res = self.registry.call_tool(tool_name, arguments)
                resp = JSONRPCResponse(id=req_id, result=call_res.model_dump())
                return resp.model_dump_json()
            except Exception as exc:
                resp = JSONRPCResponse(
                    id=req_id,
                    error=JSONRPCError(code=INTERNAL_ERROR, message=f"Tool invocation exception: {exc}")
                )
                return resp.model_dump_json()

        else:
            resp = JSONRPCResponse(
                id=req_id,
                error=JSONRPCError(code=METHOD_NOT_FOUND, message=f"Method not found: '{method}'")
            )
            return resp.model_dump_json()

    def run_stdio(self) -> None:
        """Runs the blocking stdio server loop, reading from stdin line by line and writing to stdout."""
        sys.stderr.write(f"[mcp-bridge] Server started (sandbox: {self.registry.sandbox_root})\n")
        sys.stderr.flush()

        while True:
            line = sys.stdin.readline()
            if not line:
                break
            response_json = self.handle_request(line)
            if response_json:
                sys.stdout.write(response_json + "\n")
                sys.stdout.flush()
