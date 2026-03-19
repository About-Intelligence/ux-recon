"""Page analyzer — extracts structural information from captured page data."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from collections import Counter

from bs4 import BeautifulSoup, Tag
from rich.console import Console

from src.browser.controller import PageSnapshot, CrawlResult

console = Console()


@dataclass
class ComponentInfo:
    """Detected UI component."""
    type: str  # e.g., "button", "card", "modal", "form", "table", "sidebar"
    selector: str
    count: int
    sample_html: str
    classes: list[str] = field(default_factory=list)


@dataclass
class RouteInfo:
    """Discovered route/page."""
    path: str
    title: str
    has_sidebar: bool = False
    has_navbar: bool = False
    has_footer: bool = False
    component_types: list[str] = field(default_factory=list)


@dataclass
class DesignTokens:
    """Extracted design system tokens."""
    colors: dict[str, list[str]] = field(default_factory=dict)  # category -> [color values]
    fonts: list[str] = field(default_factory=list)
    font_sizes: list[str] = field(default_factory=list)
    spacing_values: list[str] = field(default_factory=list)
    border_radii: list[str] = field(default_factory=list)
    shadows: list[str] = field(default_factory=list)


@dataclass
class SiteAnalysis:
    """Complete analysis of the crawled site."""
    routes: list[RouteInfo] = field(default_factory=list)
    components: list[ComponentInfo] = field(default_factory=list)
    design_tokens: DesignTokens = field(default_factory=DesignTokens)
    tech_stack: dict[str, str] = field(default_factory=dict)
    layout_pattern: str = ""  # e.g., "sidebar + main", "top-nav + content"
    css_framework: str = ""
    all_classes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to serializable dict."""
        return {
            "routes": [vars(r) for r in self.routes],
            "components": [vars(c) for c in self.components],
            "design_tokens": vars(self.design_tokens),
            "tech_stack": self.tech_stack,
            "layout_pattern": self.layout_pattern,
            "css_framework": self.css_framework,
            "top_classes": self.all_classes[:100],
        }


