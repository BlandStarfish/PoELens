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
Tabs are: 0=Quests, 1=Tree, 2=Price, 3=Currency, 4=Crafting
`show_crafting()` must use index 4, not 3. (Fixed Session 1)

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

## Open Questions

1. **Stash tab API** — Would need OAuth login flow or user-provided POESESSID. Is this
   worth the complexity? Would significantly improve currency tracker UX.
2. **Map overlay data source** — poedb.tw? Static JSON? Need to decide format and
   update strategy for map mods.
3. **Character API** — Could auto-import allocated passive nodes for tree highlighting.
   Requires POESESSID or OAuth. Undocumented API, risk of TOS gray area.
4. **PoE 2 support** — Config has `poe_version: poe1/poe2` field but no conditional logic
   exists. Passive tree data format differs. Future concern.
