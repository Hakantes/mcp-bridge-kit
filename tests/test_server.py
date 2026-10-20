import json
from pathlib import Path
from mcp_bridge.server import MCPServer


def test_server_initialize():
    server = MCPServer()
    req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    resp_str = server.handle_request(req)
    data = json.loads(resp_str)

    assert data["id"] == 1
    assert data["result"]["protocolVersion"] == "2024-11-05"
    assert data["result"]["serverInfo"]["name"] == "mcp-bridge-kit"


def test_server_tools_list():
    server = MCPServer()
    req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    resp_str = server.handle_request(req)
    data = json.loads(resp_str)

    assert data["id"] == 2
    tools = data["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "read_file" in tool_names
    assert "write_file" in tool_names
    assert "list_directory" in tool_names
    assert "get_env" in tool_names


def test_server_tools_call(tmp_path: Path):
    server = MCPServer(sandbox_root=tmp_path)
    (tmp_path / "hello.txt").write_text("World", encoding="utf-8")

    req = json.dumps({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "read_file",
            "arguments": {"path": "hello.txt"}
        }
    })
    resp_str = server.handle_request(req)
    data = json.loads(resp_str)

    assert data["id"] == 3
    assert data["result"]["content"][0]["text"] == "World"
    assert data["result"]["isError"] is False


def test_server_method_not_found():
    server = MCPServer()
    req = json.dumps({"jsonrpc": "2.0", "id": 4, "method": "non_existent_method"})
    resp_str = server.handle_request(req)
    data = json.loads(resp_str)

    assert data["id"] == 4
    assert data["error"]["code"] == -32601
