═══════════════════════════════════════════════════════════════
SESSION: 2026-03-23  (First Run)
═══════════════════════════════════════════════════════════════

## ORIENTATION SUMMARY
First session. No prior session notes existed. Full codebase read from scratch.
Project is a PyQt6 TOS-compliant PoE overlay with 5 tabs: Quests, Passive Tree,
Price Check, Currency/hr, Crafting. All core modules exist and are wired together.
The installer (tkinter GUI → .exe) is complete. Auto-updater and crash reporter exist.

## ASSESSMENT GRADES

| Module               | Completeness | Quality | Vision Alignment |
|----------------------|-------------|---------|-----------------|
| Quest Tracker        |     8/10     |  8/10   |      9/10       |
| Passive Tree Viewer  |     7/10     |  8/10   |      7/10       |
| Price Checker        |     8/10     |  7/10   |      9/10       |
| Currency Tracker     |     6/10     |  8/10   |      7/10       |
| Crafting System      |     7/10     |  8/10   |      8/10       |
| Core Infrastructure  |     9/10     |  8/10   |      9/10       |
| Installer / GUI      |     8/10     |  7/10   |      9/10       |
| Map Overlay          |     1/10     |   N/A   |      1/10       |

Items below 6: Map Overlay (1/1/1) — not started.

## SMOKE TEST FINDINGS

### Phase 1B — Logic & Structure Issues

1. core/updater.py:163-165 — CRITICAL BUG: QMetaObject.invokeMethod(app, "_show_update_dialog")
   calls a method that was never defined on QApplication. The update detection background
   thread runs and finds updates but the dialog is never shown. Complete silent failure.

2. ui/hud.py:156 — BUG: show_crafting() called setCurrentIndex(3) but Crafting is tab 4
   (Quests=0, Tree=1, Price=2, Currency=3, Crafting=4). Pressing the crafting hotkey
   would navigate to the Currency tab instead.

3. core/client_log.py:73-84 — RESOURCE LEAK: File handle opened in _tail() is never
   closed when stop() is called or if an exception is raised. The background thread exits
   cleanly but the file descriptor leaks until process exit.

4. modules/passive_tree.py:142 — TYPE ANNOTATION BUG: `edges: list[tuple[str, str]] = set()`
   declares a list type but initializes as a set. Works at runtime (converted on line 178)
   but the annotation is misleading for any future developer.

5. modules/quest_tracker.py:92 — ENCAPSULATION BREACH: manually_uncomplete() directly
   accessed self._state._profile["completed_quests"] and self._state._save_profile(),
   both private members of AppState. AppState had no public method for this operation.

6. modules/currency_tracker.py:73 — MINOR ENCAPSULATION BREACH: get_display_data()
   accessed self._state._profile directly to get currency_session_start. Should use
   a property on AppState.

### Phase 1C — Redundancy & Counter-Vision Issues

7. install.py:141-206 — DUPLICATION: Passive tree download logic duplicated from
   modules/passive_tree.PassiveTree.download(). Not fixed this session (would require
   touching install.py + passive_tree.py together — low-impact duplication, deferred).

8. ui/widgets/passive_tree_panel.py:270-272 — STUB GAP: _get_quest_node_ids() returned
   an empty set with a vague comment. The quest tracker integration was missing entirely.
   Fixed in Phase 3 with quest summary banner and proper explanation of why node
   highlighting isn't possible (quest rewards = unspent points, not specific nodes).

## MAINTENANCE LOG

### Fix 1 — updater.py: Update dialog never shown (CRITICAL)
- File: core/updater.py
- Issue: QMetaObject.invokeMethod(app, "_show_update_dialog") called a non-existent method
- Fix: Added module-level _Signaler(QObject) with update_ready = pyqtSignal(str).
  check_and_prompt() creates the signaler, connects it to show_update_dialog(), then
  starts the background thread. Thread emits the signal instead of invoking a missing method.
  Signal is properly cross-thread safe via Qt's queued connection mechanism.
- Why it matters: The auto-updater was completely broken. Users would never be prompted
  to update despite the feature being prominently documented.

### Fix 2 — hud.py: Wrong tab index for crafting hotkey
- File: ui/hud.py:156
- Issue: setCurrentIndex(3) navigated to Currency tab, not Crafting tab
- Fix: Changed to setCurrentIndex(4) with comment showing the tab order
- Why it matters: The crafting hotkey (Ctrl+Shift+C) opened the wrong tab

### Fix 3 — client_log.py: File handle leak
- File: core/client_log.py:70-84
- Issue: File opened in _tail() but no finally block to close it
- Fix: Wrapped the read loop in try/finally: f.close()
- Why it matters: On repeated start/stop or reloads, file descriptors accumulate

