"""
Passive tree viewer panel.

Renders the full PoE passive tree using QGraphicsView:
  - Pan: click + drag
  - Zoom: scroll wheel
  - Hover: shows node tooltip
  - Click: pins node detail panel
  - Search bar: highlights matching nodes
  - Highlights quest reward nodes (from quest_tracker)

Node color scheme:
  keystone    — gold border, large
  notable     — silver border, medium
  normal      — small circle, muted
  class_start — large, class-colored
  jewel       — teal diamond
  mastery     — icon placeholder
  ascendancy  — purple tint
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
    QGraphicsLineItem, QGraphicsTextItem, QGraphicsItem,
    QProgressBar, QFrame, QSizePolicy, QComboBox, QSpinBox,
)
import threading

from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QPen, QBrush, QColor, QFont, QTransform, QWheelEvent, QPainter

# ─────────────────────────────────────────────────────────────────────────────
# Colors
# ─────────────────────────────────────────────────────────────────────────────

NODE_COLORS = {
    "normal":      ("#3a3a5a", "#6a6aaa"),      # (fill, border)
    "notable":     ("#2a2a1a", "#c8a84b"),
    "keystone":    ("#1a1a0a", "#e2b96f"),
    "class_start": ("#0a0a2a", "#4a8ae8"),
    "ascendancy":  ("#2a0a2a", "#9a4ae8"),
    "jewel":       ("#0a2a2a", "#4ae8c8"),
    "mastery":     ("#1a0a0a", "#e84a4a"),
}

NODE_RADII = {
    "normal":      5,
    "notable":     8,
    "keystone":    12,
    "class_start": 14,
    "ascendancy":  7,
    "jewel":       8,
    "mastery":     6,
}

EDGE_COLOR      = QColor("#2a2a4a")
HIGHLIGHT_COLOR = QColor("#e2b96f")
SEARCH_COLOR    = QColor("#5cba6e")
QUEST_COLOR     = QColor("#4ae8c8")
ALLOCATED_COLOR = QColor("#ffd700")   # bright gold — player's own allocated nodes

SCALE_FACTOR = 0.04   # tree coords ~28000 wide → ~1120 px scene

# ─────────────────────────────────────────────────────────────────────────────
# Background loader thread
# ─────────────────────────────────────────────────────────────────────────────

class TreeLoader(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(object)   # PassiveTree
    error    = pyqtSignal(str)

    def run(self):
        try:
            from modules.passive_tree import PassiveTree
            tree = PassiveTree.load_or_download(callback=lambda m: self.progress.emit(m))
            self.finished.emit(tree)
        except Exception as e:
            self.error.emit(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Custom graphics items
# ─────────────────────────────────────────────────────────────────────────────

class NodeItem(QGraphicsEllipseItem):
    def __init__(self, node, panel):
        r = NODE_RADII.get(node.node_type, 5)
        super().__init__(-r, -r, r * 2, r * 2)
        self._node = node
        self._panel = panel
        self._base_r = r
        self._allocated = False   # True when this node is in the loaded build

        fill, border = NODE_COLORS.get(node.node_type, ("#3a3a5a", "#6a6aaa"))
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
        # Priority: search highlight > allocated > default
        if self.data(0) == "search":
            pass   # keep search color
        elif self._allocated:
            self.setPen(QPen(ALLOCATED_COLOR, 3))
        else:
            fill, border = NODE_COLORS.get(self._node.node_type, ("#3a3a5a", "#6a6aaa"))
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
        """Clear search highlight. Does NOT affect allocation state."""
        self.setData(0, None)
        if self._allocated:
            self.setPen(QPen(ALLOCATED_COLOR, 3))
            self.setZValue(3)
        else:
            fill, border = NODE_COLORS.get(self._node.node_type, ("#3a3a5a", "#6a6aaa"))
            self.setPen(QPen(QColor(border), 1.5))
            self.setZValue(1)

    def set_allocated(self, allocated: bool):
        """Set or clear build allocation highlight (player's own nodes)."""
        self._allocated = allocated
        if allocated:
            if self.data(0) != "search":
                self.setPen(QPen(ALLOCATED_COLOR, 3))
            self.setZValue(3)
        else:
            if self.data(0) == "search":
                self.setZValue(2)
            else:
                fill, border = NODE_COLORS.get(self._node.node_type, ("#3a3a5a", "#6a6aaa"))
                self.setPen(QPen(QColor(border), 1.5))
                self.setZValue(1)


# ─────────────────────────────────────────────────────────────────────────────
# Meta build loader
# ─────────────────────────────────────────────────────────────────────────────

def _load_meta_builds() -> list:
    """Load meta build definitions from data/meta_builds.json."""
    import json, os
    path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "meta_builds.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)["builds"]
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Main panel
# ─────────────────────────────────────────────────────────────────────────────

class PassiveTreePanel(QWidget):
    # Signals for thread-safe UI updates from background character API calls
    _char_sync_done  = pyqtSignal(object, str)   # (set[str] node_ids, char_name)
    _char_sync_error = pyqtSignal(str)

    def __init__(self, quest_tracker=None, oauth_manager=None,
                 character_api=None, league="Standard"):
        super().__init__()
        self._quest_tracker = quest_tracker
        self._oauth = oauth_manager
        self._character_api = character_api
        self._league = league
        self._tree = None
        self._node_items: dict[str, NodeItem] = {}
        self._pinned_node = None
        self._allocated_ids: set[str] = set()   # node IDs from loaded build code
        self._meta_builds = _load_meta_builds()
        self._active_build_nodes: set[str] = set()   # currently previewed build nodes
        self._compare_build_nodes: set[str] = set()  # comparison build nodes
        self._build_ui()
        self._start_loading()

        self._char_sync_done.connect(self._on_char_sync_done)
        self._char_sync_error.connect(self._on_char_sync_error)

        if quest_tracker:
            quest_tracker.on_update(lambda _: self._refresh_quest_summary())
            self._refresh_quest_summary()

    # ------------------------------------------------------------------
    # UI layout
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # ── Quest point summary ──
        self._quest_summary = QLabel("Quest passive points: —")
        self._quest_summary.setStyleSheet(
            "color: #4ae8c8; font-size: 11px; font-weight: bold;"
            " background: #0a1a1a; border-radius: 3px; padding: 3px 6px;"
        )
        layout.addWidget(self._quest_summary)

        # ── Top bar ──
        top = QHBoxLayout()

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search nodes (e.g. 'life', 'crit', 'mana')")
        self._search.setStyleSheet(
            "background: #0f0f23; color: #d4c5a9; border: 1px solid #2a2a4a;"
            " border-radius: 3px; padding: 3px; font-size: 11px;"
        )
        self._search.textChanged.connect(self._on_search)
        top.addWidget(self._search, 1)

        reset_btn = QPushButton("Reset View")
        reset_btn.setFixedWidth(80)
        reset_btn.clicked.connect(self._reset_view)
        top.addWidget(reset_btn)

        layout.addLayout(top)

        # ── Build import ──
        build_row = QHBoxLayout()
        self._build_input = QLineEdit()
        self._build_input.setPlaceholderText(
            "Paste PoE tree URL or Path of Building code to show your build"
        )
        self._build_input.setStyleSheet(
            "background: #0f0f23; color: #d4c5a9; border: 1px solid #2a2a4a;"
            " border-radius: 3px; padding: 3px; font-size: 11px;"
        )
        build_row.addWidget(self._build_input, 1)

        load_build_btn = QPushButton("Load")
        load_build_btn.setFixedWidth(52)
        load_build_btn.setStyleSheet(
            "QPushButton { color: #ffd700; font-size: 11px; padding: 3px 6px; }"
        )
        load_build_btn.clicked.connect(self._load_build)
        build_row.addWidget(load_build_btn)

        clear_build_btn = QPushButton("Clear")
        clear_build_btn.setFixedWidth(52)
        clear_build_btn.setStyleSheet(
            "QPushButton { font-size: 11px; padding: 3px 6px; }"
        )
        clear_build_btn.clicked.connect(self._clear_build)
        build_row.addWidget(clear_build_btn)

        layout.addLayout(build_row)

        # ── PoE Account character sync (only when OAuth is configured) ──
        if self._oauth and self._oauth.is_configured:
            self._build_char_sync_row(layout)

        # ── Meta build preview ──
        self._build_meta_row(layout)

        # ── Progress / status ──
        self._status = QLabel("Loading passive tree data...")
        self._status.setStyleSheet("color: #8a7a65; font-size: 11px;")
        layout.addWidget(self._status)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)   # indeterminate
        self._progress.setFixedHeight(4)
        self._progress.setStyleSheet(
            "QProgressBar { background: #1a1a2e; border: none; }"
            "QProgressBar::chunk { background: #e2b96f; }"
        )
        layout.addWidget(self._progress)

        # ── Graphics view ──
        self._scene = QGraphicsScene()
        self._scene.setBackgroundBrush(QBrush(QColor("#0d0d1a")))

        self._view = TreeView(self._scene)
        self._view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._view, 1)

        # ── Node detail panel ──
        self._detail = QLabel("Hover or click a node to see details.")
        self._detail.setWordWrap(True)
        self._detail.setFixedHeight(80)
        self._detail.setStyleSheet(
            "background: #0f0f23; color: #d4c5a9; font-size: 11px;"
            " border: 1px solid #2a2a4a; border-radius: 4px; padding: 6px;"
        )
        layout.addWidget(self._detail)

    def _build_char_sync_row(self, layout):
        """Add the 'Sync from PoE Account' row (only when OAuth is configured)."""
        sync_row = QHBoxLayout()
        sync_row.setSpacing(4)

        self._sync_status = QLabel("")
        self._sync_status.setStyleSheet(
            "color: #8a7a65; font-size: 10px;"
        )
        sync_row.addWidget(self._sync_status, 1)

        self._sync_btn = QPushButton("↺ Sync from PoE Account")
        self._sync_btn.setStyleSheet(
            "QPushButton { color: #ffd700; font-size: 10px; padding: 2px 6px; }"
            "QPushButton:disabled { color: #4a4a4a; }"
        )
        self._sync_btn.clicked.connect(self._sync_from_account)
        sync_row.addWidget(self._sync_btn)

        layout.addLayout(sync_row)
        self._update_sync_status()

    def _build_meta_row(self, layout):
        """Add the meta build preview row."""
        row1 = QHBoxLayout()
        row1.setSpacing(4)

        meta_lbl = QLabel("Meta:")
        meta_lbl.setStyleSheet("color: #8a7a65; font-size: 10px;")
        meta_lbl.setFixedWidth(32)
        row1.addWidget(meta_lbl)

        self._meta_combo = QComboBox()
        self._meta_combo.setStyleSheet(
            "QComboBox { background: #0f0f23; color: #d4c5a9; border: 1px solid #2a2a4a;"
            " border-radius: 3px; padding: 2px 4px; font-size: 10px; }"
            "QComboBox::drop-down { border: none; }"
        )
        self._meta_combo.addItem("— select build —", None)
        for build in self._meta_builds:
            self._meta_combo.addItem(build["name"], build)
        row1.addWidget(self._meta_combo, 2)

        lv_lbl = QLabel("Lv:")
        lv_lbl.setStyleSheet("color: #8a7a65; font-size: 10px;")
        lv_lbl.setFixedWidth(16)
        row1.addWidget(lv_lbl)

        self._meta_level = QSpinBox()
        self._meta_level.setRange(1, 100)
        self._meta_level.setValue(90)
        self._meta_level.setFixedWidth(46)
        self._meta_level.setStyleSheet(
            "QSpinBox { background: #0f0f23; color: #ffd700; border: 1px solid #2a2a4a;"
            " border-radius: 3px; padding: 2px; font-size: 10px; }"
        )
        row1.addWidget(self._meta_level)

        preview_btn = QPushButton("Preview")
        preview_btn.setFixedWidth(56)
        preview_btn.setStyleSheet(
            "QPushButton { color: #ffd700; font-size: 10px; padding: 2px 4px; }"
        )
        preview_btn.clicked.connect(self._preview_meta_build)
        row1.addWidget(preview_btn)
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
        self._compare_combo.addItem("— compare build —", None)
        for build in self._meta_builds:
            self._compare_combo.addItem(build["name"], build)
        row2.addWidget(self._compare_combo, 2)

        compare_btn = QPushButton("Respec Cost")
        compare_btn.setFixedWidth(80)
        compare_btn.setStyleSheet(
            "QPushButton { color: #4ae8c8; font-size: 10px; padding: 2px 4px; }"
        )
        compare_btn.clicked.connect(self._show_respec_cost)
        row2.addWidget(compare_btn)

        self._respec_label = QLabel("")
        self._respec_label.setStyleSheet("color: #e05050; font-size: 10px;")
        row2.addWidget(self._respec_label, 1)
        layout.addLayout(row2)

    def _preview_meta_build(self):
        """Preview the selected meta build on the tree."""
        if not self._tree:
            self._status.setText("Tree not loaded yet — wait for load to complete.")
            return

        build = self._meta_combo.currentData()
        if build is None:
            self._status.setText("Select a meta build first.")
            return

        from modules import build_path
        level = self._meta_level.value()
        available = build_path.calc_available_points(level)

        nodes = build_path.simulate_build(
            self._tree,
            build["class_index"],
            build.get("keystones", []),
            build.get("notable_search", []),
            build.get("fill_search", []),
            available,
        )

        self._active_build_nodes = nodes
        self._allocated_ids = nodes
        self._apply_allocation()
        self._build_input.clear()
        self._respec_label.setText("")

        in_tree = sum(1 for n in nodes if n in self._node_items)
        self._status.setText(
            f"{build['name']} — Lv{level} ({available} pts) — "
            f"{in_tree} nodes highlighted"
        )

    def _show_respec_cost(self):
        """Show how many regret orbs are needed to swap from current to compare build."""
        if not self._tree:
            self._status.setText("Tree not loaded yet.")
            return
        if not self._active_build_nodes:
            self._status.setText("Preview a build first (click Preview).")
            return

        build_b = self._compare_combo.currentData()
        if build_b is None:
            self._respec_label.setText("Select a comparison build.")
            return

        from modules import build_path
        level = self._meta_level.value()
        available = build_path.calc_available_points(level)

        nodes_b = build_path.simulate_build(
            self._tree,
            build_b["class_index"],
            build_b.get("keystones", []),
            build_b.get("notable_search", []),
            build_b.get("fill_search", []),
            available,
        )

        self._compare_build_nodes = nodes_b
        cost = build_path.respec_cost(self._active_build_nodes, nodes_b)
        shared = len(self._active_build_nodes & nodes_b)

        build_a_name = (self._meta_combo.currentData() or {}).get("name", "Current")
        self._respec_label.setText(
            f"  {cost} regret orbs  ({shared} pts shared)"
        )
        self._status.setText(
            f"Respec {build_a_name} → {build_b['name']}: {cost} Regret Orbs needed"
            f" ({shared} nodes kept)"
        )

    def _update_sync_status(self):
        """Reflect current OAuth auth state in the sync row label."""
        if not hasattr(self, "_sync_status"):
            return
        if self._oauth and self._oauth.is_authenticated:
            name = self._oauth.account_name or "account"
            self._sync_status.setText(f"PoE: {name}")
            self._sync_btn.setEnabled(True)
        else:
            self._sync_status.setText("Not connected — connect in Currency tab first")
            self._sync_btn.setEnabled(False)

    def _sync_from_account(self):
        """Fetch the best character's passive nodes in a background thread."""
        if not self._character_api or not self._oauth or not self._oauth.is_authenticated:
            self._sync_status.setText("Not connected — use Currency tab to connect.")
            return

        self._sync_btn.setEnabled(False)
        self._sync_btn.setText("Syncing...")

        def _fetch():
            try:
                char = self._character_api.get_best_character(self._league)
                if not char:
                    self._char_sync_error.emit(
                        "No characters found in this league."
                    )
                    return
                name = char.get("name", "")
                hashes = self._character_api.get_passive_hashes(name)
                if hashes is None:
                    self._char_sync_error.emit(
                        "Character data unavailable — re-connect in Currency tab "
                        "to authorize character access."
                    )
                    return
                self._char_sync_done.emit(hashes, name)
            except Exception as e:
                self._char_sync_error.emit(str(e))

        threading.Thread(target=_fetch, daemon=True).start()

    @pyqtSlot(object, str)
    def _on_char_sync_done(self, node_ids: set, char_name: str):
        self._allocated_ids = node_ids
        self._apply_allocation()
        self._sync_btn.setEnabled(True)
        self._sync_btn.setText("↺ Sync from PoE Account")
        in_tree = sum(1 for nid in node_ids if nid in self._node_items)
        self._sync_status.setText(
            f"Loaded: {char_name} ({in_tree} nodes)"
        )
        # Clear the manual build input to avoid confusion with the synced build
        self._build_input.clear()

    @pyqtSlot(str)
    def _on_char_sync_error(self, message: str):
        self._sync_btn.setEnabled(True)
        self._sync_btn.setText("↺ Sync from PoE Account")
        self._sync_status.setText(f"Error: {message[:80]}")

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _start_loading(self):
        self._loader = TreeLoader()
        self._loader.progress.connect(self._on_load_progress)
        self._loader.finished.connect(self._on_load_done)
        self._loader.error.connect(self._on_load_error)
        self._loader.start()

    @pyqtSlot(str)
    def _on_load_progress(self, msg: str):
        self._status.setText(msg)

    @pyqtSlot(object)
    def _on_load_done(self, tree):
        self._tree = tree
        self._progress.hide()
        self._status.setText(
            f"Tree loaded — {len(tree.nodes)} nodes, {len(tree.edges)} connections"
        )
        self._render_tree()

    @pyqtSlot(str)
    def _on_load_error(self, msg: str):
        self._progress.hide()
        self._status.setText(f"Error loading tree: {msg}")
        self._status.setStyleSheet("color: #e05050; font-size: 11px;")

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
        quest_node_ids = self._get_quest_node_ids()
        for node in self._tree.nodes.values():
            item = NodeItem(node, self)
            self._scene.addItem(item)
            self._node_items[node.node_id] = item
            if node.node_id in quest_node_ids:
                item.highlight(QUEST_COLOR)

        self._reset_view()

        # Reapply any previously loaded build allocation after tree re-render
        if self._allocated_ids:
            self._apply_allocation()

    def _refresh_quest_summary(self):
        """Update the quest passive points banner from live quest tracker data."""
        if not self._quest_tracker:
            return
        totals = self._quest_tracker.get_point_totals()
        earned   = totals["earned"]
        total    = totals["total_available"]
        net      = totals["net"]
        remaining = totals["remaining"]
        deducted = totals["deducted"]

        if deducted:
            self._quest_summary.setText(
                f"Quest passive points: {net} net  "
                f"({earned} earned − {deducted} deducted)  |  {remaining} still available"
            )
        else:
            self._quest_summary.setText(
                f"Quest passive points: {earned} / {total} collected  |  {remaining} still available"
            )

    def _get_quest_node_ids(self) -> set:
        """
        In PoE, quest passive point rewards give freely-allocatable unspent points —
        they do not unlock specific named nodes on the tree. There is therefore no
        node-to-quest mapping to highlight. The quest summary banner above the tree
        is the correct integration point.
        """
        return set()

    # ------------------------------------------------------------------
    # Build import (PoE tree URL / Path of Building code)
    # ------------------------------------------------------------------

    def _load_build(self):
        """Parse the pasted build code and highlight the player's allocated nodes."""
        from modules.passive_tree import PassiveTree
        code = self._build_input.text().strip()
        if not code:
            self._status.setText("Paste a PoE tree URL or Path of Building code first.")
            return

        ids = PassiveTree.parse_tree_url(code)
        if not ids:
            self._status.setText(
                "Could not parse build code — paste the full URL or the base64 code."
            )
            return

        self._allocated_ids = ids
        self._apply_allocation()

        in_tree = sum(1 for nid in ids if nid in self._node_items)
        self._status.setText(
            f"Build loaded — {in_tree} nodes highlighted  "
            f"({len(ids)} in code, {len(ids) - in_tree} not in current tree data)"
        )

    def _clear_build(self):
        """Remove all build allocation highlights."""
        self._allocated_ids = set()
        for item in self._node_items.values():
            item.set_allocated(False)
        self._build_input.clear()
        if self._tree:
            self._status.setText(
                f"Build cleared — {len(self._tree.nodes)} nodes, {len(self._tree.edges)} connections"
            )

    def _apply_allocation(self):
        """Apply allocation highlights to all loaded node items."""
        for nid, item in self._node_items.items():
            item.set_allocated(nid in self._allocated_ids)

    def _reset_view(self):
        if not self._tree:
            return
        scene_rect = self._scene.itemsBoundingRect()
        self._view.setSceneRect(scene_rect)
        self._view.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _on_search(self, text: str):
        # Clear existing highlights first
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

        # Auto-center on first result
        if results:
            first = self._node_items.get(results[0].node_id)
            if first:
                self._view.centerOn(first)

    # ------------------------------------------------------------------
    # Tooltip / detail
    # ------------------------------------------------------------------

    def show_tooltip(self, node):
        lines = [f"<b style='color:#e2b96f'>{node.name}</b>  <span style='color:#8a7a65'>[{node.node_type}]</span>"]
        if node.ascendancy_name:
            lines.append(f"<span style='color:#9a4ae8'>{node.ascendancy_name}</span>")
        for stat in node.stats[:6]:
            lines.append(f"• {stat}")
        self._detail.setText("<br>".join(lines))

    def pin_node(self, node):
        self._pinned_node = node
        self.show_tooltip(node)


# ─────────────────────────────────────────────────────────────────────────────
# Custom view with pan + zoom
# ─────────────────────────────────────────────────────────────────────────────

class TreeView(QGraphicsView):
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
