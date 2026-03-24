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
  - If any deductions exist: "Quest passive points: X net (Y earned − Z deducted) | W still available"
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

- **Quest→node mapping**: PoE quest rewards grant freely-allocatable passive points,
  not specific nodes. Any "highlight uncollected quest nodes" feature would need to
  track the player's actual allocated nodes (via character API, OAuth required). This
  is a future enhancement that requires user authentication.

- **AppState encapsulation pattern**: All mutation and persistence belongs in AppState.
  External modules should only call public methods. The pattern is: one method per
  conceptual state change, always save + notify inside that method.

## SUGGESTIONS FOR NEXT SESSION

1. **Currency tracker — stash tab API** (MEDIUM priority): The manual spinbox entry
   creates significant friction. Adding official stash tab API support would let users
   auto-read currency counts. Requires user to provide POESESSID cookie or implement
   OAuth. Needs research into GGG's stash tab API format and TOS implications.

2. **Map overlay — initial implementation** (LOW priority): The map overlay tab shows
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
tracking. The updater was silently broken and is now fixed — important for keeping
users on current versions.

Notable risks:
- The `keyboard` library requires elevated permissions on some systems; if hotkeys
  don't fire, this is why
- poe.ninja API format could change between PoE versions — monitor if prices stop loading
- The passive tree CDN URL is scraped from the PoE web page; could break if GGG changes
  their page structure (fallback URL to grindinggear/skilltree-export is the safety net)

═══════════════════════════════════════════════════════════════
