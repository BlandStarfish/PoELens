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

import config as cfg

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
from ui.widgets.map_stash_panel import MapStashPanel
from ui.widgets.expedition_panel import ExpeditionPanel
from ui.widgets.currency_flip_panel import CurrencyFlipPanel
from ui.widgets.lab_panel import LabPanel


DARK_BG = "#1a1a2e"
PANEL_BG = "#16213e"
ACCENT   = "#e2b96f"   # PoE gold-ish
TEXT     = "#d4c5a9"
SUBTEXT  = "#8a7a65"

# Outer tab group indices
_GRP_CHARACTER = 0
_GRP_LOOT      = 1
_GRP_ENDGAME   = 2
_GRP_INFO      = 3

# Inner tab indices within each group
_CHAR_QUESTS = 0
_CHAR_TREE   = 1
_CHAR_XP     = 2
_CHAR_NOTES  = 3
_CHAR_LAB    = 4

_LOOT_PRICE    = 0
_LOOT_CURRENCY = 1
_LOOT_RECIPE   = 2
_LOOT_DIVS     = 3
_LOOT_FLIP     = 4

_END_MAP       = 0
_END_ATLAS     = 1
_END_CRAFT     = 2
_END_HEIST     = 3
_END_GEMS      = 4
_END_MAP_STASH = 5

_INFO_BESTIARY    = 0
_INFO_EXPEDITION  = 1
_INFO_SETTINGS    = 2


