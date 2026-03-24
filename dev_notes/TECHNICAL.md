# ExileHUD — Technical Reference

## Architecture

```
main.py                      — entry point, wires all modules, runs Qt event loop
config.py                    — defaults + state/config.json overlay loader
core/
  client_log.py              — tails Client.txt, emits named events (thread-safe)
  state.py                   — AppState: persists profile + currency log to JSON
  hotkeys.py                 — global hotkey manager (keyboard lib)
  updater.py                 — GitHub SHA comparison, ZIP download, restart
  crash_reporter.py          — global excepthook → JSONL log + Qt dialog
api/
  poe_ninja.py               — poe.ninja price cache (TTL-based, in-memory)
  poe_trade.py               — official trade API wrapper (rate-limited)
modules/
  passive_tree.py            — PassiveTree data layer: load/download/parse/search
  quest_tracker.py           — QuestTracker: maps log events → quest completion
  price_check.py             — PriceChecker: clipboard → ninja + trade API
  currency_tracker.py        — CurrencyTracker: session delta + chaos/hr
  crafting.py                — CraftingModule: cheat sheets + task queue
ui/
  hud.py                     — HUD(QMainWindow): tabs, title bar, drag-to-move
  widgets/
    quest_panel.py           — Quest list + point summary + next-quest callout
    passive_tree_panel.py    — QGraphicsView tree viewer + search + quest summary
    price_panel.py           — Price check results display
    currency_panel.py        — Currency input spinboxes + rate display
    crafting_panel.py        — Cheat sheet browser + task queue
data/
  passive_quests.json        — All passive-point quests, Acts 1–10
  crafting/methods.json      — 8 crafting method definitions
  passive_tree.json          — Downloaded by install.py / PassiveTree.download()
state/                       — Runtime data (gitignored except .gitkeep)
  config.json                — User config overrides
  profile.json               — Quest completion + crafting queue + current zone
  currency_log.json          — Per-session currency delta log
  version.json               — Installed commit SHA (written by installer)
  crash_log.jsonl            — Rotating crash log (500 entries max)
installer_gui.py             — Standalone tkinter GUI installer (compiled to .exe)
install.py                   — CLI installer (Python users)
```

## APIs & Data Sources

### poe.ninja
- Base: `https://poe.ninja/api/data`
- Endpoints: `currencyoverview` (currency/fragment) and `itemoverview` (items)
- Cache TTL: configurable, default 300s
- Returns chaos equivalent values
- No auth required, public API

### PoE Official Trade API
- Base: `https://www.pathofexile.com/api/trade`
- POST `/search/{league}` — returns result IDs and query ID
- GET `/fetch/{ids}?query={qid}` — returns up to 10 listings with price info
- Rate limit: ~12 req/10s; code enforces 1s minimum between requests
- No auth required for public stashes; user-specific endpoints require OAuth

### GitHub API (updater)
- `GET /repos/{owner}/{repo}/commits/{branch}` — compare SHAs
- Branch archive: `https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip`
- Token support (GITHUB_TOKEN in updater.py and installer_gui.py)

### Passive Tree Data
- Primary: scrape current URL from `https://www.pathofexile.com/passive-skill-tree` page
- Fallback: `https://raw.githubusercontent.com/grindinggear/skilltree-export/master/data.json`
- GGG abbreviated field names: `dn`=name, `sd`=stats, `ks`=keystone, `not`=notable, `m`=mastery, `isJewelSocket`=jewel socket, `out`/`in`=connections, `passivePointsGranted`=points granted
- Groups use `n` for node ID list (current format) or `nodes` (legacy)
- Nodes with direct `x`/`y` coords (new format) vs group+orbit+orbitIndex (legacy)
- Parser handles both formats

## Known Quirks

### Tab Index (hud.py)
Tabs are: 0=Quests, 1=Tree, 2=Price, 3=Currency, 4=Crafting, 5=Map
`show_crafting()` uses index 4. `show_map()` uses index 5. (Map tab added Session 2)

