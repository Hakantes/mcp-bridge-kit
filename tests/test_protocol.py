from mcp_bridge.protocol import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    InitializeResult,
    ServerInfo,
    ToolDefinition,
    ToolInputSchema,
    CallToolResult,
    ContentItem
)


def test_jsonrpc_request_serialization():
    req = JSONRPCRequest(id=1, method="initialize", params={"version": "1.0"})
    dumped = req.model_dump()
    assert dumped["jsonrpc"] == "2.0"
    assert dumped["id"] == 1
    assert dumped["method"] == "initialize"


def test_jsonrpc_response_success():
    resp = JSONRPCResponse(id=1, result={"status": "ok"})
    dumped = resp.model_dump()
    assert dumped["jsonrpc"] == "2.0"
    assert dumped["result"]["status"] == "ok"
    assert dumped["error"] is None


def test_jsonrpc_response_error():
    err = JSONRPCError(code=-32601, message="Method not found")
    resp = JSONRPCResponse(id=2, error=err)
    dumped = resp.model_dump()
    assert dumped["error"]["code"] == -32601


def test_call_tool_result_structure():
    res = CallToolResult(content=[ContentItem(text="sample text")], isError=False)
    dumped = res.model_dump()
    assert len(dumped["content"]) == 1
    assert dumped["content"][0]["text"] == "sample text"
    assert dumped["isError"] is False
