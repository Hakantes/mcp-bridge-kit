import subprocess
import sys


def test_cli_help():
    res = subprocess.run([sys.executable, "-m", "mcp_bridge.cli", "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "MCP-Bridge-Kit" in res.stdout or "mcp-bridge" in res.stdout


def test_cli_verify_help():
    res = subprocess.run([sys.executable, "-m", "mcp_bridge.cli", "verify", "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "--command" in res.stdout
