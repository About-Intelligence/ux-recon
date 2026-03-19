"""CLI entry point for Frontend Mimic."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from src.config import AppConfig, load_config
from src.browser.controller import BrowserController
from src.analyzer.page_analyzer import PageAnalyzer
from src.ai.client import AIClient
from src.generator.vue_generator import VueGenerator

console = Console()


async def run_pipeline(config: AppConfig, skip_crawl: bool, skip_ai: bool, skip_generate: bool) -> None:
    """Run the full analysis and generation pipeline."""
    project_root = Path(__file__).parent.parent

    console.print(Panel.fit(
        f"[bold cyan]Frontend Mimic[/bold cyan]\n"
        f"Target: {config.target.url}\n"
        f"Crawl depth: {config.crawl.max_depth} | Max pages: {config.crawl.max_pages}\n"
        f"AI provider: {config.ai.provider}\n"
        f"Output: {config.output.vue_project_dir}",
        title="Configuration",
    ))

    # Phase 1: Crawl
    crawl_result = None
    crawl_data_path = project_root / config.output.reports_dir / "crawl_data.json"

    if not skip_crawl:
        console.print("\n[bold]Phase 1: Browser Crawl[/bold]")
        browser = BrowserController(config)
        try:
            await browser.start()

            if not await browser.login():
                console.print("[red]Login failed. Check credentials in config.[/red]")
                await browser.stop()
                return

            crawl_result = await browser.crawl()

            # Save crawl data
            def serialize_snapshots(snapshots):
                return [
                    {
                        "url": p.url, "title": p.title,
                        "screenshot_path": p.screenshot_path,
                        "html_length": len(p.html), "styles_count": len(p.styles),
                        "computed_styles": p.computed_styles,
                        "links": p.links, "meta": p.meta,
                        "context": p.context,
                    }
                    for p in snapshots
                ]

            crawl_serializable = {
                "pages": serialize_snapshots(crawl_result.pages),
                "interaction_captures": serialize_snapshots(crawl_result.interaction_captures),
                "visited_urls": list(crawl_result.visited_urls),
                "failed_urls": crawl_result.failed_urls,
            }
            crawl_data_path.write_text(json.dumps(crawl_serializable, indent=2, ensure_ascii=False), encoding="utf-8")
            console.print(f"[green]Crawl data saved to {crawl_data_path}[/green]")

        finally:
            await browser.stop()
    else:
        console.print("[yellow]Skipping crawl — loading existing data...[/yellow]")
        if crawl_data_path.exists():
            console.print(f"[green]Loaded crawl data from {crawl_data_path}[/green]")
        else:
            console.print("[red]No crawl data found. Run without --skip-crawl first.[/red]")
            return

    if crawl_result is None:
        console.print("[red]No crawl data available. Exiting.[/red]")
        return

    # Phase 2: Analyze
    console.print("\n[bold]Phase 2: Frontend Analysis[/bold]")
    analyzer = PageAnalyzer()
    analysis = analyzer.analyze(crawl_result)

    analysis_path = project_root / config.output.reports_dir / "analysis.json"
    analysis_path.write_text(json.dumps(analysis.to_dict(), indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    console.print(f"[green]Analysis saved to {analysis_path}[/green]")

    # Phase 3: AI Summary
    summary = ""
    summary_path = project_root / config.output.reports_dir / "frontend_summary.md"
    if not skip_ai:
        console.print("\n[bold]Phase 3: AI Analysis[/bold]")
        ai_client = AIClient(config)

        screenshot_analyses = []
        for page in crawl_result.pages:
            console.print(f"  Analyzing screenshot: {page.title}")
            result = await ai_client.analyze_screenshot(
                page.screenshot_path,
                context=f"Page: {page.title} ({page.url})"
            )
            screenshot_analyses.append(result)

        console.print("  Generating comprehensive summary...")
        summary = await ai_client.generate_summary(analysis, screenshot_analyses)
        summary_path.write_text(summary, encoding="utf-8")
        console.print(f"[green]Summary saved to {summary_path}[/green]")
    else:
        if summary_path.exists():
            summary = summary_path.read_text(encoding="utf-8")
            console.print("[yellow]Loaded existing summary[/yellow]")

    # Phase 4: Generate Vue project
    if not skip_generate:
        console.print("\n[bold]Phase 4: Vue Project Generation[/bold]")
        ai_client = AIClient(config) if skip_ai else ai_client  # noqa: F841
        generator = VueGenerator(config, ai_client)
        output_path = await generator.generate(analysis, summary)
        console.print(f"\n[bold green]Done! Vue project at: {output_path}[/bold green]")
        console.print(f"[cyan]To run: cd {config.output.vue_project_dir} && npm install && npm run dev[/cyan]")
    else:
        console.print("[yellow]Skipping Vue generation[/yellow]")

    console.print(Panel.fit("[bold green]Pipeline complete![/bold green]"))


@click.command()
@click.option("--config", "-c", default=None, help="Path to config YAML file")
@click.option("--depth", "-d", type=int, default=None, help="Override crawl depth")
@click.option("--max-pages", "-m", type=int, default=None, help="Override max pages")
@click.option("--skip-crawl", is_flag=True, help="Skip crawl, use existing data")
@click.option("--skip-ai", is_flag=True, help="Skip AI analysis")
@click.option("--skip-generate", is_flag=True, help="Skip Vue generation")
@click.option("--headless", is_flag=True, help="Run browser in headless mode")
def main(config: str | None, depth: int | None, max_pages: int | None,
         skip_crawl: bool, skip_ai: bool, skip_generate: bool, headless: bool) -> None:
    """Frontend Mimic — AI-powered website frontend analyzer and replicator."""
    try:
        cfg = load_config(config)
        if depth is not None:
            cfg.crawl.max_depth = depth
        if max_pages is not None:
            cfg.crawl.max_pages = max_pages
        if headless:
            cfg.browser.headless = True

        asyncio.run(run_pipeline(cfg, skip_crawl, skip_ai, skip_generate))
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
