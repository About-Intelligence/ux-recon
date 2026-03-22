"""Page analyzer — extracts structural information from a single page's HTML."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from bs4 import BeautifulSoup, Tag
from rich.console import Console

console = Console()


class PageAnalyzer:
    """Analyzes a single page's HTML to extract structural and design information."""

    def analyze(self, html: str, computed_styles: dict[str, dict[str, str]] | None = None) -> dict:
        """Analyze a single page. Returns structured analysis dict."""
        soup = BeautifulSoup(html, "lxml")

        result = {
            "component_types": self._get_component_types(soup),
            "components": self._detect_components(soup),
            "layout_pattern": self._detect_layout(soup),
            "tech_stack": self._detect_tech_stack(html),
            "css_framework": self._detect_css_framework(soup),
            "design_tokens": self._extract_design_tokens(computed_styles) if computed_styles else {},
            "element_stats": self._count_elements(soup),
        }

        return result

    def _get_component_types(self, soup: BeautifulSoup) -> list[str]:
        """Identify component types present on the page."""
        types = []
        checks = {
            "table": "table, .el-table, .ant-table",
            "form": "form, .el-form, .ant-form",
            "card": ".card, .el-card, .ant-card",
            "modal": ".modal, .el-dialog, .ant-modal, [role='dialog']",
            "tabs": ".el-tabs, .ant-tabs, .nav-tabs",
            "button": "button, .el-button, .ant-btn",
            "input": ".el-input, .ant-input, input:not([type='hidden'])",
            "dropdown": ".el-dropdown, .ant-dropdown",
            "pagination": ".el-pagination, .ant-pagination",
            "breadcrumb": ".el-breadcrumb, .ant-breadcrumb",
            "tree": ".el-tree, .ant-tree",
            "upload": "[class*='upload'], input[type='file']",
            "tag": ".el-tag, .ant-tag, .badge",
            "select": "select, .el-select, .ant-select",
            "drawer": ".el-drawer, .ant-drawer",
            "sidebar": ".el-aside, .ant-layout-sider, [class*='sidebar']",
            "navbar": "nav, .navbar, .el-header",
        }
        for comp_type, selector in checks.items():
            if soup.select_one(selector):
                types.append(comp_type)
        return types

    def _detect_components(self, soup: BeautifulSoup) -> list[dict]:
        """Detect and catalog UI components with counts."""
        selectors = {
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
            "pagination": ".el-pagination, .ant-pagination",
            "tag": ".el-tag, .ant-tag, .badge",
            "breadcrumb": ".el-breadcrumb, .ant-breadcrumb",
        }

        components = []
        for comp_type, selector in selectors.items():
            elements = soup.select(selector)
            if elements:
                sample = elements[0]
                classes = sample.get("class", []) if isinstance(sample, Tag) else []
                components.append({
                    "type": comp_type,
                    "count": len(elements),
                    "sample_classes": list(classes)[:5],
                })

        return components

    def _detect_layout(self, soup: BeautifulSoup) -> str:
        """Detect page layout pattern."""
        parts = []
        if soup.select_one("nav, .navbar, .el-header, .ant-layout-header, header"):
            parts.append("top-navbar")
        if soup.select_one(".sidebar, .el-aside, .ant-layout-sider, [class*='sidebar']"):
            parts.append("sidebar")
        parts.append("main-content")
        if soup.select_one("footer, .footer, .el-footer"):
            parts.append("footer")
        return " + ".join(parts)

    def _detect_tech_stack(self, html: str) -> dict[str, str]:
        """Detect frontend tech stack."""
        stack = {}
        if "data-v-" in html or "__vue__" in html:
            stack["framework"] = "Vue.js"
        elif "__NEXT" in html or "_next" in html:
            stack["framework"] = "Next.js"
        elif "data-reactroot" in html or "_reactRootContainer" in html:
            stack["framework"] = "React"
        elif "ng-" in html:
            stack["framework"] = "Angular"

        if "el-" in html:
            stack["ui_library"] = "Element Plus"
        elif "ant-" in html:
            stack["ui_library"] = "Ant Design"
        elif "bootstrap" in html.lower():
            stack["ui_library"] = "Bootstrap"

        return stack

    def _detect_css_framework(self, soup: BeautifulSoup) -> str:
        """Detect CSS framework from class naming patterns."""
        classes: set[str] = set()
        for tag in soup.find_all(attrs={"class": True}):
            for cls in tag.get("class", []):
                classes.add(cls)

        el = sum(1 for c in classes if c.startswith("el-"))
        ant = sum(1 for c in classes if c.startswith("ant-"))
        tw = sum(1 for c in classes if re.match(r'^(bg|text|flex|grid|p|m|w|h|rounded|shadow|border)-', c))

        scores = {"Element Plus": el, "Ant Design": ant, "Tailwind CSS": tw}
        best = max(scores, key=scores.get)  # type: ignore[arg-type]
        return best if scores[best] > 5 else "unknown"

    def _extract_design_tokens(self, computed_styles: dict[str, dict[str, str]]) -> dict:
        """Extract design tokens from computed styles."""
        tokens: dict[str, Any] = {
            "colors": {"text": [], "background": []},
            "fonts": [],
            "font_sizes": [],
            "border_radii": [],
            "shadows": [],
        }

        for selector, styles in computed_styles.items():
            for key, category in [("color", "text"), ("backgroundColor", "background")]:
                val = styles.get(key, "")
                if val and val not in ("rgba(0, 0, 0, 0)", "transparent") and val not in tokens["colors"][category]:
                    tokens["colors"][category].append(val)

            font = styles.get("fontFamily", "")
            if font and font not in tokens["fonts"]:
                tokens["fonts"].append(font)

            size = styles.get("fontSize", "")
            if size and size not in tokens["font_sizes"]:
                tokens["font_sizes"].append(size)

            radius = styles.get("borderRadius", "")
            if radius and radius != "0px" and radius not in tokens["border_radii"]:
                tokens["border_radii"].append(radius)

            shadow = styles.get("boxShadow", "")
            if shadow and shadow != "none" and shadow not in tokens["shadows"]:
                tokens["shadows"].append(shadow)

        return tokens

    def _count_elements(self, soup: BeautifulSoup) -> dict[str, int]:
        """Count key element types for structural comparison."""
        counter: Counter[str] = Counter()
        for tag in soup.find_all(True):
            counter[tag.name] += 1
        # Return top 20 most common
        return dict(counter.most_common(20))