class HUD(QMainWindow):
    def __init__(self, state, quest_tracker, price_checker, currency_tracker, crafting,
                 map_overlay, xp_tracker, chaos_recipe, config,
                 div_tracker=None, atlas_tracker=None,
                 heist_planner=None, gem_planner=None, map_scanner=None,
                 lab_tracker=None, currency_flip=None,
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
                       div_tracker, atlas_tracker, heist_planner, gem_planner, map_scanner,
                       lab_tracker, currency_flip)

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
                  heist_planner=None, gem_planner=None, map_scanner=None,
                  lab_tracker=None, currency_flip=None):
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

        # Build all panels first, then wire into grouped tab structure
        league = self._config.get("league", "Standard")
        auto_scan = self._config.get("auto_scan_minutes", 0)

        self._quest_panel    = QuestPanel(quest_tracker)
        self._price_panel    = PricePanel()
        self._currency_panel = CurrencyPanel(
            currency_tracker,
            oauth_manager=self._oauth_manager,
            stash_api=self._stash_api,
            league=league,
        )
        self._crafting_panel = CraftingPanel(crafting)
        self._tree_panel     = PassiveTreePanel(
            quest_tracker,
            oauth_manager=self._oauth_manager,
            character_api=self._character_api,
            league=league,
        )
        self._map_panel      = MapPanel(map_overlay)
        self._xp_panel       = XPPanel(
            xp_tracker,
            oauth_manager=self._oauth_manager,
            league=league,
        )
        self._chaos_panel    = ChaosPanel(
            chaos_recipe,
            oauth_manager=self._oauth_manager,
            stash_api=self._stash_api,
            league=league,
            auto_scan_minutes=auto_scan,
        )
        self._notes_panel    = NotesPanel()
        self._settings_panel = SettingsPanel(
            self._config,
            on_opacity_change=self.setWindowOpacity,
            on_auto_scan_change=self._apply_auto_scan,
            state=self._state,
        )
        self._div_panel = DivPanel(
            div_tracker,
            oauth_manager=self._oauth_manager,
            stash_api=self._stash_api,
            league=league,
            auto_scan_minutes=auto_scan,
        ) if div_tracker else QWidget()
        self._atlas_panel    = AtlasPanel(atlas_tracker) if atlas_tracker else QWidget()
        self._bestiary_panel = BestiaryPanel()
        self._heist_panel = HeistPanel(
            heist_planner,
            oauth_manager=self._oauth_manager,
            stash_api=self._stash_api,
            league=league,
        ) if heist_planner else QWidget()
        self._gem_panel = GemPanel(
            gem_planner,
            character_api=self._character_api,
            oauth_manager=self._oauth_manager,
            league=league,
        ) if gem_planner else QWidget()
        self._map_stash_panel = MapStashPanel(
            map_scanner,
            oauth_manager=self._oauth_manager,
            stash_api=self._stash_api,
            league=league,
        ) if map_scanner else QWidget()
        self._expedition_panel   = ExpeditionPanel()
        self._currency_flip_panel = CurrencyFlipPanel(currency_flip) if currency_flip else QWidget()
        self._lab_panel = LabPanel(lab_tracker) if lab_tracker else QWidget()

        # ── Outer tab widget (4 categories, evenly spaced) ─────────────
        outer_tabs = QTabWidget()
        outer_tabs.tabBar().setExpanding(True)
        outer_tabs.setStyleSheet(f"""
            QTabBar::tab {{ font-size: 11px; font-weight: bold; padding: 6px 10px; }}
            QTabBar::tab:selected {{ color: {ACCENT}; border-bottom: 2px solid {ACCENT}; }}
        """)
        self._tabs = outer_tabs
        self._inner_tabs: list[QTabWidget] = []

        def _make_inner() -> QTabWidget:
            t = QTabWidget()
            t.tabBar().setUsesScrollButtons(True)
            t.tabBar().setExpanding(False)
            return t

        # Character group: Quests · Tree · XP · Notes · Lab
        char_tabs = _make_inner()
        char_tabs.addTab(self._quest_panel, "Quests")    # _CHAR_QUESTS = 0
        char_tabs.addTab(self._tree_panel,  "Tree")      # _CHAR_TREE   = 1
        char_tabs.addTab(self._xp_panel,    "XP")        # _CHAR_XP     = 2
        char_tabs.addTab(self._notes_panel, "Notes")     # _CHAR_NOTES  = 3
        char_tabs.addTab(self._lab_panel,   "Lab")       # _CHAR_LAB    = 4
        self._inner_tabs.append(char_tabs)
        outer_tabs.addTab(char_tabs, "Character")        # _GRP_CHARACTER = 0

        # Loot group: Price · Currency · Recipe · Divs · Flip
        loot_tabs = _make_inner()
        loot_tabs.addTab(self._price_panel,         "Price")    # _LOOT_PRICE    = 0
        loot_tabs.addTab(self._currency_panel,      "Currency") # _LOOT_CURRENCY = 1
        loot_tabs.addTab(self._chaos_panel,         "Recipe")   # _LOOT_RECIPE   = 2
        loot_tabs.addTab(self._div_panel,           "Divs")     # _LOOT_DIVS     = 3
        loot_tabs.addTab(self._currency_flip_panel, "Flip")     # _LOOT_FLIP     = 4
        self._inner_tabs.append(loot_tabs)
        outer_tabs.addTab(loot_tabs, "Loot")                    # _GRP_LOOT      = 1

        # Endgame group: Map · Atlas · Crafting · Heist · Gems
        end_tabs = _make_inner()
        end_tabs.addTab(self._map_panel,        "Map")       # _END_MAP       = 0
        end_tabs.addTab(self._atlas_panel,      "Atlas")     # _END_ATLAS     = 1
        end_tabs.addTab(self._crafting_panel,   "Crafting")  # _END_CRAFT     = 2
        end_tabs.addTab(self._heist_panel,      "Heist")     # _END_HEIST     = 3
        end_tabs.addTab(self._gem_panel,        "Gems")      # _END_GEMS      = 4
        end_tabs.addTab(self._map_stash_panel,  "MapStash")  # _END_MAP_STASH = 5
        self._inner_tabs.append(end_tabs)
        outer_tabs.addTab(end_tabs, "Endgame")             # _GRP_ENDGAME   = 2

        # Info group: Bestiary · Expedition · Settings
        info_tabs = _make_inner()
        info_tabs.addTab(self._bestiary_panel,   "Bestiary")   # _INFO_BESTIARY   = 0
        info_tabs.addTab(self._expedition_panel, "Expedition") # _INFO_EXPEDITION = 1
        info_tabs.addTab(self._settings_panel,   "Settings")   # _INFO_SETTINGS   = 2
        self._inner_tabs.append(info_tabs)
        outer_tabs.addTab(info_tabs, "Info")                   # _GRP_INFO        = 3

        # Restore last active tabs from config (saved on tab-change)
        outer_tabs.setCurrentIndex(self._config.get("last_group", 0))
        for i, inner in enumerate(self._inner_tabs):
            inner.setCurrentIndex(self._config.get(f"last_inner_{i}", 0))

        # Persist tab selection whenever user navigates
        outer_tabs.currentChanged.connect(self._save_last_tab)
        for inner in self._inner_tabs:
            inner.currentChanged.connect(self._save_last_tab)

        layout.addWidget(outer_tabs)
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

    def _show_tab(self, group: int, inner: int):
        """Navigate to a specific panel by group and inner tab index."""
        self.show()
        self._tabs.setCurrentIndex(group)
        self._inner_tabs[group].setCurrentIndex(inner)

    def show_passive_tree(self):
        self._show_tab(_GRP_CHARACTER, _CHAR_TREE)

    def show_crafting(self):
        self._show_tab(_GRP_ENDGAME, _END_CRAFT)

    def show_map(self):
        self._show_tab(_GRP_ENDGAME, _END_MAP)

    def on_currency_clipboard(self, currency_name: str, count: int):
        """Called when a currency stack is Ctrl+C'd in-game."""
        self._currency_panel.update_from_clipboard_scan(currency_name, count)

    def _apply_auto_scan(self, minutes: int):
        """Apply a new auto-scan interval to both Div Card and Chaos Recipe panels immediately."""
        if hasattr(self._chaos_panel, "set_auto_scan_minutes"):
            self._chaos_panel.set_auto_scan_minutes(minutes)
        if hasattr(self._div_panel, "set_auto_scan_minutes"):
            self._div_panel.set_auto_scan_minutes(minutes)

    def _save_last_tab(self):
        """Persist current outer/inner tab selection to config so it survives restarts."""
        updates = {"last_group": self._tabs.currentIndex()}
        for i, inner in enumerate(self._inner_tabs):
            updates[f"last_inner_{i}"] = inner.currentIndex()
        cfg.save(updates)

    def _refresh_currency(self):
        self._currency_panel.refresh()
