"""Inventory generator — produces structured page inventory from agent state."""

from __future__ import annotations

from typing import Any

from src.agent.state import AgentState, StateSnapshot, ExplorationTarget


class InventoryGenerator:
    """Generates page/state inventory JSON from agent state."""

    def generate(self, state: AgentState) -> list[dict[str, Any]]:
        """Generate inventory entries for all captured states."""
        entries = []

        for snapshot in sorted(state.states.values(), key=lambda s: s.timestamp):
            target = state.targets.get(snapshot.target_id)

            # Build parent path
            parent_path = self._build_parent_path(snapshot.target_id, state)

            entry = {
                "id": snapshot.id,
                "target_id": snapshot.target_id,
                "url": snapshot.url,
                "title": snapshot.title,
                "target_type": target.target_type.value if target else "unknown",
                "label": target.label if target else "",
                "parent_path": parent_path,
                "depth": snapshot.depth,
                "discovery_method": target.discovery_method if target else "",
                "visit_status": snapshot.visit_status.value,
                "novelty_score": snapshot.novelty_score,
                "screenshot": snapshot.screenshot_path,
                "html": snapshot.html_path,
                "timestamp": snapshot.timestamp,
                "retries": snapshot.retry_count,
                "error": snapshot.error,
            }
            entries.append(entry)

        return entries

    def _build_parent_path(self, target_id: str, state: AgentState) -> list[str]:
        """Build the parent hierarchy path for a target."""
        path = []
        current = state.targets.get(target_id)
        visited_ids: set[str] = set()

        while current and current.parent_id and current.parent_id not in visited_ids:
            visited_ids.add(current.id)
            parent = state.targets.get(current.parent_id)
            if parent:
                path.insert(0, parent.label)
                current = parent
            else:
                break

        return path if path else ["root"]
