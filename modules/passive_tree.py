"""
Passive tree data layer.

Loads SkillTree.json (downloaded by install.py), parses nodes and
connections, and exposes a clean API for the UI to render.

Coordinate system:
  GGG's tree uses large integer coordinates (roughly -14000 to +14000).
  The viewer scales and translates these to screen space.

Node types (from GGG data "classStartIndex" / "m" flags):
  - Normal small passive
  - Notable
  - Keystone
  - Class start node
  - Ascendancy node
  - Jewel socket
  - Mastery

Usage:
  tree = PassiveTree.load()
  nodes = tree.nodes           # dict[str, TreeNode]
  edges = tree.edges           # list[(node_id_a, node_id_b)]
  tree.search("life")          # returns list of matching nodes
"""

import json
import os
import re
import threading
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "passive_tree.json")
_CDN_PAGE  = "https://www.pathofexile.com/passive-skill-tree"
# Official GGG-maintained export repo — always current, no versioned path needed
_FALLBACK_URL = (
    "https://raw.githubusercontent.com/grindinggear/skilltree-export/master/data.json"
)
_HEADERS = {"User-Agent": "ExileHUD/1.0 (github.com/BlandStarfish/ExileHUD)"}


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TreeNode:
    node_id: str
    name: str
    x: float
    y: float
    stats: list[str]
    node_type: str          # "normal" | "notable" | "keystone" | "class_start" | "ascendancy" | "jewel" | "mastery"
    connections: list[str]  # list of adjacent node_ids
    is_ascendancy: bool = False
    ascendancy_name: str = ""
    class_start_index: int = -1
    icon: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Loader / parser
# ─────────────────────────────────────────────────────────────────────────────

