"""
Main HUD window — transparent, always-on-top PyQt6 overlay.

Each panel (quest tracker, price check, crafting, etc.) is a dockable
widget that can be shown/hidden independently.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QLabel, QPushButton, QHBoxLayout, QFrame,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QTabBar

from ui.widgets.quest_panel import QuestPanel
from ui.widgets.price_panel import PricePanel
from ui.widgets.currency_panel import CurrencyPanel
from ui.widgets.crafting_panel import CraftingPanel
from ui.widgets.passive_tree_panel import PassiveTreePanel
from ui.widgets.map_panel import MapPanel
from ui.widgets.settings_panel import SettingsPanel
from ui.widgets.xp_panel import XPPanel
from ui.widgets.chaos_panel import ChaosPanel
from ui.widgets.notes_panel import NotesPanel
from ui.widgets.div_panel import DivPanel
from ui.widgets.atlas_panel import AtlasPanel
from ui.widgets.bestiary_panel import BestiaryPanel
from ui.widgets.heist_panel import HeistPanel
from ui.widgets.gem_panel import GemPanel


DARK_BG = "#1a1a2e"
PANEL_BG = "#16213e"
ACCENT   = "#e2b96f"   # PoE gold-ish
TEXT     = "#d4c5a9"
SUBTEXT  = "#8a7a65"


class HUD(QMainWindow):
    def __init__(self, state, quest_tracker, price_checker, currency_tracker, crafting,
                 map_overlay, xp_tracker, chaos_recipe, config,
                 div_tracker=None, atlas_tracker=None,
                 heist_planner=None, gem_planner=None,
                 oauth_manager=None, stash_api=None, character_api=None):
        super().__init__()
        self._state = state
        self._config = config
        self._oauth_manager = oauth_manager
        self._stash_api = stash_api
        self._character_api = character_api

        self._setup_window()
        self._build_ui(quest_tracker, price_checker, currency_tracker, crafting,
                       map_overlay, xp_tracker, chaos_recipe,
                       div_tracker, atlas_tracker, heist_planner, gem_planner)

        # Wire price checker results to price panel
        price_checker.on_result(self._price_panel.show_result)

        # Auto-refresh currency display every 60s
        timer = QTimer(self)
        timer.timeout.connect(self._refresh_currency)
        timer.start(60_000)

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _setup_window(self):
        self.setWindowTitle("PoELens")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(self._config.get("overlay_opacity", 0.92))

        # Position: top-right corner by default
        screen = self.screen().geometry() if self.screen() else None
        if screen:
            self.setGeometry(screen.width() - 420, 40, 400, 700)
        else:
            self.setGeometry(1500, 40, 400, 700)

    def _build_ui(self, quest_tracker, price_checker, currency_tracker, crafting,
                  map_overlay, xp_tracker, chaos_recipe,
                  div_tracker=None, atlas_tracker=None,
                  heist_planner=None, gem_planner=None):
        root = QWidget()
        root.setStyleSheet(f"""
            QWidget {{ background-color: {DARK_BG}; color: {TEXT}; font-family: 'Segoe UI'; font-size: 12px; border-radius: 8px; }}
            QTabWidget::pane {{ border: 1px solid #2a2a4a; background: {PANEL_BG}; }}
            QTabBar::tab {{ background: #0f0f23; color: {SUBTEXT}; padding: 5px 8px; border-radius: 4px 4px 0 0; }}
            QTabBar::tab:selected {{ background: {PANEL_BG}; color: {ACCENT}; border-bottom: 2px solid {ACCENT}; }}
            QTabBar::scroller {{ width: 20px; }}
            QTabBar QToolButton {{ background: #0f0f23; color: {SUBTEXT}; border: 1px solid #2a2a4a; }}
            QPushButton {{ background: #2a2a4a; color: {TEXT}; border: 1px solid #3a3a5a; border-radius: 4px; padding: 4px 10px; }}
            QPushButton:hover {{ background: #3a3a5a; }}
            QLabel {{ background: transparent; }}
        """)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Title bar
        title_bar = self._make_title_bar()
        layout.addWidget(title_bar)

        # Tab widget — one tab per module
        tabs = QTabWidget()
        tabs.tabBar().setUsesScrollButtons(True)
        tabs.tabBar().setExpanding(False)
        self._tabs = tabs

        self._quest_panel    = QuestPanel(quest_tracker)
        self._price_panel    = PricePanel()
        self._currency_panel = CurrencyPanel(
            currency_tracker,
            oauth_manager=self._oauth_manager,
            stash_api=self._stash_api,
            league=self._config.get("league", "Standard"),
        )
        self._crafting_panel = CraftingPanel(crafting)
        self._tree_panel     = PassiveTreePanel(
            quest_tracker,
            oauth_manager=self._oauth_manager,
            character_api=self._character_api,
            league=self._config.get("league", "Standard"),
        )
        self._map_panel      = MapPanel(map_overlay)
        self._xp_panel       = XPPanel(
            xp_tracker,
            oauth_manager=self._oauth_manager,
            league=self._config.get("league", "Standard"),
        )
        self._chaos_panel    = ChaosPanel(
            chaos_recipe,
            oauth_manager=self._oauth_manager,
            stash_api=self._stash_api,
            league=self._config.get("league", "Standard"),
        )
        self._notes_panel    = NotesPanel()
        self._settings_panel = SettingsPanel(
            self._config,
            on_opacity_change=self.setWindowOpacity,
            state=self._state,
        )
        self._div_panel = DivPanel(
            div_tracker,
            oauth_manager=self._oauth_manager,
            stash_api=self._stash_api,
            league=self._config.get("league", "Standard"),
        ) if div_tracker else QWidget()
        self._atlas_panel    = AtlasPanel(atlas_tracker) if atlas_tracker else QWidget()
        self._bestiary_panel = BestiaryPanel()
        self._heist_panel = HeistPanel(
            heist_planner,
            oauth_manager=self._oauth_manager,
            stash_api=self._stash_api,
            league=self._config.get("league", "Standard"),
        ) if heist_planner else QWidget()
        self._gem_panel = GemPanel(
            gem_planner,
            character_api=self._character_api,
            oauth_manager=self._oauth_manager,
            league=self._config.get("league", "Standard"),
        ) if gem_planner else QWidget()

        # Tab indices: Quests=0, Tree=1, Price=2, Currency=3, Crafting=4,
        #              Map=5, XP=6, Recipe=7, Notes=8, Settings=9,
        #              Divs=10, Atlas=11, Bestiary=12, Heist=13, Gems=14
        tabs.addTab(self._quest_panel,    "Quests")
        tabs.addTab(self._tree_panel,     "Tree")
        tabs.addTab(self._price_panel,    "Price")
        tabs.addTab(self._currency_panel, "Currency")
        tabs.addTab(self._crafting_panel, "Crafting")
        tabs.addTab(self._map_panel,      "Map")
        tabs.addTab(self._xp_panel,       "XP")
        tabs.addTab(self._chaos_panel,    "Recipe")
        tabs.addTab(self._notes_panel,    "Notes")
        tabs.addTab(self._settings_panel, "Settings")
        tabs.addTab(self._div_panel,      "Divs")
        tabs.addTab(self._atlas_panel,    "Atlas")
        tabs.addTab(self._bestiary_panel, "Bestiary")
        tabs.addTab(self._heist_panel,    "Heist")
        tabs.addTab(self._gem_panel,      "Gems")

        layout.addWidget(tabs)
        self.setCentralWidget(root)

    def _make_title_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(32)
        bar.setStyleSheet(f"background: {PANEL_BG}; border-radius: 6px;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 0, 8, 0)

        title = QLabel("PoELens")
        title.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 13px;")
        layout.addWidget(title)
        layout.addStretch()

        min_btn = QPushButton("—")
        min_btn.setFixedSize(24, 24)
        min_btn.clicked.connect(self.showMinimized)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("QPushButton { color: #e05050; } QPushButton:hover { background: #5a2020; }")
        close_btn.clicked.connect(self.hide)

        layout.addWidget(min_btn)
        layout.addWidget(close_btn)

        # Allow dragging the title bar to move the window
        bar._drag_pos = None
        def mousePressEvent(e):
            if e.button() == Qt.MouseButton.LeftButton:
                bar._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
        def mouseMoveEvent(e):
            if bar._drag_pos and e.buttons() == Qt.MouseButton.LeftButton:
                self.move(e.globalPosition().toPoint() - bar._drag_pos)
        bar.mousePressEvent = mousePressEvent
        bar.mouseMoveEvent = mouseMoveEvent

        return bar

    # ------------------------------------------------------------------
    # Public actions (called by hotkeys)
    # ------------------------------------------------------------------

    def toggle(self):
        self.hide() if self.isVisible() else self.show()

    def show_passive_tree(self):
        self.show()
        self._tabs.setCurrentIndex(1)  # Tree tab

    def show_crafting(self):
        self.show()
        self._tabs.setCurrentIndex(4)  # Crafting=4

    def show_map(self):
        self.show()
        self._tabs.setCurrentIndex(5)  # Map=5

    def on_currency_clipboard(self, currency_name: str, count: int):
        """Called when a currency stack is Ctrl+C'd in-game."""
        self._currency_panel.update_from_clipboard_scan(currency_name, count)

    def _refresh_currency(self):
        self._currency_panel.refresh()
