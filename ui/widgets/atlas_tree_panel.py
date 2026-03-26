"""
Atlas Passive Tree panel.
Renders the PoE Atlas passive tree with strategy preview and respec cost comparison.
Downloads tree data on first use.
"""

import collections
import json
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
    QGraphicsLineItem, QGraphicsItem,
    QProgressBar, QSizePolicy, QComboBox,
)
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QPen, QBrush, QColor, QFont, QTransform, QWheelEvent, QPainter

# ─────────────────────────────────────────────────────────────────────────────
# Colors
# ─────────────────────────────────────────────────────────────────────────────

NODE_COLORS = {
    "normal":   ("#1a2a1a", "#3a6a3a"),   # green tint
    "notable":  ("#1a2a10", "#8ac840"),   # bright green
    "keystone": ("#1a1a0a", "#d4a820"),   # gold
    "mastery":  ("#0a1a0a", "#50a850"),   # mid green
    "start":    ("#0a2a0a", "#60d060"),   # start node - bright green
}

NODE_RADII = {
    "normal": 4, "notable": 7, "keystone": 11, "mastery": 5, "start": 12
}

EDGE_COLOR      = QColor("#1a3a1a")
HIGHLIGHT_COLOR = QColor("#e2b96f")
SEARCH_COLOR    = QColor("#5cba6e")
ALLOCATED_COLOR = QColor("#ffd700")   # bright gold — strategy-highlighted nodes

SCALE_FACTOR = 0.04   # match passive tree scale

# ─────────────────────────────────────────────────────────────────────────────
# Data helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_atlas_strategies() -> list:
    """Load atlas strategy definitions from data/atlas_builds.json."""
    path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "atlas_builds.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)["strategies"]
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Background loader thread
# ─────────────────────────────────────────────────────────────────────────────

