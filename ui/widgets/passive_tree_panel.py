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
    QProgressBar, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QPen, QBrush, QColor, QFont, QTransform, QWheelEvent

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

EDGE_COLOR    = QColor("#2a2a4a")
HIGHLIGHT_COLOR = QColor("#e2b96f")
SEARCH_COLOR  = QColor("#5cba6e")
QUEST_COLOR   = QColor("#4ae8c8")

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
        fill, border = NODE_COLORS.get(self._node.node_type, ("#3a3a5a", "#6a6aaa"))
        # Restore original pen unless highlighted by search
        if self.data(0) != "search":
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
        fill, border = NODE_COLORS.get(self._node.node_type, ("#3a3a5a", "#6a6aaa"))
        self.setPen(QPen(QColor(border), 1.5))
        self.setData(0, None)
        self.setZValue(1)


# ─────────────────────────────────────────────────────────────────────────────
# Main panel
# ─────────────────────────────────────────────────────────────────────────────

class PassiveTreePanel(QWidget):
    def __init__(self, quest_tracker=None):
        super().__init__()
        self._quest_tracker = quest_tracker
        self._tree = None
        self._node_items: dict[str, NodeItem] = {}
        self._pinned_node = None
        self._build_ui()
        self._start_loading()
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
        self.setRenderHint(self.renderHints().__class__.Antialiasing, True)
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
