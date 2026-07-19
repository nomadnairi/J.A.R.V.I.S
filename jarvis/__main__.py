"""
Command-line entry point for J.A.R.V.I.S. (async, streaming).

Run an interactive chat session with the assistant:

    python -m jarvis

Special commands inside the session:
    /reset    clear the conversation history
    /skills   list locally-handled skills and tools
    /stats    show telemetry for this session
    /state    show the current assistant state
    /help     show available commands
    /quit     exit (also: /exit, Ctrl-D)
"""

from __future__ import annotations

import asyncio
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from jarvis import __version__
from jarvis.config.settings import get_settings
from jarvis.core.engine import JarvisEngine
from jarvis.models.response import Request
from jarvis.utils.exceptions import JarvisError
from jarvis.utils.logger import setup_logging

console = Console()
SESSION_ID = "cli"


def _banner(assistant_name: str) -> None:
    console.print(
        Panel.fit(
            f"[bold cyan]{assistant_name}[/bold cyan]\n"
            f"[dim]Just A Rather Very Intelligent System — v{__version__}[/dim]\n\n"
            "Type your message and press Enter.\n"
            "[dim]/help for commands · /quit to exit[/dim]",
            border_style="cyan",
        )
    )


def _print_help() -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("[cyan]/reset[/cyan]", "clear conversation history (keeps memory)")
    table.add_row("[cyan]/forget[/cyan]", "wipe history and long-term memory")
    table.add_row("[cyan]/memory[/cyan]", "show memory statistics")
    table.add_row("[cyan]/skills[/cyan]", "list locally-handled skills and tools")
    table.add_row("[cyan]/integrations[/cyan]", "show integration statuses")
    table.add_row("[cyan]/goals[/cyan]", "show open goals")
    table.add_row("[cyan]/tools[/cyan]", "list tools by category")
    table.add_row("[cyan]/doctor[/cyan]", "run health diagnostics")
    table.add_row("[cyan]/stats[/cyan]", "show session telemetry")
    table.add_row("[cyan]/state[/cyan]", "show current assistant state")
    table.add_row("[cyan]/help[/cyan]", "show this help")
    table.add_row("[cyan]/quit[/cyan]", "exit the session")
    console.print("\n[bold]Commands[/bold]")
    console.print(table)


def _print_skills(engine: JarvisEngine) -> None:
    table = Table(title="Registered Skills")
    table.add_column("Skill", style="cyan")
    table.add_column("Priority", justify="right", style="magenta")
    table.add_column("Tool", justify="center")
    table.add_column("Description")
    for skill in sorted(engine.skills.all(), key=lambda s: s.priority, reverse=True):
        is_tool = "✓" if skill.parameters is not None else "—"
        table.add_row(skill.name, str(skill.priority), is_tool, skill.description)
    console.print(table)


def _print_integrations(engine: JarvisEngine) -> None:
    if engine.integrations is None:
        console.print("[yellow]Integrations are disabled.[/yellow]")
        return
    table = Table(title="Integrations")
    table.add_column("Integration", style="cyan")
    table.add_column("State")
    table.add_column("Detail")
    for status in engine.integrations.statuses():
        colour = {"connected": "green", "error": "red"}.get(status.state.value, "dim")
        table.add_row(status.name, f"[{colour}]{status.state.value}[/{colour}]",
                    status.detail)
    console.print(table)


def _print_doctor(engine: JarvisEngine) -> None:
    from jarvis.core.diagnostics import diagnose

    table = Table(title="Diagnostics")
    table.add_column("Check", style="cyan")
    table.add_column("", justify="center")
    table.add_column("Detail")
    for check in diagnose(engine):
        mark = "[green]✓[/green]" if check.ok else "[red]✗[/red]"
        table.add_row(check.name, mark, check.detail)
    console.print(table)


def _print_tools(engine: JarvisEngine) -> None:
    table = Table(title="Tools by Category")
    table.add_column("Category", style="cyan")
    table.add_column("Tools")
    for category, names in engine.tools.categories().items():
        table.add_row(category, ", ".join(names))
    console.print(table)


async def _print_goals(engine: JarvisEngine) -> None:
    if engine.goals is None:
        console.print("[yellow]Goals are disabled.[/yellow]")
        return
    goals = await engine.goals.active(SESSION_ID)
    if not goals:
        console.print("[dim]No open goals.[/dim]")
        return
    table = Table(title="Open Goals")
    table.add_column("#", justify="right", style="magenta")
    table.add_column("Goal")
    for goal in goals:
        table.add_row(str(goal.id), goal.text)
    console.print(table)


