from __future__ import annotations

import argparse
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from mcp_bridge import __version__
from mcp_bridge.server import MCPServer
from mcp_bridge.verifier import MCPVerifier

console = Console()


def render_verification_report(report) -> None:
    status_style = "bold green" if report.passed else "bold red"
    status_text = "PASSED (100% COMPLIANT)" if report.passed else "FAILED (NON-COMPLIANT)"

    console.print()
    console.print(
        Panel(
            f"Target: [cyan]{report.target}[/cyan]\n"
            f"Result: [{status_style}]{status_text}[/{status_style}] | "
            f"Total Checks: {len(report.checks)} | "
            f"Latency: {report.total_latency_ms:.1f}ms\n"
            f"Stdout Cleanliness: {'[red]POLLUTION DETECTED[/red]' if report.stdout_pollution_detected else '[green]CLEAN[/green]'}",
            title="Model Context Protocol (MCP) Conformance Suite",
            border_style="green" if report.passed else "red"
        )
    )

    table = Table(title="Conformance Verification Breakdown", header_style="bold magenta")
    table.add_column("Protocol Check", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Latency", justify="right")
    table.add_column("Details", style="dim")

    for chk in report.checks:
        stat = "[green]✓ PASS[/green]" if chk.passed else "[red]✗ FAIL[/red]"
        lat = f"{chk.latency_ms:.1f}ms" if chk.latency_ms > 0 else "-"
        table.add_row(chk.name, stat, lat, chk.details)

    console.print(table)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mcp-bridge",
        description="Hardened Model Context Protocol (MCP) server & developer toolkit."
    )
    parser.add_argument("--version", "-v", action="version", version=f"MCP-Bridge-Kit {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    # serve subcommand
    serve_p = subparsers.add_parser("serve", help="Run the hardened MCP stdio server")
    serve_p.add_argument("--sandbox", "-s", type=str, default=".", help="Root directory boundary for sandbox")

    # verify subcommand
    verify_p = subparsers.add_parser("verify", help="Verify protocol conformance of an MCP server")
    verify_p.add_argument("--command", "-c", type=str, required=True, help="Subprocess command to launch target MCP server")

    args = parser.parse_args()

    if not args.command:
        # Default to serve
        server = MCPServer()
        server.run_stdio()
        return

    if args.command == "serve":
        sandbox_path = Path(args.sandbox).resolve()
        server = MCPServer(sandbox_root=sandbox_path)
        server.run_stdio()

    elif args.command == "verify":
        verifier = MCPVerifier(command=args.command)
        report = verifier.verify()
        render_verification_report(report)
        sys.exit(0 if report.passed else 1)


def verify_cli() -> None:
    parser = argparse.ArgumentParser(
        prog="mcp-verify",
        description="Automated JSON-RPC 2.0 conformance and compliance verifier for Model Context Protocol servers."
    )
    parser.add_argument("--command", "-c", type=str, required=True, help="Target MCP server launch command (e.g. 'python -m my_mcp')")
    args = parser.parse_args()

    verifier = MCPVerifier(command=args.command)
    report = verifier.verify()
    render_verification_report(report)
    sys.exit(0 if report.passed else 1)


if __name__ == "__main__":
    main()
