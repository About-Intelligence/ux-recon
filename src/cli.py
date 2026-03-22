"""CLI entry point for Frontend Mimic Agent."""

from __future__ import annotations

import asyncio
import sys

import click
from rich.console import Console

from src.config import load_config
from src.agent.engine import ExplorationEngine

console = Console()


async def run_agent(config_path: str | None, max_states: int | None,
                    max_depth: int | None, headless: bool, clear: bool) -> None:
    """Run the exploration agent."""
    config = load_config(config_path)

    # CLI overrides
    if max_states is not None:
        config.budget.max_states = max_states
    if max_depth is not None:
        config.budget.max_depth = max_depth
    if headless:
        config.browser.headless = True

    engine = ExplorationEngine(config)

    if clear:
        engine.artifacts.clear_output()
        console.print("[green]Output cleared[/green]")

    await engine.run()


@click.command()
@click.option("--config", "-c", default=None, help="Path to config YAML file")
@click.option("--max-states", "-s", type=int, default=None, help="Override max states budget")
@click.option("--max-depth", "-d", type=int, default=None, help="Override max exploration depth")
@click.option("--headless", is_flag=True, help="Run browser in headless mode")
@click.option("--clear", is_flag=True, help="Clear output before running")
def main(config: str | None, max_states: int | None, max_depth: int | None,
         headless: bool, clear: bool) -> None:
    """Frontend Mimic Agent — autonomous website exploration and UI analysis."""
    try:
        asyncio.run(run_agent(config, max_states, max_depth, headless, clear))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)
    except SystemExit:
        raise
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
