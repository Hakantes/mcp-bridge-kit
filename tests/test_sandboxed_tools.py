import os
from pathlib import Path
from mcp_bridge.tools import ToolRegistry


def test_sandboxed_file_read_write(tmp_path: Path):
    registry = ToolRegistry(sandbox_root=tmp_path)

    # Write file inside sandbox
    write_res = registry.call_tool("write_file", {"path": "sub/test.txt", "content": "Hello Sandbox!"})
    assert write_res.isError is False
    assert (tmp_path / "sub" / "test.txt").exists()

    # Read file back
    read_res = registry.call_tool("read_file", {"path": "sub/test.txt"})
    assert read_res.isError is False
    assert read_res.content[0].text == "Hello Sandbox!"


def test_path_traversal_blocked(tmp_path: Path):
    registry = ToolRegistry(sandbox_root=tmp_path)

    # Attempt to escape sandbox via ../../
    escape_res = registry.call_tool("read_file", {"path": "../../secret.txt"})
    assert escape_res.isError is True
    assert "Security Violation" in escape_res.content[0].text


def test_list_directory(tmp_path: Path):
    registry = ToolRegistry(sandbox_root=tmp_path)
    (tmp_path / "file1.txt").write_text("a", encoding="utf-8")
    (tmp_path / "dir1").mkdir()

    list_res = registry.call_tool("list_directory", {"path": "."})
    assert list_res.isError is False
    text = list_res.content[0].text
    assert "[FILE] file1.txt" in text
    assert "[DIR]  dir1" in text


def test_get_env_masks_secrets(monkeypatch):
    monkeypatch.setenv("APP_PORT", "8080")
    monkeypatch.setenv("DATABASE_PASSWORD", "super_secret_12345")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-test12345")

    registry = ToolRegistry()
    res = registry.call_tool("get_env", {})
    assert res.isError is False
    text = res.content[0].text

    assert "APP_PORT=8080" in text
    assert "DATABASE_PASSWORD=******** [REDACTED SENSITIVE KEY]" in text
    assert "OPENAI_API_KEY=******** [REDACTED SENSITIVE KEY]" in text
