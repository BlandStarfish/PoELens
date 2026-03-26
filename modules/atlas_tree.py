"""
Atlas passive tree data layer.
Downloads and parses the PoE Atlas passive tree, exposing it with the same
TreeNode interface as modules.passive_tree for rendering in AtlasTreePanel.
"""

import json
import math
import os
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "atlas_tree.json")
_FALLBACK_URL = "https://raw.githubusercontent.com/grindinggear/skilltree-export/master/atlasTree.json"
_HEADERS = {"User-Agent": "PoELens/1.0"}


# ─────────────────────────────────────────────────────────────────────────────
# Data class
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AtlasNode:
    node_id: str
    name: str
    x: float
    y: float
    stats: list
    node_type: str          # "notable" | "keystone" | "normal" | "start" | "mastery"
    connections: list       # list of adjacent node_ids
    is_notable: bool = False
    icon: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Tree class
# ─────────────────────────────────────────────────────────────────────────────

class AtlasTree:
    def __init__(self, nodes: dict, edges: list, raw: dict):
        self.nodes = nodes
        self.edges = edges
        self._raw = raw
        # Bounding box for coordinate normalisation
        xs = [n.x for n in nodes.values()]
        ys = [n.y for n in nodes.values()]
        self.x_min = min(xs) if xs else -6000
        self.x_max = max(xs) if xs else 6000
        self.y_min = min(ys) if ys else -6000
        self.y_max = max(ys) if ys else 6000

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def is_available(cls) -> bool:
        return os.path.exists(_DATA_PATH)

    @classmethod
    def load(cls) -> "AtlasTree":
        """Load from cache or raise FileNotFoundError."""
        if not os.path.exists(_DATA_PATH):
            raise FileNotFoundError(f"Atlas tree data not found at {_DATA_PATH}.")
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return cls._parse(raw)

    @classmethod
    def download(cls, callback=None) -> "AtlasTree":
        """Download the Atlas tree data from GGG's export repo and cache it."""
        def emit(msg):
            if callback:
                callback(msg)
            else:
                print(msg)

        emit("Downloading Atlas passive tree...")
        req = urllib.request.Request(_FALLBACK_URL, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        os.makedirs(os.path.dirname(_DATA_PATH), exist_ok=True)
        with open(_DATA_PATH, "wb") as f:
            f.write(data)
        emit(f"Saved ({len(data) // 1024} KB)")
        return cls._parse(json.loads(data))

    @classmethod
    def load_or_download(cls, callback=None) -> "AtlasTree":
        """Load if cached, otherwise download."""
        if os.path.exists(_DATA_PATH):
            return cls.load()
        return cls.download(callback)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @classmethod
    def _parse(cls, raw: dict) -> "AtlasTree":
        nodes = {}
        edges = set()
        raw_nodes = raw.get("nodes", {})
        groups = raw.get("groups", {})
        orbit_radii = raw.get("orbitRadii", [0, 82, 162, 335, 493])
        skills_per_orbit = raw.get("skillsPerOrbit", [1, 6, 12, 12, 40])

        for node_id, nd in raw_nodes.items():
            name = nd.get("dn") or nd.get("name", "")
            stats = nd.get("sd") or nd.get("stats", [])
            if isinstance(stats, dict):
                stats = list(stats.values())

            # Determine node type
            if nd.get("ks") or nd.get("isKeystone"):
                ntype = "keystone"
            elif nd.get("not") or nd.get("isNotable"):
                ntype = "notable"
            elif nd.get("m") or nd.get("isMastery"):
                ntype = "mastery"
            elif str(node_id) == "0" or nd.get("isAscendancyStart"):
                ntype = "start"
            else:
                ntype = "normal"

            x, y = cls._coords(nd, groups, orbit_radii, skills_per_orbit)

            node = AtlasNode(
                node_id=str(node_id),
                name=name,
                x=x,
                y=y,
                stats=stats,
                node_type=ntype,
                connections=[str(c) for c in nd.get("out", []) + nd.get("in", [])],
                is_notable=(ntype in ("notable", "keystone")),
                icon=nd.get("icon", ""),
            )
            nodes[str(node_id)] = node

            for out_id in nd.get("out", []):
                edges.add(tuple(sorted([str(node_id), str(out_id)])))

        return cls(nodes, list(edges), raw)

    @classmethod
    def _coords(cls, nd, groups, orbit_radii, spo):
        """Compute absolute x,y from node data."""
        if "x" in nd and "y" in nd:
            return float(nd["x"]), float(nd["y"])

        gid = nd.get("group")
        g = groups.get(str(gid), groups.get(gid, {}))
        gx, gy = float(g.get("x", 0)), float(g.get("y", 0))
        orbit = nd.get("orbit", 0)
        oi = nd.get("orbitIndex", 0)
        r = orbit_radii[orbit] if orbit < len(orbit_radii) else 0
        npo = spo[orbit] if orbit < len(spo) else 12
        if npo == 0:
            return gx, gy
        angle = (2 * math.pi * oi / npo) - math.pi / 2
        return gx + r * math.cos(angle), gy + r * math.sin(angle)

    # ------------------------------------------------------------------
    # Search / query
    # ------------------------------------------------------------------

    def search(self, query: str) -> list:
        """Find nodes whose name or stats contain query (case-insensitive)."""
        q = query.lower()
        return [n for n in self.nodes.values()
                if n.node_type not in ("normal", "mastery")
                and (q in n.name.lower() or any(q in s.lower() for s in n.stats))]

    def get_node(self, node_id: str) -> Optional[AtlasNode]:
        return self.nodes.get(str(node_id))

    def nodes_by_type(self, ntype: str) -> list:
        return [n for n in self.nodes.values() if n.node_type == ntype]


# ─────────────────────────────────────────────────────────────────────────────
# CLI helper
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if "--download" in sys.argv:
        AtlasTree.download(callback=print)
    elif "--stats" in sys.argv:
        tree = AtlasTree.load()
        by_type = {}
        for n in tree.nodes.values():
            by_type[n.node_type] = by_type.get(n.node_type, 0) + 1
        print(f"Total nodes: {len(tree.nodes)}")
        print(f"Total edges: {len(tree.edges)}")
        for t, count in sorted(by_type.items()):
            print(f"  {t:15s}: {count}")
    else:
        print("Usage: python -m modules.atlas_tree --download | --stats")
