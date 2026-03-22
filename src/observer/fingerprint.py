"""DOM fingerprinting — structural hash for novelty comparison."""

from __future__ import annotations

import hashlib
from collections import Counter

from bs4 import BeautifulSoup, Tag


class DOMFingerprinter:
    """Generates structural fingerprints of HTML pages."""

    # Tags that matter for structure (skip script/style/meta)
    STRUCTURAL_TAGS = {
        "div", "section", "article", "aside", "main", "header", "footer", "nav",
        "form", "input", "select", "textarea", "button", "label",
        "table", "thead", "tbody", "tr", "th", "td",
        "ul", "ol", "li", "dl", "dt", "dd",
        "h1", "h2", "h3", "h4", "h5", "h6",
        "p", "span", "a", "img",
        "dialog",
    }

    # Class prefixes that indicate UI components
    COMPONENT_PREFIXES = (
        "el-", "ant-", "v-", "arco-", "n-",  # UI libraries
        "van-", "ivu-", "t-",
    )

    def compute(self, html: str) -> str:
        """Compute structural fingerprint hash of HTML."""
        soup = BeautifulSoup(html, "lxml")

        # Build structural signature
        signature_parts = []

        # 1. Tag tree depth-limited (first 3 levels)
        body = soup.find("body") or soup
        tag_tree = self._tag_tree(body, max_depth=3)
        signature_parts.append(f"tree:{tag_tree}")

        # 2. Component class inventory
        component_classes = self._extract_component_classes(soup)
        signature_parts.append(f"components:{','.join(sorted(component_classes))}")

        # 3. Structural element counts
        counts = self._count_structural_elements(soup)
        count_str = ",".join(f"{k}:{v}" for k, v in sorted(counts.items()))
        signature_parts.append(f"counts:{count_str}")

        combined = "|".join(signature_parts)
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def compute_similarity(self, fp1: str, fp2: str) -> float:
        """Simple binary similarity — 1.0 if same, 0.0 if different.
        For more nuanced comparison, use detailed_similarity."""
        return 1.0 if fp1 == fp2 else 0.0

    def detailed_fingerprint(self, html: str) -> dict:
        """Return detailed fingerprint components (for nuanced comparison)."""
        soup = BeautifulSoup(html, "lxml")
        return {
            "component_classes": self._extract_component_classes(soup),
            "element_counts": self._count_structural_elements(soup),
            "tag_tree_hash": self._tag_tree(soup.find("body") or soup, max_depth=3),
        }

    def detailed_similarity(self, fp_a: dict, fp_b: dict) -> float:
        """Compare two detailed fingerprints. Returns 0.0-1.0."""
        scores = []

        # Component class overlap (Jaccard similarity)
        set_a = set(fp_a.get("component_classes", []))
        set_b = set(fp_b.get("component_classes", []))
        if set_a or set_b:
            jaccard = len(set_a & set_b) / len(set_a | set_b) if (set_a | set_b) else 1.0
            scores.append(jaccard)

        # Element count similarity (cosine-ish)
        counts_a = fp_a.get("element_counts", {})
        counts_b = fp_b.get("element_counts", {})
        all_keys = set(counts_a) | set(counts_b)
        if all_keys:
            dot = sum(counts_a.get(k, 0) * counts_b.get(k, 0) for k in all_keys)
            mag_a = sum(v**2 for v in counts_a.values()) ** 0.5 or 1
            mag_b = sum(v**2 for v in counts_b.values()) ** 0.5 or 1
            cosine = dot / (mag_a * mag_b)
            scores.append(cosine)

        # Tag tree match (binary)
        if fp_a.get("tag_tree_hash") == fp_b.get("tag_tree_hash"):
            scores.append(1.0)
        else:
            scores.append(0.0)

        return sum(scores) / len(scores) if scores else 0.0

    def _tag_tree(self, element: Tag, max_depth: int, current_depth: int = 0) -> str:
        """Build a string representation of the tag tree structure."""
        if current_depth >= max_depth:
            return ""
        if not isinstance(element, Tag):
            return ""

        tag_name = element.name
        if tag_name not in self.STRUCTURAL_TAGS and not any(
            cls.startswith(p) for cls in element.get("class", []) for p in self.COMPONENT_PREFIXES
        ):
            tag_name = "div"  # normalize non-structural tags

        children = []
        for child in element.children:
            if isinstance(child, Tag):
                child_repr = self._tag_tree(child, max_depth, current_depth + 1)
                if child_repr:
                    children.append(child_repr)

        if children:
            return f"{tag_name}({','.join(children[:20])})"  # cap children
        return tag_name

    def _extract_component_classes(self, soup: BeautifulSoup) -> list[str]:
        """Extract CSS classes that indicate UI components."""
        component_classes: set[str] = set()
        for tag in soup.find_all(attrs={"class": True}):
            for cls in tag.get("class", []):
                if any(cls.startswith(p) for p in self.COMPONENT_PREFIXES):
                    # Normalize: keep base component class, not modifiers
                    # e.g., "el-table--border" -> "el-table"
                    base = cls.split("--")[0]
                    component_classes.add(base)
        return sorted(component_classes)

    def _count_structural_elements(self, soup: BeautifulSoup) -> dict[str, int]:
        """Count key structural elements."""
        counter: Counter[str] = Counter()
        for tag in soup.find_all(True):
            if tag.name in self.STRUCTURAL_TAGS:
                counter[tag.name] += 1
            # Also count UI component roots
            for cls in tag.get("class", []):
                if any(cls.startswith(p) for p in self.COMPONENT_PREFIXES):
                    base = cls.split("--")[0]
                    counter[f"component:{base}"] += 1
                    break  # one per element
        return dict(counter)
