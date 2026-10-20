from mcp_bridge.server import MCPServer
from mcp_bridge.verifier import MCPVerifier


def test_in_process_verification():
    server = MCPServer()
    verifier = MCPVerifier(in_process_server=server)
    report = verifier.verify()

    assert report.passed is True
    assert report.stdout_pollution_detected is False
    assert len(report.checks) >= 5

    check_names = [c.name for c in report.checks]
    assert any("initialize" in name for name in check_names)
    assert any("tools/list" in name for name in check_names)
    assert any("Cleanliness" in name for name in check_names)