### Fix 4 — passive_tree.py: Misleading type annotation on edges
- File: modules/passive_tree.py:142
- Issue: `edges: list[tuple[str, str]] = set()` — type says list, init is set
- Fix: Changed annotation to `set[tuple[str, str]]` to match the actual initialization
- Why it matters: Clarity for future development; mypy/pylance would flag this

### Fix 5 — state.py: Added uncomplete_quest() method
- File: core/state.py
- Issue: No public API to unmark a quest as complete
- Fix: Added uncomplete_quest(quest_id: str) method with save + notify
- Why it matters: quest_tracker was forced to reach into private state

### Fix 6 — state.py: Added currency_session_start property
- File: core/state.py
- Issue: No public property for currency session start timestamp
- Fix: Added @property currency_session_start -> float | None
- Why it matters: currency_tracker was reaching into _profile dict directly

### Fix 7 — quest_tracker.py: Removed private state access
- File: modules/quest_tracker.py:92
- Issue: manually_uncomplete() accessed self._state._profile and _save_profile() directly
- Fix: Now calls self._state.uncomplete_quest(quest_id) using the new public method
- Why it matters: Encapsulation — AppState owns its own mutation logic

### Fix 8 — currency_tracker.py: Removed private state access
- File: modules/currency_tracker.py:73
- Issue: get_display_data() accessed self._state._profile directly
- Fix: Now uses self._state.currency_session_start property
- Why it matters: Same encapsulation principle as Fix 7

## DEVELOPMENT LOG

### Quest Summary Integration in Passive Tree Panel

**Goal**: Wire quest tracker status into the passive tree viewer.

**What was built**:
- Added `_quest_summary` QLabel at the top of PassiveTreePanel, styled in teal
  (matching QUEST_COLOR used for highlighting)
- Added `_refresh_quest_summary()` method that pulls live totals from quest_tracker:
  - If any deductions exist: "Quest passive points: X net (Y earned - Z deducted) | W still available"
  - Otherwise: "Quest passive points: X / Y collected | Z still available"
- Subscribed to quest_tracker.on_update() in __init__ so the banner updates in real-time
  as quests are completed/uncompleted (both from Client.txt events and manual toggling)
- Updated `_get_quest_node_ids()` stub with a clear docstring explaining why it correctly
  returns an empty set: in PoE, quest rewards give unspent points (no specific node mapping)

**Files modified**: ui/widgets/passive_tree_panel.py

**Why it matters**: The passive tree panel previously had zero connection to the quest
system despite quest integration being a stated vision goal. Now a player can open the
tree, see their current quest point status at a glance, and use the tree to decide
where to spend upcoming earned points.

## TECHNICAL NOTES

- **Qt signal thread safety**: When bridging background threads to Qt UI, always use
  pyqtSignal on a QObject. Never use QMetaObject.invokeMethod with method names as
  strings on objects that don't define those methods.

- **Tab index management**: Consider using named constants or a dict for tab indices
  in hud.py if tabs are added/reordered in future. Currently hardcoded integers.

- **Quest->node mapping**: PoE quest rewards grant freely-allocatable passive points,
  not specific nodes. Any "highlight uncollected quest nodes" feature would need to
  track the player's actual allocated nodes (via character API, OAuth required). This
  is a future enhancement that requires user authentication.

- **AppState encapsulation pattern**: All mutation and persistence belongs in AppState.
  External modules should only call public methods. The pattern is: one method per
  conceptual state change, always save + notify inside that method.

## SUGGESTIONS FOR NEXT SESSION

1. **Currency tracker -- stash tab API** (MEDIUM priority): The manual spinbox entry
   creates significant friction. Adding official stash tab API support would let users
   auto-read currency counts. Requires user to provide POESESSID cookie or implement
   OAuth. Needs research into GGG's stash tab API format and TOS implications.

2. **Map overlay -- initial implementation** (LOW priority): The map overlay tab shows
   nothing (just calls self.show()). A minimal v1 could display zone name + mod count
   from Client.txt zone_change events with a static mods reference file. No live API
   needed for basic zone info.

3. **install.py duplication cleanup** (LOW): download_tree_data() in install.py
   duplicates logic from PassiveTree.download(). install.py should call
   PassiveTree.download(callback=print) directly. Simple fix, deferred.

4. **Price check UX refinement** (LOW): The category guesser heuristic in
   modules/price_check.py._guess_category() is basic. Item classes like "Trinket"
   or PoE2-specific classes would fall through to "BaseType". Could be improved
   with a more complete category map.

5. **Character API integration** (FUTURE/LONG): The most impactful future feature for
   the passive tree would be loading the player's allocated nodes from the GGG character
   API, enabling "highlight your current build" on the tree. Requires OAuth or
   POESESSID. Research TOS implications before starting.

## PROJECT HEALTH

Overall grade: 7.5/10
% complete toward original vision: ~65%