### Updater Signal (updater.py)
Original code tried `QMetaObject.invokeMethod(app, "_show_update_dialog")` but that method
never existed on QApplication. Fixed in Session 1 to use a proper Qt signal via a
module-level QObject signaler (_Signaler class with update_ready signal).

### Client.txt File Handle
The `_tail()` method in ClientLogWatcher opens a file handle that must be closed when
`stop()` is called. Fixed in Session 1 with try/finally.

### Passive Tree Edges Set vs List
`PassiveTree._parse()` collected edges into a `set` for deduplication (correct) but the
variable was annotated as `list`. Fixed in Session 1 with proper type annotation.

### AppState Encapsulation
`quest_tracker.manually_uncomplete()` previously directly accessed `state._profile` and
`state._save_profile()`. Fixed in Session 1 by adding `AppState.uncomplete_quest()`.
`currency_tracker.get_display_data()` previously accessed `state._profile` for session
start time. Fixed in Session 1 by adding `AppState.currency_session_start` property.

### Currency Tracker — Manual Entry
The currency tracker requires manual spinbox input. There is no automatic stash reading.
Stash tab API would require OAuth and is a future enhancement.

### Quest→Tree Node Mapping
In PoE, quest passive point rewards give freely-allocatable unspent points — they do not
unlock specific nodes. The tree panel therefore shows a quest summary (earned/total points)
rather than highlighting specific nodes. `_get_quest_node_ids()` intentionally returns an
empty set with documentation.

## Dependencies

See `requirements.txt` for full list. Key packages:
- `PyQt6` — main UI framework
- `requests` — HTTP for poe.ninja and trade API
- `keyboard` — global hotkey listener (requires admin on some systems)

### Zone Names in Client.txt (map_overlay.py)
Client.txt log entry: `Generating level N area "Zone Name"`. Zone names are exact in-game
strings. Zones that repeat across acts have different names (e.g. Act 6 uses
"Lioneye's Watch (Act 6)"). data/zones.json includes ~120 campaign zones with explicit
"(Act N)" suffixes for duplicated names. If a zone is not in the database, map_panel.py
shows "(zone not in database)" gracefully.

### price_check.py: stave vs staff
PoE item class is "Staves" not "Staffs". Use "stave" as the substring to match
(e.g. "stave" in "staves" = True, "staff" in "staves" = False). Fixed Session 2.

### poe_trade.py / price_check.py: Non-chaos price normalization (Session 3)
extract_prices() now returns list[dict] with {"amount": float, "currency": str} rather
than list[float]. PriceChecker._normalize_prices() converts to chaos using _TRADE_TO_NINJA
map + poe.ninja lookups. trade API currency keys: "divine", "exalt", "alch", "alt", "fuse",
"chance", "scour", "regal", "jew", "chrom", "blessed", "annul", "mir", "vaal", "ancient",
"harbinger". If a key is unknown, amount passes through as-is (graceful degradation).

### zones.json: notes field (Session 3)
Added optional "notes" field to mechanically significant zones:
- Kitava zones (Act 5 and Act 10 Cathedral Rooftop): resistance penalty warning
- Lioneye's Watch (Act 6): confirmation that -30% res is now active
- A handful of quest-relevant zones (Tidal Island, Weaver's Chambers, The Docks, The Library,
  The Dread Thicket)
map_panel.py: shows zone "notes" if present; otherwise falls back to _act_resist_note()
which returns a resistance reminder for acts 6-9 (-30%) and act 10+ (-60%).
Priority: zone-specific notes > act-based fallback > nothing.

### map_panel.py / price_panel.py: pyqtSlot import pattern (Session 3)
Both files previously imported pyqtSlot inside the class body and used the decorator in
post-definition assignment syntax. Fixed to module-level import + @pyqtSlot decorator.

### install.py: PassiveTree import is safe before pip install
modules/passive_tree.py imports only stdlib modules (json, os, re, threading,
urllib.request, dataclasses, typing). Safe to import from install.py before
dependencies are installed. Fixed Session 2 to remove 66-line duplication.