def _print_stats(engine: JarvisEngine) -> None:
    stats = engine.stats
    lat = stats["latency_ms"]
    table = Table(title="Session Telemetry", show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    table.add_row("Requests", str(stats["requests_total"]))
    table.add_row("Responses", str(stats["responses_total"]))
    table.add_row("Errors", str(stats["errors_total"]))
    table.add_row("Total tokens", str(stats["total_tokens"]))
    table.add_row("Avg latency", f"{lat['avg']} ms")
    table.add_row("Median latency", f"{lat['median']} ms")
    table.add_row("Skill usage", str(stats["skill_usage"] or "—"))
    table.add_row("Provider usage", str(stats["provider_usage"] or "—"))
    console.print(table)


async def _handle_command(cmd: str, engine: JarvisEngine) -> bool:
    """Handle a slash command. Returns True if the session should continue."""
    if cmd in ("/quit", "/exit"):
        console.print("[dim]Goodbye.[/dim]")
        return False
    if cmd == "/reset":
        await engine.reset(SESSION_ID)
        console.print("[dim]History cleared.[/dim]")
    elif cmd == "/forget":
        await engine.forget(SESSION_ID)
        console.print("[dim]History and long-term memory wiped.[/dim]")
    elif cmd == "/memory":
        if engine.memory is None:
            console.print("[yellow]Memory is disabled.[/yellow]")
        else:
            stats = engine.memory.stats()
            console.print(
                f"Memory: [cyan]{stats['memories']}[/cyan] memories · "
                f"[cyan]{stats['stored_messages']}[/cyan] messages · "
                f"[cyan]{stats['sessions']}[/cyan] sessions"
            )
    elif cmd == "/skills":
        _print_skills(engine)
    elif cmd == "/integrations":
        _print_integrations(engine)
    elif cmd == "/goals":
        await _print_goals(engine)
    elif cmd == "/tools":
        _print_tools(engine)
    elif cmd == "/doctor":
        _print_doctor(engine)
    elif cmd == "/stats":
        _print_stats(engine)
    elif cmd == "/state":
        console.print(f"State: [cyan]{engine.state.state.value}[/cyan]")
    elif cmd == "/help":
        _print_help()
    else:
        console.print(f"[yellow]Unknown command:[/yellow] {cmd}  (try /help)")
    return True


async def _stream_reply(engine: JarvisEngine, text: str, assistant_name: str) -> None:
    """Stream a reply, printing chunks as they arrive."""
    console.print(f"[bold cyan]{assistant_name}[/bold cyan] › ", end="")
    got_any = False
    try:
        async for chunk in engine.stream(Request(text=text, session_id=SESSION_ID)):
            got_any = True
            console.print(chunk, end="", markup=False, highlight=False)
    except JarvisError as exc:
        if not got_any:
            console.print(f"[red]Error:[/red] {exc}")
            return
    console.print()  # newline after the streamed reply


async def _run() -> int:
    settings = get_settings()
    setup_logging(level=settings.log_level, log_file=settings.log_file)

    _banner(settings.assistant_name)

    engine = JarvisEngine(settings)
    await engine.start()

    if not engine.llm.has_any_provider():
        console.print(
            f"\n[yellow]⚠  No API key found for provider "
            f"'{settings.llm_provider}'.[/yellow]\n"
            "Copy [cyan].env.example[/cyan] to [cyan].env[/cyan] and add your "
            "key. Skills and tools that don't need the LLM (try "
            "[cyan]/skills[/cyan]) still work.\n"
        )

    try:
        while True:
            try:
                user_input = await asyncio.to_thread(
                    console.input,
                    f"\n[bold green]{settings.user_name}[/bold green] › ",
                )
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Goodbye.[/dim]")
                break

            text = user_input.strip()
            if not text:
                continue

            if text.startswith("/"):
                if not await _handle_command(text, engine):
                    break
                continue

            await _stream_reply(engine, text, settings.assistant_name)
    finally:
        await engine.shutdown()

    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except KeyboardInterrupt:  # pragma: no cover
        return 0


if __name__ == "__main__":
    sys.exit(main())