Core features are implemented and wired together. Quality is professional-grade.
The main gap is the map overlay (0% implemented) and the currency tracker's manual
input requirement. The passive tree viewer is fully functional but lacks player-node
tracking. The updater was silently broken and is now fixed -- important for keeping
users on current versions.

Notable risks:
- The `keyboard` library requires elevated permissions on some systems; if hotkeys
  don't fire, this is why
- poe.ninja API format could change between PoE versions -- monitor if prices stop loading
- The passive tree CDN URL is scraped from the PoE web page; could break if GGG changes
  their page structure (fallback URL to grindinggear/skilltree-export is the safety net)

═══════════════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════════
SESSION: 2026-03-23  (Session 2)
═══════════════════════════════════════════════════════════════

## ORIENTATION SUMMARY
Session 2. Read all prior session notes. Session 1 left off with 5 suggestions;
primary targets were currency stash tab API (medium) and map overlay v1 (low).
Map overlay was selected as the development target this session -- simpler to
implement, does not require OAuth/POESESSID research, directly advances the
one 0%-implemented feature. Currency stash API deferred again (still needs TOS
research before proceeding).

## ASSESSMENT GRADES

| Module               | Completeness | Quality | Vision Alignment |
|----------------------|-------------|---------|-----------------|
| Quest Tracker        |     8/10     |  9/10   |      9/10       |
| Passive Tree Viewer  |     7/10     |  8/10   |      8/10       |
| Price Checker        |     8/10     |  8/10   |      9/10       |
| Currency Tracker     |     6/10     |  8/10   |      7/10       |
| Crafting System      |     7/10     |  8/10   |      8/10       |
| Core Infrastructure  |     9/10     |  9/10   |      9/10       |
| Map Overlay          |     4/10     |  8/10   |      7/10       |

## SMOKE TEST FINDINGS

### Phase 1B -- Logic & Structure Issues

1. core/crash_reporter.py:104 -- ANTI-PATTERN: btns_layout created via
   __import__("PyQt6.QtWidgets", fromlist=["QHBoxLayout"]).QHBoxLayout()
   Dynamic import instead of just adding QHBoxLayout to the existing local
   import on line 65. Fixed.

2. core/client_log.py:12 -- MISLEADING DOCSTRING: quest_complete event
   documented as emitting {"quest_id": str, "name": str} but only emits
   {"name": str}. No quest_id field exists. Fixed docstring.

3. modules/price_check.py:127 -- CATEGORY GUESSER BUG: Weapon list included
   "staff" but PoE item class is "Staves" (not "Staff"). "staff" is not a
   substring of "staves". Also missing sceptres. Staves/sceptres were falling
   through to UniqueAccessory instead of UniqueWeapon. Fixed.

4. install.py:141-206 -- DUPLICATION (carried from Session 1): download_tree_data()
   and _download_tree_fallback() (~66 lines) duplicated PassiveTree.download().
   Fixed this session by delegating to PassiveTree.download().

### Phase 1C -- Redundancy & Counter-Vision Issues

No new counter-vision issues found. Session 1 issues are resolved or deferred.

## MAINTENANCE LOG

### Fix 1 -- crash_reporter.py: Dynamic import anti-pattern
- File: core/crash_reporter.py:65,104
- Issue: QHBoxLayout obtained via __import__() instead of proper import
- Fix: Added QHBoxLayout to the local from-import; replaced dynamic call with QHBoxLayout()
- Why it matters: Anti-pattern; confusing to read; no reason to use dynamic import here

### Fix 2 -- client_log.py: Misleading docstring
- File: core/client_log.py:12
- Issue: quest_complete docstring claimed quest_id field that does not exist
- Fix: Removed quest_id from docstring; now reads {"name": str}
- Why it matters: Documentation accuracy; future developer would search for quest_id

### Fix 3 -- price_check.py: Staff/sceptre category detection bug
- File: modules/price_check.py:127-130
- Issue: "staff" not in "staves"; "sceptre" not in weapon list at all
- Fix: Changed "staff" to "stave" (matches "staves"); added "sceptre", "spear", "flail"
  Also added "armour" to armour class list for completeness
- Why it matters: Unique staves/sceptres were silently mapped to UniqueAccessory category

### Fix 4 -- install.py: Passive tree download deduplication
- File: install.py:141-206
- Issue: 66 lines duplicating PassiveTree.download() and _download_tree_fallback()
- Fix: Replaced with 10-line function that calls PassiveTree.download() directly.
  PassiveTree uses only stdlib imports so safe to call from installer before pip install.
- Why it matters: Removes the duplication flagged in Session 1; single source of truth

## DEVELOPMENT LOG

### Map Overlay v1

**Goal**: Implement the last unstarted feature -- map overlay showing zone info.

