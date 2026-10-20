from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from mcp_bridge.server import MCPServer


@dataclass
class CheckResult:
    name: str
    passed: bool
    details: str
    latency_ms: float = 0.0


@dataclass
class VerificationReport:
    target: str
    passed: bool
    checks: List[CheckResult] = field(default_factory=list)
    stdout_pollution_detected: bool = False
    pollution_lines: List[str] = field(default_factory=list)
    total_latency_ms: float = 0.0


class MCPVerifier:
    def __init__(self, command: Optional[str] = None, in_process_server: Optional[MCPServer] = None):
        self.command = command
        self.in_process_server = in_process_server
        self._proc: Optional[subprocess.Popen] = None

    def _send_and_receive(self, request_payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], float, List[str]]:
        req_line = json.dumps(request_payload) + "\n"
        start = time.perf_counter()
        expect_response = request_payload.get("id") is not None

        if self.in_process_server:
            resp_str = self.in_process_server.handle_request(req_line)
            latency = (time.perf_counter() - start) * 1000
            if not resp_str:
                return None, latency, []
            return json.loads(resp_str), latency, []

        elif self._proc:
            self._proc.stdin.write(req_line)
            self._proc.stdin.flush()

            if not expect_response:
                # Notifications do not generate a JSON-RPC response
                latency = (time.perf_counter() - start) * 1000
                return None, latency, []

            pollution = []
            while True:
                line = self._proc.stdout.readline()
                if not line:
                    break
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    parsed = json.loads(stripped)
                    latency = (time.perf_counter() - start) * 1000
                    return parsed, latency, pollution
                except json.JSONDecodeError:
                    # Non-JSON-RPC output on stdout = STDOUT POLLUTION
                    pollution.append(stripped)

            latency = (time.perf_counter() - start) * 1000
            return None, latency, pollution

        return None, 0.0, []

    def verify(self) -> VerificationReport:
        checks: List[CheckResult] = []
        all_pollution: List[str] = []
        target_name = self.command or "In-Process MCPServer"

        if self.command:
            try:
                self._proc = subprocess.Popen(
                    self.command,
                    shell=True,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8"
                )
            except Exception as exc:
                return VerificationReport(
                    target=target_name,
                    passed=False,
                    checks=[CheckResult(name="Process Launch", passed=False, details=str(exc))]
                )

        try:
            # 1. Initialize Handshake
            init_req = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "mcp-verifier", "version": "0.1.0"}
                }
            }
            resp, lat, pol = self._send_and_receive(init_req)
            all_pollution.extend(pol)

            if resp and "result" in resp and "protocolVersion" in resp["result"]:
                checks.append(
                    CheckResult(
                        name="Protocol Handshake (initialize)",
                        passed=True,
                        details=f"Version: {resp['result']['protocolVersion']}, Server: {resp['result'].get('serverInfo', {}).get('name')}",
                        latency_ms=round(lat, 2)
                    )
                )
            else:
                checks.append(
                    CheckResult(
                        name="Protocol Handshake (initialize)",
                        passed=False,
                        details=f"Invalid initialize response: {resp}",
                        latency_ms=round(lat, 2)
                    )
                )

            # 2. Initialized Notification
            notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
            _, lat, pol = self._send_and_receive(notif)
            all_pollution.extend(pol)
            checks.append(
                CheckResult(
                    name="Notification Handshake (notifications/initialized)",
                    passed=True,
                    details="Notification acknowledged cleanly",
                    latency_ms=round(lat, 2)
                )
            )

            # 3. Tools Discovery (tools/list)
            tools_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
            resp, lat, pol = self._send_and_receive(tools_req)
            all_pollution.extend(pol)

            tools = []
            if resp and "result" in resp and "tools" in resp["result"]:
                tools = resp["result"]["tools"]
                checks.append(
                    CheckResult(
                        name="Tool Discovery (tools/list)",
                        passed=True,
                        details=f"Discovered {len(tools)} registered tools",
                        latency_ms=round(lat, 2)
                    )
                )
            else:
                checks.append(
                    CheckResult(
                        name="Tool Discovery (tools/list)",
                        passed=False,
                        details=f"Failed to list tools: {resp}",
                        latency_ms=round(lat, 2)
                    )
                )

            # 4. Tool Call Execution
            if tools:
                first_tool = tools[0]
                tool_name = first_tool["name"]
                # Provide empty arguments or sample path for known tools
                sample_args = {"path": "."} if "path" in first_tool.get("inputSchema", {}).get("properties", {}) else {}
                call_req = {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": sample_args}
                }
                resp, lat, pol = self._send_and_receive(call_req)
                all_pollution.extend(pol)

                if resp and "result" in resp and "content" in resp["result"]:
                    checks.append(
                        CheckResult(
                            name=f"Tool Execution ({tool_name})",
                            passed=True,
                            details="Valid CallToolResult structure returned",
                            latency_ms=round(lat, 2)
                        )
                    )
                else:
                    checks.append(
                        CheckResult(
                            name=f"Tool Execution ({tool_name})",
                            passed=False,
                            details=f"Tool call failed: {resp}",
                            latency_ms=round(lat, 2)
                        )
                    )

            # 5. Method Not Found Error Code (-32601)
            err_req = {"jsonrpc": "2.0", "id": 4, "method": "unknown_test_method"}
            resp, lat, pol = self._send_and_receive(err_req)
            all_pollution.extend(pol)

            if resp and "error" in resp and resp["error"].get("code") == -32601:
                checks.append(
                    CheckResult(
                        name="Error Code Conformance (-32601 METHOD_NOT_FOUND)",
                        passed=True,
                        details="Standard JSON-RPC 2.0 error code returned",
                        latency_ms=round(lat, 2)
                    )
                )
            else:
                checks.append(
                    CheckResult(
                        name="Error Code Conformance (-32601 METHOD_NOT_FOUND)",
                        passed=False,
                        details=f"Expected error code -32601, got: {resp}",
                        latency_ms=round(lat, 2)
                    )
                )

            # 6. Stdout Cleanliness Check
            if all_pollution:
                checks.append(
                    CheckResult(
                        name="Stdout Channel Cleanliness (No Pollution)",
                        passed=False,
                        details=f"Detected {len(all_pollution)} non-JSON-RPC lines on stdout!"
                    )
                )
            else:
                checks.append(
                    CheckResult(
                        name="Stdout Channel Cleanliness (No Pollution)",
                        passed=True,
                        details="100% clean JSON-RPC stdout stream"
                    )
                )

        finally:
            if self._proc:
                try:
                    self._proc.terminate()
                    self._proc.wait(timeout=2)
                except Exception:
                    self._proc.kill()

        all_passed = all(c.passed for c in checks)
        total_lat = sum(c.latency_ms for c in checks)

        return VerificationReport(
            target=target_name,
            passed=all_passed,
            checks=checks,
            stdout_pollution_detected=bool(all_pollution),
            pollution_lines=all_pollution,
            total_latency_ms=round(total_lat, 2)
        )