class PassiveTree:
    def __init__(self, nodes: dict[str, TreeNode], edges: list[tuple[str, str]], raw: dict):
        self.nodes = nodes
        self.edges = edges
        self._raw = raw
        # Bounding box for coordinate normalisation
        xs = [n.x for n in nodes.values()]
        ys = [n.y for n in nodes.values()]
        self.x_min = min(xs) if xs else -14000
        self.x_max = max(xs) if xs else 14000
        self.y_min = min(ys) if ys else -14000
        self.y_max = max(ys) if ys else 14000

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def load(cls) -> "PassiveTree":
        """Load from cache or raise FileNotFoundError."""
        if not os.path.exists(_DATA_PATH):
            raise FileNotFoundError(
                f"Passive tree data not found at {_DATA_PATH}. "
                "Run install.py or call PassiveTree.download() first."
            )
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return cls._parse(raw)

    @classmethod
    def download(cls, callback=None) -> "PassiveTree":
        """
        Download the tree data from GGG CDN (or fallback) and cache it.
        callback(status: str) is called with progress messages.
        Returns loaded PassiveTree on success.
        """
        def emit(msg):
            if callback:
                callback(msg)
            else:
                print(msg)

        os.makedirs(os.path.dirname(_DATA_PATH), exist_ok=True)

        tree_url = cls._find_cdn_url(emit)
        emit(f"Fetching tree data...")

        data = cls._fetch_url(tree_url)
        if data is None:
            emit("Primary URL failed, trying fallback...")
            data = cls._fetch_url(_FALLBACK_URL)
        if data is None:
            raise RuntimeError("Failed to download passive tree data from all sources.")

        with open(_DATA_PATH, "wb") as f:
            f.write(data)

        emit(f"Saved ({len(data)//1024} KB)")
        raw = json.loads(data)
        return cls._parse(raw)

    @classmethod
    def load_or_download(cls, callback=None) -> "PassiveTree":
        """Load if cached, otherwise download."""
        if os.path.exists(_DATA_PATH):
            return cls.load()
        return cls.download(callback)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @classmethod
    def _parse(cls, raw: dict) -> "PassiveTree":
        nodes: dict[str, TreeNode] = {}
        edges: set[tuple[str, str]] = set()

        raw_nodes = raw.get("nodes", {})

        for node_id, nd in raw_nodes.items():
            ntype = cls._node_type(nd)
            x, y = cls._node_coords(nd, raw)

            # GGG export uses abbreviated keys: dn=name, sd=stats, ascendancyName etc.
            # Support both the abbreviated (current) and long-form (legacy) field names.
            name  = nd.get("dn") or nd.get("name", "")
            stats = nd.get("sd") or nd.get("stats", [])
            # sd can be a dict {0: "stat"} in some versions — normalise to list
            if isinstance(stats, dict):
                stats = list(stats.values())

            node = TreeNode(
                node_id=str(node_id),
                name=name,
                x=x,
                y=y,
                stats=stats,
                node_type=ntype,
                connections=[str(c) for c in nd.get("out", []) + nd.get("in", [])],
                is_ascendancy=bool(nd.get("isAscendancyStart") or nd.get("ascendancyName")),
                ascendancy_name=nd.get("ascendancyName", ""),
                class_start_index=nd.get("classStartIndex", -1),
                icon=nd.get("icon", ""),
            )
            nodes[str(node_id)] = node

            # Add edges (deduplicated via set of frozensets)
            for out_id in nd.get("out", []):
                edge = tuple(sorted([str(node_id), str(out_id)]))
                edges.add(edge)

        return cls(nodes, list(edges), raw)

    @classmethod
    def _node_type(cls, nd: dict) -> str:
        # GGG abbreviated keys: ks=keystone, not=notable, m=mastery
        # Also handle legacy long-form keys for older cached data files
        if nd.get("ks") or nd.get("isKeystone"):
            return "keystone"
        if nd.get("not") or nd.get("isNotable"):
            return "notable"
        if nd.get("classStartIndex", -1) >= 0:
            return "class_start"
        if nd.get("isAscendancyStart") or nd.get("ascendancyName"):
            return "ascendancy"
        if nd.get("isJewelSocket"):
            return "jewel"
        if nd.get("m") or nd.get("isMastery"):
            return "mastery"
        return "normal"

    @classmethod
    def _node_coords(cls, nd: dict, raw: dict) -> tuple[float, float]:
        """Compute absolute x,y from node's group+orbit data or direct coords."""
        import math

        # New format: nodes have direct x, y
        if "x" in nd and "y" in nd:
            return float(nd["x"]), float(nd["y"])

        # Legacy format: group + orbit + orbitIndex
        group_id = nd.get("group")
        orbit = nd.get("orbit", 0)
        orbit_index = nd.get("orbitIndex", 0)

        groups = raw.get("groups", {})
        group = groups.get(str(group_id), groups.get(group_id, {}))
        gx = float(group.get("x", 0))
        gy = float(group.get("y", 0))
        # groups use "n" (current GGG format) or "nodes" (legacy) for their node list
        # — no action needed here, we just need x/y from the group

        orbit_radii = raw.get("orbitRadii", [0, 82, 162, 335, 493])
        nodes_per_orbit = raw.get("skillsPerOrbit", [1, 6, 12, 12, 40])

        if orbit >= len(orbit_radii):
            return gx, gy

        radius = orbit_radii[orbit]
        npo = nodes_per_orbit[orbit] if orbit < len(nodes_per_orbit) else 12
        if npo == 0:
            return gx, gy

        angle = (2 * math.pi * orbit_index / npo) - (math.pi / 2)
        x = gx + radius * math.cos(angle)
        y = gy + radius * math.sin(angle)
        return x, y

    # ------------------------------------------------------------------
    # Search / query
    # ------------------------------------------------------------------

    def search(self, query: str, include_ascendancy: bool = False) -> list[TreeNode]:
        """Find nodes whose name or stats contain query (case-insensitive)."""
        q = query.lower()
        results = []
        for node in self.nodes.values():
            if node.is_ascendancy and not include_ascendancy:
                continue
            if node.node_type in ("class_start", "mastery"):
                continue
            if q in node.name.lower() or any(q in s.lower() for s in node.stats):
                results.append(node)
        return sorted(results, key=lambda n: (n.node_type != "keystone", n.node_type != "notable", n.name))

    def get_node(self, node_id: str) -> Optional[TreeNode]:
        return self.nodes.get(str(node_id))

    def nodes_by_type(self, ntype: str) -> list[TreeNode]:
        return [n for n in self.nodes.values() if n.node_type == ntype]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_cdn_url(emit) -> str:
        emit("Finding current tree data URL...")
        try:
            req = urllib.request.Request(_CDN_PAGE, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            match = re.search(r'"(https://[^"]+/data/SkillTree\.json[^"]*)"', html)
            if match:
                return match.group(1)
        except Exception as e:
            emit(f"Warning: could not fetch CDN page: {e}")
        return _FALLBACK_URL

    @staticmethod
    def _fetch_url(url: str) -> Optional[bytes]:
        try:
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except Exception:
            return None


# ─────────────────────────────────────────────────────────────────────────────
# CLI helper
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if "--download" in sys.argv:
        PassiveTree.download(callback=print)
    elif "--stats" in sys.argv:
        tree = PassiveTree.load()
        by_type = {}
        for n in tree.nodes.values():
            by_type[n.node_type] = by_type.get(n.node_type, 0) + 1
        print(f"Total nodes: {len(tree.nodes)}")
        print(f"Total edges: {len(tree.edges)}")
        for t, count in sorted(by_type.items()):
            print(f"  {t:15s}: {count}")
    else:
        print("Usage: python -m modules.passive_tree --download | --stats")