**Approach**: Static zone database + Client.txt zone_change events. No external
API needed for v1. Scope: current zone info card + session history.

**Files created**:

data/zones.json
  - ~120 zone entries covering Acts 1-10
  - Per entry: act, area_level, waypoint (bool), boss (nullable), type (campaign/town)
  - Zone names match Client.txt log format exactly (e.g. "The Twilight Strand")
  - Act-specific zone names disambiguated (e.g. "Lioneye's Watch (Act 6)")

modules/map_overlay.py
  - MapOverlay class, no external dependencies
  - handle_zone_change(data): enriches zone with static data, updates history
  - get_current_zone() -> dict | None
  - get_history() -> list[dict]
  - on_update(callback) subscriber pattern (consistent with all other modules)
  - _MAX_HISTORY = 15 entries

ui/widgets/map_panel.py
  - MapPanel(QWidget) -- consistent with other panel patterns
  - Current zone card: name (gold, prominent), meta row (act/level/waypoint), boss label
  - Boss label shown in red only when boss exists
  - Hint text shown when no zone detected yet
  - Zone history QListWidget -- timestamped, most recent first
  - Town entries styled in dim color to distinguish from combat zones
  - Thread-safe update via QMetaObject.invokeMethod + pyqtSlot pattern
  - On init: populates from existing zone data (if app restarted mid-session)

main.py
  - Added MapOverlay import
  - Instantiated as map_overlay = MapOverlay()
  - Subscribed to zone_change: log_watcher.on("zone_change", map_overlay.handle_zone_change)
  - Passed to HUD constructor

ui/hud.py
  - Added MapPanel import
  - Added map_overlay parameter to __init__ and _build_ui
  - Created self._map_panel = MapPanel(map_overlay)
  - Added "Map" tab at index 5 (Quests=0, Tree=1, Price=2, Currency=3, Crafting=4, Map=5)
  - show_map() now navigates to index 5 (was a no-op placeholder)

**Result**: Map overlay is fully wired. When the player enters a zone, the Map tab
updates in real-time showing zone name, act, area level, waypoint status, and boss
(if applicable). History persists for the session.

## TECHNICAL NOTES

- **Tab index now 6 tabs**: Quests=0, Tree=1, Price=2, Currency=3, Crafting=4, Map=5
  Updated in TECHNICAL.md.

- **Zone names in Client.txt**: Act-repeated zones (Lioneye's Watch appears in Acts 1
  and 6) use different internal names. Act 6 version is "Lioneye's Watch (Act 6)".
  zones.json disambiguates with explicit "(Act N)" suffixes for repeated zones. If the
  player enters a zone not in the database, the map panel gracefully shows
  "(zone not in database)" -- it does not crash or show nothing.

- **install.py safe to import PassiveTree**: modules/passive_tree.py uses only stdlib
  (json, os, re, threading, urllib.request, dataclasses, typing). Safe to import
  from install.py before pip install has run.

- **price_check.py: stave vs staff**: "stave" matches "staves" (in substring check).
  "staff" does not. PoE item class is "Staves". Always use "stave" in substring matches
  against PoE item class strings.

## SUGGESTIONS FOR NEXT SESSION

1. **Map overlay -- zone mods data** (MEDIUM): Static zones.json has act/level/boss
   but no area mods. Adding a static map mods reference (e.g. common implicit mods
   by region or boss) would complete the map overlay to ~7/10 completeness.
   Alternatively, research poedb.tw scraping (no API, would need HTML parsing).

2. **Currency tracker -- stash tab API research** (MEDIUM): TOS research needed before
   implementing. Questions: Is POESESSID-based access TOS-compliant? Is it rate-limited?
   Does GGG officially support it? Research and document findings before coding.

3. **Passive tree -- player node highlighting** (FUTURE): Character API endpoint
   (undocumented) could return allocated nodes. Needs OAuth or POESESSID. TOS
   research required. Long-term enhancement.

4. **Price check -- currency conversion for non-chaos listings** (LOW): extract_prices()
   in poe_trade.py currently appends non-chaos amounts as raw values without conversion.
   The comment says "caller normalizes via poe_ninja" but PriceChecker never does this.
   Minor accuracy issue for divine/exalt-priced items.

## PROJECT HEALTH

Overall grade: 7.8/10 (up from 7.5 last session)
% complete toward vision: ~72% (up from ~65%)

All 6 planned features now have working implementations. Map overlay is v1 quality
(zone identity and history) with mods/mechanics data as next step. The main remaining
gaps are: map mods data, currency auto-reading, passive tree player node highlighting.
No new technical debt introduced.

Notable risk update: The install.py deduplication fix means PassiveTree.download()
is now the single implementation -- any bugs in that function affect both the installer
and the runtime module. Worth keeping in mind.

═══════════════════════════════════════════════════════════════
