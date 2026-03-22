"""Authenticator — handles website login flow."""

from __future__ import annotations

import asyncio

from playwright.async_api import TimeoutError as PwTimeout
from rich.console import Console

from src.config import AppConfig
from src.browser.controller import BrowserController

console = Console()


class Authenticator:
    """Handles login using configured selectors and credentials."""

    def __init__(self, config: AppConfig, controller: BrowserController):
        self.config = config
        self.controller = controller

    async def login(self) -> bool:
        """Log into the target website. Returns True on success."""
        cfg = self.config.login
        page = self.controller.page

        if not cfg.username or not cfg.password:
            console.print("[red]No credentials configured[/red]")
            return False

        # Navigate to login page (with retry)
        reached = False
        for attempt in range(3):
            if await self.controller.goto(self.config.target.url, timeout=60000):
                reached = True
                break
            console.print(f"[yellow]Login page load attempt {attempt + 1} failed, retrying...[/yellow]")
            await asyncio.sleep(2)
        if not reached:
            console.print("[red]Failed to reach login page after 3 attempts[/red]")
            return False

        try:
            # Fill credentials
            username_input = page.locator(cfg.username_selector).first
            await username_input.wait_for(state="visible", timeout=10000)
            await username_input.fill(cfg.username)

            password_input = page.locator(cfg.password_selector).first
            await password_input.fill(cfg.password)

            # Submit
            submit_btn = page.locator(cfg.submit_selector).first
            await submit_btn.click()

            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(self.config.crawl.wait_for_spa / 1000)

            # Verify login
            current_url = page.url

            if cfg.success_indicator:
                try:
                    await page.locator(cfg.success_indicator).first.wait_for(
                        state="visible", timeout=5000
                    )
                    return True
                except PwTimeout:
                    console.print("[red]Login indicator not found[/red]")
                    return False

            if "login" not in current_url.lower() and "auth" not in current_url.lower():
                return True

            console.print("[red]Still on login page after submit[/red]")
            return False

        except Exception as e:
            console.print(f"[red]Login failed: {e}[/red]")
            return False

    async def check_session(self) -> bool:
        """Check if we're still logged in (not redirected to login)."""
        url = await self.controller.get_url()
        return "login" not in url.lower() and "auth" not in url.lower()

    async def re_login(self) -> bool:
        """Re-authenticate if session expired."""
        console.print("[yellow]Re-authenticating...[/yellow]")
        return await self.login()
