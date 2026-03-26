"""
Build path simulation for the passive tree.

Uses BFS from the class start node to find shortest paths to target keystones
and notables, then fills remaining passive points outward.
"""

import collections
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from modules.passive_tree import PassiveTree


def calc_available_points(level: int) -> int:
    """
    Approximate total passive points at a given character level.
    Includes base skill points (level - 1) plus scaled quest point approximation.
    """
    skill_pts = max(0, level - 1)
    # Quest passive points are awarded throughout Acts 1-10 (~24 total max)
    # Scale gradually so low levels don't overstate available points
    quest_pts = min(24, level // 4)
    return skill_pts + quest_pts


def simulate_build(tree, class_index: int, keystones: list,
                   notable_search: list, fill_search: list,
                   available_points: int) -> set:
    """
    BFS from the class start node toward target keystones and notables.

    Phase 1: BFS the full tree recording shortest-path parents. When a target
             node is first reached, trace the path back to start. Stop adding
             new target paths once the budget is exhausted.
             Keystones are always included (never budget-skipped).
             Notables are added in order of proximity (BFS order = closest first)
             up to a cap of available_points // 6 notables.
    Phase 2: Fill remaining budget via BFS expansion from allocated nodes,
             prioritising neighbors that match fill_search terms.

    Returns a set of node_id strings (always <= available_points + small slack).
    """
    # Find class start node
    start_node = None
    for node in tree.nodes.values():
        if node.node_type == "class_start" and node.class_start_index == class_index:
            start_node = node
            break
    if start_node is None:
        return set()

    keystone_ids = _find_targets(tree, keystones, [])
    notable_ids  = _find_targets(tree, [], notable_search)
    notable_cap  = max(4, available_points // 6)   # limit notables by level

    # BFS from start, building parent map
    parent: dict = {start_node.node_id: None}
    queue = collections.deque([start_node.node_id])
    allocated: set = {start_node.node_id}
    found_notables = 0

    while queue:
        nid = queue.popleft()
        node = tree.nodes.get(nid)
        if node is None:
            continue
        for conn_id in node.connections:
            if conn_id in parent or conn_id not in tree.nodes:
                continue
            parent[conn_id] = nid
            queue.append(conn_id)

            is_keystone = conn_id in keystone_ids
            is_notable  = conn_id in notable_ids

            # Always path to keystones; path to notables up to cap and budget
            if is_keystone or (is_notable and found_notables < notable_cap
                               and len(allocated) < available_points):
                if is_notable and not is_keystone:
                    found_notables += 1
                # Trace shortest path back to start
                trace = conn_id
                while trace is not None:
                    allocated.add(trace)
                    trace = parent.get(trace)

    # Phase 2: fill remaining budget with BFS expansion
    if len(allocated) < available_points:
        fill_targets = _find_targets(tree, [], fill_search) if fill_search else set()
        expand  = collections.deque(allocated)
        visited = set(allocated)
        while expand and len(allocated) < available_points:
            nid  = expand.popleft()
            node = tree.nodes.get(nid)
            if node is None:
                continue
            # Prioritise fill-target neighbours so the build "spreads" correctly
            neighbors = sorted(
                [c for c in node.connections if c not in visited and c in tree.nodes],
                key=lambda c: (0 if c in fill_targets else 1),
            )
            for conn_id in neighbors:
                if conn_id not in visited:
                    visited.add(conn_id)
                    allocated.add(conn_id)
                    expand.append(conn_id)
                    if len(allocated) >= available_points:
                        break

    return allocated


def respec_cost(nodes_a: set, nodes_b: set) -> int:
    """
    Regret Orbs needed to go from build A to build B.
    = nodes allocated in A but not in B (must be unspecced).
    Does not count class start node (it can never be unspecced).
    """
    return len(nodes_a - nodes_b)


def _find_targets(tree, keystones: list, search_terms: list) -> set:
    """Find node IDs matching keystones (exact name) or search terms (name/stat substring)."""
    targets = set()
    ks_lower = {k.lower() for k in keystones}
    sq_lower = [t.lower() for t in search_terms]

    for node in tree.nodes.values():
        if node.is_ascendancy:
            continue
        if node.node_type in ("class_start", "mastery", "normal"):
            continue  # only target keystones and notables

        name_lower = node.name.lower()

        # Exact keystone name match
        if name_lower in ks_lower:
            targets.add(node.node_id)
            continue

        # Search term match on name or stats
        for term in sq_lower:
            if term in name_lower or any(term in s.lower() for s in node.stats):
                targets.add(node.node_id)
                break

    return targets