### QPainter.RenderHint vs QPainter.RenderHints (Session 4)
In PyQt6, QPainter.RenderHint (enum) and QPainter.RenderHints (flags combination) are
different classes. QGraphicsView.setRenderHint() takes a QPainter.RenderHint enum value.
QGraphicsView.renderHints() returns a QPainter.RenderHints flags value.
NEVER use `self.renderHints().__class__.Antialiasing` -- the flags class does not have
the enum values. Always import QPainter and use `QPainter.RenderHint.Antialiasing`.

### install.py: config.py import is safe before pip install (updated Session 4)
config.py uses only json + os (stdlib). Safe to import from install.py at the top level,
before pip install runs. DEFAULTS is now imported from config.py instead of duplicated.

### Currency rate calculation (Session 4)
get_currency_rate() now divides delta by the snapshot's own elapsed_hours (recorded at
snapshot time), not by current elapsed time. This gives a stable, accurate rate that
does not dilute as time passes between snapshots. Rate is "as of last snapshot" -- it
updates only when a new snapshot is taken.

### currency_last_amounts schema (Session 4)
New field "currency_last_amounts": {} added to _PROFILE_DEFAULTS in state.py.
Populated by log_currency_snapshot() each time a snapshot is taken. Used by
CurrencyPanel.__init__ to restore spinbox values on app restart. The {**defaults, **data}
merge pattern handles backward compatibility -- existing profiles get {} automatically.

### currency_panel.py / state.py: Cross-session aggregation (Session 5)
state.py added get_historical_rate(days: int | None). days=None means all-time (cutoff=0,
all positive timestamps pass). days=7 means last 7*24 hours (time-zone-agnostic).
currency_tracker.py added get_historical_display_data(days) mirroring get_display_data().
currency_panel.py added _hist_label + _refresh_historical() showing "7-day avg: Xc/hr
| All-time avg: Xc/hr" in dim text below the current session rates.
Historical label hidden until at least one snapshot exists (all_total == 0 guard).

### state.py: Currency rate session boundary (Session 5)
get_currency_rate() now checks if last snapshot timestamp < currency_session_start.
If so, returns {} (snapshot belongs to old session). This ensures starting a new
session clears displayed rates rather than showing stale previous-session values.

### currency_log.json retention
Never pruned. Grows modestly: ~200 bytes/snapshot. 5 snapshots/day * 365 days ≈ 350KB.
No rotation needed. Long-term use gives increasingly meaningful all-time averages.

## Open Questions

1. **Stash tab API -- OAuth implementation** (UNBLOCKED as of Session 5):
   TOS research confirmed: OAuth is the correct, fully TOS-compliant approach.
   POESESSID is technically prohibited (credential-sharing clause) and uses
   undocumented endpoints. The 2020 POE Overlay incident showed POESESSID is
   detectable and actionable.

   **To register**: Email oauth@grindinggear.com for a public OAuth client registration.
   **Required disclaimer in-app**: "This product isn't affiliated with or endorsed
   by Grinding Gear Games in any way."

   **Implementation details**:
   - OAuth 2.1 flow; desktop tools register as public clients (no client_secret)
   - Scope needed: `account:stashes`
   - Endpoint: GET /api/stash/{league} (list tabs) + GET /api/stash/{league}/{stash_id}
   - User authenticates once in-browser; token stored in state/ (never committed)
   - Access token refresh handled via standard OAuth refresh flow
   - Official docs: https://www.pathofexile.com/developer/docs/authorization

   **TOS verdict**: Fully compliant when using OAuth. POESESSID = do NOT use.
   Known compliant tools using stash API: Exilence Next, Sidekick, poe-ninja, trade sites.

2. **Map overlay data source** — poedb.tw? Static JSON? Need to decide format and
   update strategy for map mods.
3. **Character API** — Could auto-import allocated passive nodes for tree highlighting.
   Uses undocumented but community-known endpoint. Requires OAuth (same flow as stash).
   TOS status: likely compliant if read-only and non-competitive, but needs confirmation
   before implementing. Could reuse the OAuth infrastructure built for stash access.
4. **PoE 2 support** — Config has `poe_version: poe1/poe2` field but no conditional logic
   exists. Passive tree data format differs. Future concern.