class AtlasLoader(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(object)   # AtlasTree
    error    = pyqtSignal(str)

    def __init__(self, download: bool = False):
        super().__init__()
        self._download = download

    def run(self):
        try:
            from modules.atlas_tree import AtlasTree
            if self._download:
                tree = AtlasTree.download(callback=lambda m: self.progress.emit(m))
            else:
                tree = AtlasTree.load_or_download(callback=lambda m: self.progress.emit(m))
            self.finished.emit(tree)
        except Exception as e:
            self.error.emit(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Custom graphics items
# ─────────────────────────────────────────────────────────────────────────────

class NodeItem(QGraphicsEllipseItem):
    def __init__(self, node, panel):
        r = NODE_RADII.get(node.node_type, 4)
        super().__init__(-r, -r, r * 2, r * 2)
        self._node = node
        self._panel = panel
        self._base_r = r
        self._allocated = False

        fill, border = NODE_COLORS.get(node.node_type, ("#1a2a1a", "#3a6a3a"))
        self.setBrush(QBrush(QColor(fill)))
        self.setPen(QPen(QColor(border), 1.5))
        self.setPos(node.x * SCALE_FACTOR, node.y * SCALE_FACTOR)
        self.setAcceptHoverEvents(True)
        self.setZValue(1)
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)

    def hoverEnterEvent(self, event):
        self._panel.show_tooltip(self._node)
        self.setPen(QPen(HIGHLIGHT_COLOR, 2.5))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        if self.data(0) == "search":
            pass
        elif self._allocated:
            self.setPen(QPen(ALLOCATED_COLOR, 3))
        else:
            fill, border = NODE_COLORS.get(self._node.node_type, ("#1a2a1a", "#3a6a3a"))
            self.setPen(QPen(QColor(border), 1.5))
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._panel.pin_node(self._node)
        super().mousePressEvent(event)

    def highlight(self, color: QColor):
        self.setPen(QPen(color, 3))
        self.setData(0, "search")
        self.setZValue(2)

    def clear_highlight(self):
        self.setData(0, None)
        if self._allocated:
            self.setPen(QPen(ALLOCATED_COLOR, 3))
            self.setZValue(3)
        else:
            fill, border = NODE_COLORS.get(self._node.node_type, ("#1a2a1a", "#3a6a3a"))
            self.setPen(QPen(QColor(border), 1.5))
            self.setZValue(1)

    def set_allocated(self, allocated: bool):
        self._allocated = allocated
        if allocated:
            if self.data(0) != "search":
                self.setPen(QPen(ALLOCATED_COLOR, 3))
            self.setZValue(3)
        else:
            if self.data(0) == "search":
                self.setZValue(2)
            else:
                fill, border = NODE_COLORS.get(self._node.node_type, ("#1a2a1a", "#3a6a3a"))
                self.setPen(QPen(QColor(border), 1.5))
                self.setZValue(1)


# ─────────────────────────────────────────────────────────────────────────────
# Custom view with pan + zoom
# ─────────────────────────────────────────────────────────────────────────────

class AtlasTreeView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("border: none; background: transparent;")
        self._zoom = 1.0

    def wheelEvent(self, event: QWheelEvent):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom *= factor
        self._zoom = max(0.05, min(50.0, self._zoom))
        self.scale(factor, factor)


# ─────────────────────────────────────────────────────────────────────────────
# Main panel
# ─────────────────────────────────────────────────────────────────────────────

class AtlasTreePanel(QWidget):
    def __init__(self):
        super().__init__()
        self._tree = None
        self._node_items: dict = {}
        self._pinned_node = None
        self._allocated_ids: set = set()
        self._active_strategy_nodes: set = set()
        self._compare_strategy_nodes: set = set()
        self._strategies = _load_atlas_strategies()
        self._build_ui()
        self._start_loading()

    # ------------------------------------------------------------------
    # UI layout
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Header label
        header = QLabel("Atlas Passive Tree — Strategy Planner")
        header.setStyleSheet(
            "color: #4ae8c8; font-size: 11px; font-weight: bold;"
            " background: #0a1a1a; border-radius: 3px; padding: 3px 6px;"
        )
        layout.addWidget(header)

        # Top bar: search + reset
        top = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search atlas nodes (e.g. 'breach', 'harvest', 'map')")
        self._search.setStyleSheet(
            "background: #0f0f23; color: #d4c5a9; border: 1px solid #1a3a1a;"
            " border-radius: 3px; padding: 3px; font-size: 11px;"
        )
        self._search.textChanged.connect(self._on_search)
        top.addWidget(self._search, 1)

        reset_btn = QPushButton("Reset View")
        reset_btn.setFixedWidth(80)
        reset_btn.clicked.connect(self._reset_view)
        top.addWidget(reset_btn)
        layout.addLayout(top)

        # Strategy selector row
        self._build_meta_row(layout)

        # Progress / status
        self._status = QLabel("Loading atlas tree data...")
        self._status.setStyleSheet("color: #8a7a65; font-size: 11px;")
        layout.addWidget(self._status)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setFixedHeight(4)
        self._progress.setStyleSheet(
            "QProgressBar { background: #0a1a0a; border: none; }"
            "QProgressBar::chunk { background: #4ae8c8; }"
        )
        layout.addWidget(self._progress)

        # Download prompt (shown when data not available)
        self._download_frame = QWidget()
        dl_layout = QVBoxLayout(self._download_frame)
        dl_layout.setContentsMargins(8, 8, 8, 8)
        dl_lbl = QLabel(
            "Atlas tree data not downloaded yet.\n"
            "Click below to download it from GGG's export repo (~2 MB)."
        )
        dl_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dl_lbl.setStyleSheet("color: #d4c5a9; font-size: 11px;")
        dl_lbl.setWordWrap(True)
        dl_layout.addWidget(dl_lbl)

        self._download_btn = QPushButton("Download Atlas Tree Data")
        self._download_btn.setStyleSheet(
            "QPushButton { color: #4ae8c8; font-size: 11px; padding: 6px 12px; }"
            "QPushButton:hover { background: #0a2a1a; }"
        )
        self._download_btn.clicked.connect(self._download_atlas)
        dl_layout.addWidget(self._download_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self._download_frame.hide()
        layout.addWidget(self._download_frame)

        # Graphics view
        self._scene = QGraphicsScene()
        self._scene.setBackgroundBrush(QBrush(QColor("#0d1a0d")))

        self._view = AtlasTreeView(self._scene)
        self._view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._view, 1)

        # Node detail panel
        self._detail = QLabel("Hover or click a node to see details.")
        self._detail.setWordWrap(True)
        self._detail.setFixedHeight(80)
        self._detail.setStyleSheet(
            "background: #0f0f23; color: #d4c5a9; font-size: 11px;"
            " border: 1px solid #1a3a1a; border-radius: 4px; padding: 6px;"
        )
        layout.addWidget(self._detail)

    def _build_meta_row(self, layout):
        """Add the strategy preview and compare rows."""
        # Strategy selector row
        row1 = QHBoxLayout()
        row1.setSpacing(4)

        strat_lbl = QLabel("Strategy:")
        strat_lbl.setStyleSheet("color: #8a7a65; font-size: 10px;")
        strat_lbl.setFixedWidth(52)
        row1.addWidget(strat_lbl)

        self._meta_combo = QComboBox()
        self._meta_combo.setStyleSheet(
            "QComboBox { background: #0f0f23; color: #d4c5a9; border: 1px solid #1a3a1a;"
            " border-radius: 3px; padding: 2px 4px; font-size: 10px; }"
            "QComboBox::drop-down { border: none; }"
        )
        self._meta_combo.addItem("— select strategy —", None)
        for strat in self._strategies:
            self._meta_combo.addItem(strat["name"], strat)
        row1.addWidget(self._meta_combo, 2)

        preview_btn = QPushButton("Preview")
        preview_btn.setFixedWidth(56)
        preview_btn.setStyleSheet(
            "QPushButton { color: #4ae8c8; font-size: 10px; padding: 2px 4px; }"
        )
        preview_btn.clicked.connect(self._preview_strategy)
        row1.addWidget(preview_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(46)
        clear_btn.setStyleSheet("QPushButton { font-size: 10px; padding: 2px 4px; }")
        clear_btn.clicked.connect(self._clear_strategy)
        row1.addWidget(clear_btn)

        layout.addLayout(row1)

        # Compare row
        row2 = QHBoxLayout()
        row2.setSpacing(4)

        vs_lbl = QLabel("vs:")
        vs_lbl.setStyleSheet("color: #8a7a65; font-size: 10px;")
        vs_lbl.setFixedWidth(20)
        row2.addWidget(vs_lbl)

        self._compare_combo = QComboBox()
        self._compare_combo.setStyleSheet(self._meta_combo.styleSheet())
        self._compare_combo.addItem("— compare strategy —", None)
        for strat in self._strategies:
            self._compare_combo.addItem(strat["name"], strat)
        row2.addWidget(self._compare_combo, 2)

        respec_btn = QPushButton("Respec Cost")
        respec_btn.setFixedWidth(80)
        respec_btn.setStyleSheet(
            "QPushButton { color: #e2b96f; font-size: 10px; padding: 2px 4px; }"
        )
        respec_btn.clicked.connect(self._show_respec_cost)
        row2.addWidget(respec_btn)

        self._respec_label = QLabel("")
        self._respec_label.setStyleSheet("color: #e05050; font-size: 10px;")
        row2.addWidget(self._respec_label, 1)

        layout.addLayout(row2)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _start_loading(self):
        from modules.atlas_tree import AtlasTree
        if not AtlasTree.is_available():
            # Show the download prompt immediately; don't attempt auto-download
            self._progress.hide()
            self._status.setText("Atlas tree data not found — download required.")
            self._download_frame.show()
            return

        self._loader = AtlasLoader(download=False)
        self._loader.progress.connect(self._on_load_progress)
        self._loader.finished.connect(self._on_load_done)
        self._loader.error.connect(self._on_load_error)
        self._loader.start()

    def _download_atlas(self):
        """User clicked the download button — start downloading."""
        self._download_btn.setEnabled(False)
        self._download_btn.setText("Downloading...")
        self._download_frame.hide()
        self._progress.show()
        self._status.setText("Downloading Atlas tree data...")

        self._dl_loader = AtlasLoader(download=True)
        self._dl_loader.progress.connect(self._on_load_progress)
        self._dl_loader.finished.connect(self._on_download_done)
        self._dl_loader.error.connect(self._on_download_error)
        self._dl_loader.start()

    @pyqtSlot(str)
    def _on_load_progress(self, msg: str):
        self._status.setText(msg)

    @pyqtSlot(object)
    def _on_load_done(self, tree):
        self._tree = tree
        self._progress.hide()
        self._status.setText(
            f"Atlas tree loaded — {len(tree.nodes)} nodes, {len(tree.edges)} connections"
        )
        self._render_tree()

    @pyqtSlot(str)
    def _on_load_error(self, msg: str):
        self._progress.hide()
        self._status.setText(f"Error loading atlas tree: {msg}")
        self._status.setStyleSheet("color: #e05050; font-size: 11px;")
        self._download_frame.show()

    @pyqtSlot(object)
    def _on_download_done(self, tree):
        self._download_btn.setEnabled(True)
        self._download_btn.setText("Download Atlas Tree Data")
        self._on_load_done(tree)

    @pyqtSlot(str)
    def _on_download_error(self, msg: str):
        self._download_btn.setEnabled(True)
        self._download_btn.setText("Download Atlas Tree Data")
        self._progress.hide()
        self._status.setText(f"Download failed: {msg}")
        self._status.setStyleSheet("color: #e05050; font-size: 11px;")
        self._download_frame.show()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_tree(self):
        if not self._tree:
            return

        self._scene.clear()
        self._node_items.clear()

        # Draw edges first (below nodes)
        pen = QPen(EDGE_COLOR, 0.5)
        pen.setCosmetic(False)
        for (a_id, b_id) in self._tree.edges:
            a = self._tree.nodes.get(a_id)
            b = self._tree.nodes.get(b_id)
            if a and b:
                line = QGraphicsLineItem(
                    a.x * SCALE_FACTOR, a.y * SCALE_FACTOR,
                    b.x * SCALE_FACTOR, b.y * SCALE_FACTOR
                )
                line.setPen(pen)
                line.setZValue(0)
                self._scene.addItem(line)

        # Draw nodes
        for node in self._tree.nodes.values():
            item = NodeItem(node, self)
            self._scene.addItem(item)
            self._node_items[node.node_id] = item

        self._reset_view()

        if self._allocated_ids:
            self._apply_allocation()

    def _reset_view(self):
        if not self._tree:
            return
        scene_rect = self._scene.itemsBoundingRect()
        self._view.setSceneRect(scene_rect)
        self._view.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)

    # ------------------------------------------------------------------
    # Strategy simulation
    # ------------------------------------------------------------------

    def _find_origin(self) -> str:
        """Find the atlas start/origin node."""
        if not self._tree:
            return ""
        # Prefer explicit start-type node
        for nid, node in self._tree.nodes.items():
            if node.node_type == "start":
                return nid
        # Fall back to node with most connections (likely center)
        return max(self._tree.nodes.keys(),
                   key=lambda nid: len(self._tree.nodes[nid].connections))

    def _simulate_strategy(self, strategy: dict) -> set:
        """
        BFS from the origin node, prioritizing nodes matching strategy search_terms.
        Returns a set of up to total_points node_id strings.
        """
        if not self._tree:
            return set()

        available = strategy.get("total_points", 100)
        search_terms = strategy.get("search_terms", [])

        # Find all target nodes matching any search term
        target_ids = set()
        for term in search_terms:
            for node in self._tree.search(term):
                target_ids.add(node.node_id)

        origin = self._find_origin()
        if not origin:
            return set()

        parent: dict = {origin: None}
        queue = collections.deque([origin])
        allocated: set = {origin}

        # Phase 1: BFS, tracing paths to target nodes up to budget
        while queue and len(allocated) < available:
            nid = queue.popleft()
            node = self._tree.nodes.get(nid)
            if not node:
                continue
            # Sort neighbours: targets first
            neighbors = sorted(
                [c for c in node.connections if c not in parent and c in self._tree.nodes],
                key=lambda c: (0 if c in target_ids else 1)
            )
            for conn_id in neighbors:
                if conn_id not in parent:
                    parent[conn_id] = nid
                    queue.append(conn_id)
                    if conn_id in target_ids:
                        # Trace path back to origin
                        t = conn_id
                        while t is not None:
                            allocated.add(t)
                            t = parent.get(t)
                    if len(allocated) >= available:
                        break

        # Phase 2: fill remaining budget with BFS expansion
        if len(allocated) < available:
            expand = collections.deque(allocated)
            visited = set(allocated)
            while expand and len(allocated) < available:
                nid = expand.popleft()
                node = self._tree.nodes.get(nid)
                if not node:
                    continue
                neighbors = sorted(
                    [c for c in node.connections if c not in visited and c in self._tree.nodes],
                    key=lambda c: (0 if c in target_ids else 1)
                )
                for conn_id in neighbors:
                    if conn_id not in visited:
                        visited.add(conn_id)
                        allocated.add(conn_id)
                        expand.append(conn_id)
                        if len(allocated) >= available:
                            break

        return allocated

    def _preview_strategy(self):
        """Preview the selected strategy on the atlas tree."""
        if not self._tree:
            self._status.setText("Atlas tree not loaded yet — wait for load or download.")
            return

        strategy = self._meta_combo.currentData()
        if strategy is None:
            self._status.setText("Select a strategy first.")
            return

        nodes = self._simulate_strategy(strategy)
        self._active_strategy_nodes = nodes
        self._allocated_ids = nodes
        self._apply_allocation()
        self._respec_label.setText("")

        in_tree = sum(1 for n in nodes if n in self._node_items)
        self._status.setText(
            f"{strategy['name']} — {strategy.get('total_points', 100)} pts — "
            f"{in_tree} nodes highlighted"
        )

    def _clear_strategy(self):
        """Remove all strategy allocation highlights."""
        self._allocated_ids = set()
        self._active_strategy_nodes = set()
        for item in self._node_items.values():
            item.set_allocated(False)
        self._respec_label.setText("")
        if self._tree:
            self._status.setText(
                f"Atlas tree — {len(self._tree.nodes)} nodes, {len(self._tree.edges)} connections"
            )

    def _show_respec_cost(self):
        """Show how many respec points needed to swap from current to compare strategy."""
        if not self._tree:
            self._status.setText("Atlas tree not loaded yet.")
            return
        if not self._active_strategy_nodes:
            self._status.setText("Preview a strategy first (click Preview).")
            return

        strategy_b = self._compare_combo.currentData()
        if strategy_b is None:
            self._respec_label.setText("Select a comparison strategy.")
            return

        nodes_b = self._simulate_strategy(strategy_b)
        self._compare_strategy_nodes = nodes_b

        from modules import build_path
        cost = build_path.respec_cost(self._active_strategy_nodes, nodes_b)
        shared = len(self._active_strategy_nodes & nodes_b)

        strategy_a_name = (self._meta_combo.currentData() or {}).get("name", "Current")
        self._respec_label.setText(
            f"  {cost} respec pts  ({shared} pts shared)"
        )
        self._status.setText(
            f"Respec {strategy_a_name} → {strategy_b['name']}: {cost} respec points needed"
            f" ({shared} nodes kept)"
        )

    def _apply_allocation(self):
        """Apply allocation highlights to all loaded node items."""
        for nid, item in self._node_items.items():
            item.set_allocated(nid in self._allocated_ids)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _on_search(self, text: str):
        for item in self._node_items.values():
            item.clear_highlight()

        if not text or len(text) < 2:
            return

        results = self._tree.search(text) if self._tree else []
        for node in results:
            item = self._node_items.get(node.node_id)
            if item:
                item.highlight(SEARCH_COLOR)

        count = len(results)
        self._status.setText(f"{count} node{'s' if count != 1 else ''} matching '{text}'")

        if results:
            first = self._node_items.get(results[0].node_id)
            if first:
                self._view.centerOn(first)

    # ------------------------------------------------------------------
    # Tooltip / detail
    # ------------------------------------------------------------------

    def show_tooltip(self, node):
        lines = [
            f"<b style='color:#8ac840'>{node.name}</b>"
            f"  <span style='color:#8a7a65'>[{node.node_type}]</span>"
        ]
        for stat in node.stats[:6]:
            lines.append(f"• {stat}")
        if not node.stats:
            lines.append("<span style='color:#8a7a65'>No stats</span>")
        self._detail.setText("<br>".join(lines))

    def pin_node(self, node):
        self._pinned_node = node
        self.show_tooltip(node)