class PageAnalyzer:
    """Analyzes captured pages to extract structural and design information."""

    def analyze(self, crawl_result: CrawlResult) -> SiteAnalysis:
        """Analyze all captured pages and produce a site analysis."""
        analysis = SiteAnalysis()

        all_classes_counter: Counter[str] = Counter()

        for snapshot in crawl_result.pages:
            soup = BeautifulSoup(snapshot.html, "lxml")

            # Analyze route
            route = self._analyze_route(snapshot, soup)
            analysis.routes.append(route)

            # Collect classes
            for tag in soup.find_all(attrs={"class": True}):
                for cls in tag.get("class", []):
                    all_classes_counter[cls] += 1

            # Detect components
            self._detect_components(soup, analysis)

            # Extract design tokens from computed styles
            self._extract_design_tokens(snapshot, analysis)

        # Also analyze interaction captures (modals, drawers, detail pages)
        for snapshot in crawl_result.interaction_captures:
            soup = BeautifulSoup(snapshot.html, "lxml")
            for tag in soup.find_all(attrs={"class": True}):
                for cls in tag.get("class", []):
                    all_classes_counter[cls] += 1
            self._detect_components(soup, analysis)
            self._extract_design_tokens(snapshot, analysis)

        # Detect tech stack from first page
        if crawl_result.pages:
            analysis.tech_stack = self._detect_tech_stack(crawl_result.pages[0])

        # Detect CSS framework from class names
        analysis.css_framework = self._detect_css_framework(all_classes_counter)

        # Determine layout pattern
        analysis.layout_pattern = self._detect_layout_pattern(analysis.routes)

        # Top classes
        analysis.all_classes = [cls for cls, _ in all_classes_counter.most_common(200)]

        console.print(f"[green]Analysis complete: {len(analysis.routes)} routes, "
                      f"{len(analysis.components)} component types[/green]")
        return analysis

    def _analyze_route(self, snapshot: PageSnapshot, soup: BeautifulSoup) -> RouteInfo:
        """Analyze a single page/route."""
        # Extract hash route path
        path = snapshot.url
        if "#" in path:
            path = "#" + path.split("#", 1)[1]

        return RouteInfo(
            path=path,
            title=snapshot.title,
            has_sidebar=bool(soup.select_one(".sidebar, .side-nav, .el-aside, .ant-layout-sider, [class*='sidebar']")),
            has_navbar=bool(soup.select_one("nav, .navbar, .nav-bar, .el-header, .ant-layout-header, header")),
            has_footer=bool(soup.select_one("footer, .footer, .el-footer")),
            component_types=self._get_component_types_in_page(soup),
        )

    def _get_component_types_in_page(self, soup: BeautifulSoup) -> list[str]:
        """Identify what types of components appear in a page."""
        types = []
        checks = {
            "table": "table, .el-table, .ant-table, [class*='table']",
            "form": "form, .el-form, .ant-form, [class*='form']",
            "card": ".card, .el-card, .ant-card, [class*='card']",
            "modal": ".modal, .el-dialog, .ant-modal, [class*='modal'], [class*='dialog']",
            "tabs": ".tabs, .el-tabs, .ant-tabs, [class*='tab']",
            "chart": "canvas, .chart, [class*='chart'], [class*='echarts']",
            "button": "button, .el-button, .ant-btn",
            "input": "input, .el-input, .ant-input, textarea, select",
            "dropdown": ".dropdown, .el-dropdown, .ant-dropdown, [class*='dropdown']",
            "pagination": ".pagination, .el-pagination, .ant-pagination, [class*='pagination']",
            "breadcrumb": ".breadcrumb, .el-breadcrumb, .ant-breadcrumb",
            "tree": ".tree, .el-tree, .ant-tree, [class*='tree']",
            "upload": "[class*='upload'], input[type='file']",
            "tag": ".tag, .el-tag, .ant-tag, .badge, [class*='tag']",
            "alert": ".alert, .el-alert, .ant-alert, [class*='alert']",
            "steps": ".steps, .el-steps, .ant-steps, [class*='step']",
        }
        for comp_type, selector in checks.items():
            if soup.select_one(selector):
                types.append(comp_type)
        return types

    def _detect_components(self, soup: BeautifulSoup, analysis: SiteAnalysis) -> None:
        """Detect and catalog UI components."""
        component_selectors = {
            "button": "button, .btn, .el-button, .ant-btn",
            "card": ".card, .el-card, .ant-card",
            "table": "table, .el-table, .ant-table",
            "form": "form, .el-form, .ant-form",
            "modal": ".modal, .el-dialog, .ant-modal",
            "input": ".el-input, .ant-input, input:not([type='hidden'])",
            "select": "select, .el-select, .ant-select",
            "sidebar": ".sidebar, .el-aside, .ant-layout-sider",
            "navbar": "nav, .navbar, .el-header",
            "dropdown": ".dropdown, .el-dropdown, .ant-dropdown",
            "tabs": ".el-tabs, .ant-tabs, .nav-tabs",
            "pagination": ".el-pagination, .ant-pagination, .pagination",
            "tag": ".el-tag, .ant-tag, .badge",
            "breadcrumb": ".el-breadcrumb, .ant-breadcrumb, .breadcrumb",
            "tooltip": ".el-tooltip, .ant-tooltip, [class*='tooltip']",
        }

        existing_types = {c.type for c in analysis.components}

        for comp_type, selector in component_selectors.items():
            elements = soup.select(selector)
            if not elements:
                continue

            if comp_type in existing_types:
                # Update count
                for c in analysis.components:
                    if c.type == comp_type:
                        c.count += len(elements)
                        break
            else:
                sample = elements[0]
                classes = sample.get("class", []) if isinstance(sample, Tag) else []
                analysis.components.append(ComponentInfo(
                    type=comp_type,
                    selector=selector,
                    count=len(elements),
                    sample_html=str(sample)[:500],
                    classes=list(classes),
                ))

    def _extract_design_tokens(self, snapshot: PageSnapshot, analysis: SiteAnalysis) -> None:
        """Extract design tokens from computed styles."""
        tokens = analysis.design_tokens

        for selector, styles in snapshot.computed_styles.items():
            # Colors
            for key in ["color", "backgroundColor"]:
                if val := styles.get(key):
                    if val not in ("rgba(0, 0, 0, 0)", "transparent"):
                        category = "text" if key == "color" else "background"
                        tokens.colors.setdefault(category, [])
                        if val not in tokens.colors[category]:
                            tokens.colors[category].append(val)

            # Fonts
            if font := styles.get("fontFamily"):
                if font not in tokens.fonts:
                    tokens.fonts.append(font)

            # Font sizes
            if size := styles.get("fontSize"):
                if size not in tokens.font_sizes:
                    tokens.font_sizes.append(size)

            # Spacing
            for key in ["padding", "margin"]:
                if val := styles.get(key):
                    if val != "0px" and val not in tokens.spacing_values:
                        tokens.spacing_values.append(val)

            # Border radius
            if radius := styles.get("borderRadius"):
                if radius != "0px" and radius not in tokens.border_radii:
                    tokens.border_radii.append(radius)

            # Shadows
            if shadow := styles.get("boxShadow"):
                if shadow != "none" and shadow not in tokens.shadows:
                    tokens.shadows.append(shadow)

    def _detect_tech_stack(self, snapshot: PageSnapshot) -> dict[str, str]:
        """Detect frontend tech stack from HTML and scripts."""
        html = snapshot.html
        stack = {}

        # Framework detection
        if "__vue__" in html or "data-v-" in html or "Vue" in html:
            stack["framework"] = "Vue.js"
        elif "__NEXT" in html or "_next" in html:
            stack["framework"] = "Next.js (React)"
        elif "__react" in html or "data-reactroot" in html or "_reactRootContainer" in html:
            stack["framework"] = "React"
        elif "ng-" in html or "ng2" in html:
            stack["framework"] = "Angular"

        # UI library detection
        if "el-" in html or "element" in html.lower():
            stack["ui_library"] = "Element UI / Element Plus"
        elif "ant-" in html:
            stack["ui_library"] = "Ant Design"
        elif "v-md" in html or "vuetify" in html.lower():
            stack["ui_library"] = "Vuetify"
        elif "bootstrap" in html.lower():
            stack["ui_library"] = "Bootstrap"

        # CSS framework
        if "tailwind" in html.lower():
            stack["css_framework"] = "Tailwind CSS"

        # Chart library
        if "echarts" in html.lower():
            stack["charts"] = "ECharts"
        elif "chart.js" in html.lower() or "chartjs" in html.lower():
            stack["charts"] = "Chart.js"

        # Build tool
        for style in snapshot.styles:
            if "vite" in style.lower():
                stack["build_tool"] = "Vite"
            elif "webpack" in style.lower():
                stack["build_tool"] = "Webpack"

        return stack

    def _detect_css_framework(self, class_counter: Counter) -> str:
        """Detect CSS framework from class naming patterns."""
        classes = set(class_counter.keys())

        el_count = sum(1 for c in classes if c.startswith("el-"))
        ant_count = sum(1 for c in classes if c.startswith("ant-"))
        tw_pattern = sum(1 for c in classes if re.match(r'^(bg|text|flex|grid|p|m|w|h|rounded|shadow|border)-', c))
        bs_count = sum(1 for c in classes if c in {"container", "row", "col", "btn", "form-control", "navbar"})

        scores = {
            "Element UI/Plus": el_count,
            "Ant Design": ant_count,
            "Tailwind CSS": tw_pattern,
            "Bootstrap": bs_count,
        }
        best = max(scores, key=scores.get)
        return best if scores[best] > 5 else "Custom / Unknown"

    def _detect_layout_pattern(self, routes: list[RouteInfo]) -> str:
        """Detect the predominant layout pattern."""
        sidebar_count = sum(1 for r in routes if r.has_sidebar)
        navbar_count = sum(1 for r in routes if r.has_navbar)
        footer_count = sum(1 for r in routes if r.has_footer)
        total = len(routes) or 1

        parts = []
        if navbar_count / total > 0.5:
            parts.append("top-navbar")
        if sidebar_count / total > 0.5:
            parts.append("sidebar")
        parts.append("main-content")
        if footer_count / total > 0.5:
            parts.append("footer")

        return " + ".join(parts)
