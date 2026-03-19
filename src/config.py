"""Configuration loader for Frontend Mimic."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator


class TargetConfig(BaseModel):
    url: str
    dashboard_url: str = ""

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"URL must start with http:// or https://, got: {v}")
        return v


class LoginConfig(BaseModel):
    username: str = ""
    password: str = ""
    username_selector: str = "input[type='text'], input[name='username'], input[name='email']"
    password_selector: str = "input[type='password']"
    submit_selector: str = (
        "button[type='submit'], button:has-text('Login'), button:has-text('Sign in'), "
        "button:has-text('登录'), button:has-text('Log in')"
    )
    success_indicator: str = ""  # Optional selector that appears after successful login


class CrawlConfig(BaseModel):
    max_depth: int = 2
    max_pages: int = 50
    wait_after_navigation: int = 3000
    wait_for_spa: int = 2000  # Extra wait for SPA rendering after navigation
    exclude_patterns: list[str] = Field(default_factory=lambda: ["/logout", "/api/", ".pdf", ".zip"])
    interaction_timeout: int = 10000  # Timeout for interaction clicks (ms)
    max_interaction_items: int = 5  # Max dropdown items to click per action button
    retry_failed: int = 1  # Number of retries for failed pages


class InteractionConfig(BaseModel):
    """Configurable selectors for deep interaction — adapt for different UI frameworks."""
    # Action/operation button selectors (try these in order)
    action_button_selectors: list[str] = Field(default_factory=lambda: [
        "button:has-text('操作')",
        "button:has-text('Actions')",
        "button:has-text('Action')",
        ".el-dropdown:has-text('操作') button",
        ".ant-dropdown-trigger",
        ".dropdown-toggle",
    ])
    # Add/create button selectors
    add_button_selectors: list[str] = Field(default_factory=lambda: [
        "button:has-text('添加')",
        "button:has-text('新增')",
        "button:has-text('Add')",
        "button:has-text('Create')",
        "button:has-text('New')",
    ])
    # Dropdown menu item selector
    dropdown_item_selector: str = (
        ".el-dropdown-menu__item:visible, .ant-dropdown-menu-item:visible, "
        ".dropdown-item:visible, [role='menuitem']:visible"
    )
    # Modal/dialog selectors
    modal_selectors: list[str] = Field(default_factory=lambda: [
        ".el-dialog:visible",
        ".el-drawer:visible",
        ".ant-modal-wrap:visible",
        ".modal.show",
        "[role='dialog']:visible",
    ])
    # Modal close selectors
    modal_close_selectors: list[str] = Field(default_factory=lambda: [
        ".el-dialog__headerbtn",
        ".el-drawer__close-btn",
        ".ant-modal-close",
        ".modal .btn-close",
        "[aria-label='Close']",
        ".el-icon--close",
    ])
    # Overlay background selector
    overlay_selector: str = ".el-overlay, .ant-modal-mask, .modal-backdrop"
    # Expand row selectors
    expand_selectors: list[str] = Field(default_factory=lambda: [
        ".el-table__expand-icon",
        ".ant-table-row-expand-icon",
        "td.expand-icon",
    ])
    # Tab selectors
    tab_selector: str = (
        ".el-tabs__item:not(.is-active), .ant-tabs-tab:not(.ant-tabs-tab-active), "
        ".nav-link:not(.active)"
    )
    # Destructive action keywords to skip
    destructive_keywords: list[str] = Field(default_factory=lambda: [
        "删除", "delete", "remove", "drop", "destroy", "清空", "reset",
    ])


class BrowserConfig(BaseModel):
    headless: bool = False
    viewport_width: int = 1920
    viewport_height: int = 1080
    slow_mo: int = 500


class AIConfig(BaseModel):
    provider: Literal["claude", "openai", "both"] = "claude"
    claude_model: str = "claude-sonnet-4-20250514"
    openai_model: str = "gpt-4.1"
    max_tokens: int = 4096


class OutputConfig(BaseModel):
    screenshots_dir: str = "output/screenshots"
    dom_snapshots_dir: str = "output/dom_snapshots"
    reports_dir: str = "output/reports"
    vue_project_dir: str = "output/vue_project"


class AppConfig(BaseModel):
    target: TargetConfig
    login: LoginConfig = Field(default_factory=LoginConfig)
    crawl: CrawlConfig = Field(default_factory=CrawlConfig)
    interaction: InteractionConfig = Field(default_factory=InteractionConfig)
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)


def load_config(config_path: str | Path | None = None) -> AppConfig:
    """Load configuration from YAML file.

    Priority: settings.local.yaml > settings.yaml > defaults
    Environment variables override: MIMIC_USERNAME, MIMIC_PASSWORD, ANTHROPIC_API_KEY, OPENAI_API_KEY
    """
    project_root = Path(__file__).parent.parent
    config_dir = project_root / "config"

    if config_path:
        path = Path(config_path)
    elif (config_dir / "settings.local.yaml").exists():
        path = config_dir / "settings.local.yaml"
    else:
        path = config_dir / "settings.yaml"

    try:
        with open(path, encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise SystemExit(f"Invalid YAML in {path}: {e}") from e
    except FileNotFoundError:
        raise SystemExit(f"Config file not found: {path}") from None

    config = AppConfig(**data)

    # Environment variable overrides
    if env_user := os.environ.get("MIMIC_USERNAME"):
        config.login.username = env_user
    if env_pass := os.environ.get("MIMIC_PASSWORD"):
        config.login.password = env_pass

    # Create output directories
    for dir_path in [
        config.output.screenshots_dir,
        config.output.dom_snapshots_dir,
        config.output.reports_dir,
        config.output.vue_project_dir,
    ]:
        try:
            (project_root / dir_path).mkdir(parents=True, exist_ok=True)
        except PermissionError:
            raise SystemExit(f"Permission denied creating directory: {project_root / dir_path}") from None

    return config
