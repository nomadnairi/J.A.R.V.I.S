"""
Command-line entry point for J.A.R.V.I.S.

Run an interactive chat session with the assistant:

    python -m jarvis

Special commands inside the session:
    /reset   clear the conversation history
    /help    show available commands
    /quit    exit (also: /exit, Ctrl-D)
"""

from __future__ import annotations

import sys

from rich.console import Console
from rich.panel import Panel

from jarvis import __version__
from jarvis.config.settings import get_settings
from jarvis.core.engine import JarvisEngine
from jarvis.core.llm import LLMError
from jarvis.utils.logger import setup_logging

console = Console()


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
    console.print(
        "\n[bold]Commands[/bold]\n"
        "  [cyan]/reset[/cyan]  clear conversation history\n"
        "  [cyan]/help[/cyan]   show this help\n"
        "  [cyan]/quit[/cyan]   exit the session\n"
    )


def main() -> int:
    settings = get_settings()
    setup_logging(level=settings.log_level, log_file=settings.log_file)

    _banner(settings.assistant_name)

    if not settings.has_llm_credentials():
        console.print(
            f"\n[yellow]⚠  No API key found for provider "
            f"'{settings.llm_provider}'.[/yellow]\n"
            "Copy [cyan].env.example[/cyan] to [cyan].env[/cyan] and add your "
            "key, then try again.\n"
        )
        return 1

    engine = JarvisEngine(settings)

    while True:
        try:
            user_input = console.input(f"\n[bold green]{settings.user_name}[/bold green] › ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            return 0

        text = user_input.strip()
        if not text:
            continue

        # Handle slash-commands.
        if text in ("/quit", "/exit"):
            console.print("[dim]Goodbye.[/dim]")
            return 0
        if text == "/reset":
            engine.reset()
            console.print("[dim]History cleared.[/dim]")
            continue
        if text == "/help":
            _print_help()
            continue

        # Normal turn.
        try:
            with console.status("[cyan]thinking…[/cyan]", spinner="dots"):
                reply = engine.ask(text)
        except LLMError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            continue

        console.print(
            f"[bold cyan]{settings.assistant_name}[/bold cyan] › {reply}"
        )


if __name__ == "__main__":
    sys.exit(main())
