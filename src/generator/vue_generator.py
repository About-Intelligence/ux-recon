"""Vue project generator — scaffolds a Vue 3 project from site analysis."""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console

from src.analyzer.page_analyzer import SiteAnalysis
from src.ai.client import AIClient
from src.config import AppConfig

console = Console()


class VueGenerator:
    """Generates a Vue 3 project structure from site analysis data."""

    def __init__(self, config: AppConfig, ai_client: AIClient):
        self.config = config
        self.ai = ai_client
        self._project_root = Path(__file__).parent.parent.parent
        self._output_dir = self._project_root / config.output.vue_project_dir

    async def generate(self, analysis: SiteAnalysis, summary: str) -> Path:
        """Generate a complete Vue 3 project from site analysis."""
        console.print("[yellow]Generating Vue 3 project...[/yellow]")

        self._output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Generate package.json
        self._write_package_json(analysis)

        # 2. Generate project config files
        self._write_config_files()

        # 3. Generate directory structure
        src_dir = self._output_dir / "src"
        for d in ["components", "views", "router", "assets", "layouts", "stores", "styles"]:
            (src_dir / d).mkdir(parents=True, exist_ok=True)

        # 4. Generate main entry files
        self._write_main_files(analysis)

        # 5. Generate router from discovered routes
        self._write_router(analysis)

        # 6. Generate layout components
        await self._generate_layouts(analysis, summary)

        # 7. Generate page views (stubs with structure)
        await self._generate_views(analysis, summary)

        # 8. Generate global styles / design tokens
        self._write_styles(analysis)

        # 9. Generate index.html
        self._write_index_html(analysis)

        console.print(f"[green]Vue project generated at: {self._output_dir}[/green]")
        return self._output_dir

    def _write_package_json(self, analysis: SiteAnalysis) -> None:
        ui_lib = analysis.tech_stack.get("ui_library", "")
        deps = {
            "vue": "^3.4",
            "vue-router": "^4.3",
            "pinia": "^2.1",
        }

        if "Element" in ui_lib:
            deps["element-plus"] = "^2.5"
            deps["@element-plus/icons-vue"] = "^2.3"
        elif "Ant" in ui_lib:
            deps["ant-design-vue"] = "^4.1"

        if "ECharts" in analysis.tech_stack.get("charts", ""):
            deps["echarts"] = "^5.5"
            deps["vue-echarts"] = "^6.6"

        package = {
            "name": "frontend-mimic-replica",
            "version": "0.1.0",
            "private": True,
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "vite build",
                "preview": "vite preview",
            },
            "dependencies": deps,
            "devDependencies": {
                "@vitejs/plugin-vue": "^5.0",
                "vite": "^5.4",
                "sass": "^1.72",
            },
        }

        (self._output_dir / "package.json").write_text(
            json.dumps(package, indent=2), encoding="utf-8"
        )

    def _write_config_files(self) -> None:
        # vite.config.js
        (self._output_dir / "vite.config.js").write_text("""import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
})
""", encoding="utf-8")

        # .gitignore for generated project
        (self._output_dir / ".gitignore").write_text("""node_modules/
dist/
.env
.env.local
*.local
""", encoding="utf-8")

    def _write_main_files(self, analysis: SiteAnalysis) -> None:
        src = self._output_dir / "src"
        ui_lib = analysis.tech_stack.get("ui_library", "")

        # main.js
        imports = ["import { createApp } from 'vue'",
                   "import { createPinia } from 'pinia'",
                   "import App from './App.vue'",
                   "import router from './router'",
                   "import './styles/global.scss'"]
        setup = ["const app = createApp(App)",
                 "app.use(createPinia())",
                 "app.use(router)"]

        if "Element" in ui_lib:
            imports.append("import ElementPlus from 'element-plus'")
            imports.append("import 'element-plus/dist/index.css'")
            setup.append("app.use(ElementPlus)")
        elif "Ant" in ui_lib:
            imports.append("import Antd from 'ant-design-vue'")
            imports.append("import 'ant-design-vue/dist/reset.css'")
            setup.append("app.use(Antd)")

        setup.append("app.mount('#app')")

        (src / "main.js").write_text(
            "\n".join(imports) + "\n\n" + "\n".join(setup) + "\n",
            encoding="utf-8",
        )

        # App.vue
        (src / "App.vue").write_text("""<template>
  <router-view />
</template>

<script setup>
</script>
""", encoding="utf-8")

    def _write_router(self, analysis: SiteAnalysis) -> None:
        """Generate Vue Router config from discovered routes."""
        routes_code = []
        for i, route in enumerate(analysis.routes):
            # Convert hash route to vue-router path
            path = route.path
            if "#/" in path:
                path = path.split("#", 1)[1].split("?")[0]
            elif not path.startswith("/"):
                path = "/"

            name = path.strip("/").replace("/", "-") or "home"
            view_name = "".join(word.capitalize() for word in name.split("-")) + "View"

            routes_code.append(
                f"  {{ path: '{path}', name: '{name}', "
                f"component: () => import('@/views/{view_name}.vue') }},"
            )

        router_content = f"""import {{ createRouter, createWebHashHistory }} from 'vue-router'

const routes = [
{chr(10).join(routes_code)}
]

const router = createRouter({{
  history: createWebHashHistory(),
  routes,
}})

export default router
"""
        (self._output_dir / "src" / "router" / "index.js").write_text(
            router_content, encoding="utf-8"
        )

    async def _generate_layouts(self, analysis: SiteAnalysis, summary: str) -> None:
        """Generate layout components based on detected layout pattern."""
        layout_info = f"""Layout pattern: {analysis.layout_pattern}
Components found: {[c.type for c in analysis.components]}
Design tokens: {json.dumps(vars(analysis.design_tokens), default=str)}

Summary excerpt (layout section):
{summary[:2000] if summary else 'No summary available'}"""

        # Generate main layout
        layout_code = await self.ai.generate_vue_component(
            component_info=f"Main application layout with pattern: {analysis.layout_pattern}. "
                          f"This should include the overall page structure with "
                          f"{'sidebar, ' if 'sidebar' in analysis.layout_pattern else ''}"
                          f"{'top navbar, ' if 'navbar' in analysis.layout_pattern else ''}"
                          f"main content area with <router-view />, "
                          f"{'and footer' if 'footer' in analysis.layout_pattern else ''}.",
            design_context=layout_info,
        )

        (self._output_dir / "src" / "layouts" / "DefaultLayout.vue").write_text(
            layout_code, encoding="utf-8"
        )

    async def _generate_views(self, analysis: SiteAnalysis, summary: str) -> None:
        """Generate view stubs for each discovered route."""
        for route in analysis.routes:
            path = route.path
            if "#/" in path:
                path = path.split("#", 1)[1].split("?")[0]
            elif not path.startswith("/"):
                path = "/"

            name = path.strip("/").replace("/", "-") or "home"
            view_name = "".join(word.capitalize() for word in name.split("-")) + "View"

            # Generate a structural stub
            component_list = ", ".join(route.component_types) if route.component_types else "unknown"
            view_code = f"""<template>
  <DefaultLayout>
    <div class="{name}-page">
      <h1>{route.title or name}</h1>
      <!-- Components on this page: {component_list} -->
      <!-- TODO: Implement page content based on analysis -->
      <p>Route: {path}</p>
    </div>
  </DefaultLayout>
</template>

<script setup>
import DefaultLayout from '@/layouts/DefaultLayout.vue'
</script>

<style scoped>
.{name}-page {{
  padding: 20px;
}}
</style>
"""
            (self._output_dir / "src" / "views" / f"{view_name}.vue").write_text(
                view_code, encoding="utf-8"
            )

    def _write_styles(self, analysis: SiteAnalysis) -> None:
        """Generate global styles from design tokens."""
        tokens = analysis.design_tokens

        # Build CSS custom properties
        colors_css = ""
        for category, colors in tokens.colors.items():
            for i, color in enumerate(colors[:10]):
                colors_css += f"  --color-{category}-{i}: {color};\n"

        fonts_css = ""
        if tokens.fonts:
            fonts_css = f"  --font-primary: {tokens.fonts[0]};\n"
            if len(tokens.fonts) > 1:
                fonts_css += f"  --font-secondary: {tokens.fonts[1]};\n"

        scss_content = f"""// Auto-generated design tokens from site analysis
// Customize these to match the original site more closely

:root {{
  // Colors
{colors_css}
  // Typography
{fonts_css}
  // Spacing
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;

  // Border radius
{chr(10).join(f'  --radius-{i}: {r};' for i, r in enumerate(tokens.border_radii[:5]))}

  // Shadows
{chr(10).join(f'  --shadow-{i}: {s};' for i, s in enumerate(tokens.shadows[:5]))}
}}

// Global reset & base styles
* {{
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}}

body {{
  font-family: var(--font-primary, sans-serif);
  color: var(--color-text-0, #333);
  background-color: var(--color-background-0, #fff);
}}
"""
        (self._output_dir / "src" / "styles" / "global.scss").write_text(
            scss_content, encoding="utf-8"
        )

    def _write_index_html(self, analysis: SiteAnalysis) -> None:
        (self._output_dir / "index.html").write_text("""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Frontend Mimic Replica</title>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.js"></script>
</body>
</html>
""", encoding="utf-8")
