"""Sitemap generator — produces traversal graph from agent state."""

from __future__ import annotations

from typing import Any

from src.agent.state import AgentState, TargetType


class SitemapGenerator:
    """Generates site map / traversal graph from agent state."""

    def generate(self, state: AgentState) -> dict[str, Any]:
        """Generate sitemap with nodes, edges, and groups."""
        nodes = []
        groups: dict[str, dict] = {}

        for target in state.targets.values():
            node = {
                "id": target.id,
                "label": target.label,
                "type": target.target_type.value,
                "depth": target.depth,
                "discovery_method": target.discovery_method,
                "visited": target.id in state.visited,
                "skipped": target.id in state.skipped,
            }
            if target.parent_id:
                node["parent"] = target.parent_id
            nodes.append(node)

            # Build groups from parent relationships (depth 1 = groups)
            if target.parent_id and target.target_type == TargetType.ROUTE:
                parent = state.targets.get(target.parent_id)
                if parent and parent.id not in groups:
                    groups[parent.id] = {
                        "id": parent.id,
                        "label": parent.label,
                        "children": [],
                    }
                if parent and parent.id in groups:
                    groups[parent.id]["children"].append(target.id)

        edges = []
        for edge in state.edges:
            edges.append({
                "from": edge.from_state_id,
                "to": edge.to_state_id,
                "action": edge.action.value,
                "label": edge.label,
                "timestamp": edge.timestamp,
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "groups": list(groups.values()),
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "total_groups": len(groups),
                "routes": sum(1 for n in nodes if n["type"] == "route"),
                "interactions": sum(1 for n in nodes if n["type"] != "route"),
            },
        }
