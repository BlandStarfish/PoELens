# PoELens — Technical Reference

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
modules/
  xp_tracker.py              — XPTracker: polls Character API, tracks XP/hr
  chaos_recipe.py            — ChaosRecipe: stash item scanning + set counting
ui/widgets/
  xp_panel.py                — XP rate display + session start + auto-poll timer
  chaos_panel.py             — Chaos/regal recipe set counter display
  notes_panel.py             — Personal build notes (QTextEdit + state/notes.json)
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
Tabs are: 0=Quests, 1=Tree, 2=Price, 3=Currency, 4=Crafting, 5=Map, 6=Settings
`show_crafting()` uses index 4. `show_map()` uses index 5. (Map tab added Session 2)
Settings tab added Session 12. No hotkey needed — user navigates manually.

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

### oauth.py: PKCE flow details (Session 6)
OAuthManager uses OAuth 2.1 Authorization Code + PKCE (S256):
- code_verifier: base64url(random 32 bytes)
- code_challenge: base64url(sha256(code_verifier))
- Local callback server: HTTPServer on localhost:64738 (port fixed for redirect_uri consistency)
- Auth URL: https://www.pathofexile.com/oauth/authorize
- Token URL: https://www.pathofexile.com/oauth/token
- Scope: account:stashes
- Flow timeout: 120 seconds
- Tokens stored in state/oauth_tokens.json (gitignored)
- Token response includes "username" field = PoE account name
- Refresh token preserved if not rotated by server (kept from previous token set)
- Token auto-refreshes 60s before expires_at on next get_access_token() call

### stash_api.py: API endpoint (Session 6)
Base URL: https://api.pathofexile.com (dedicated API subdomain for OAuth endpoints)
Endpoints:
  GET /stash/{realm}/{league}              → {"stashes": [...]}
  GET /stash/{realm}/{league}/{stash_id}   → {"stash": {"items": [...]}}
Default realm: "pc" (alternatives: "xbox", "sony")
Rate limiting: 1s minimum between requests; auto-retry once on 429 with Retry-After header
Currency tab detection: type == "CurrencyStash" preferred; falls back to first 3 PremiumStash/NormalStash tabs
Item currency counting: item["typeLine"] matched against TRACKED_CURRENCIES; item["stackSize"] summed
The StashAPI import of TRACKED_CURRENCIES from modules.currency_tracker is intentional — single source of truth for tracked currencies.

### currency_panel.py: Thread-safe OAuth signals (Session 6)
OAuth and stash API operations run in background threads. UI updates are marshaled to Qt main thread via:
  _auth_success  = pyqtSignal()           → _on_auth_success()
  _auth_failed   = pyqtSignal(str)        → _on_auth_failed(message)
  _stash_loaded  = pyqtSignal(object)     → _on_stash_loaded(amounts_dict)
  _stash_error   = pyqtSignal(str)        → _on_stash_error(message)
The pyqtSignal(object) type is used for the stash amounts dict since dict signals work but object is more explicit.
When oauth_client_id is not configured (empty string), the entire OAuth UI section is omitted from _build_ui()
so the panel is backward compatible for users without a registered client_id.

### OAuth disclaimer requirement (Session 6)
GGG requires registered apps to display:
  "This product isn't affiliated with or endorsed by Grinding Gear Games in any way."
This disclaimer is shown in the OAuth callback HTML page (displayed in browser after auth).

### passive_tree_panel.py: Build URL import (Session 7)
Accepts two formats:

1. **PoE passive tree URL** (from in-game export or poebuilds website)
   URL form: `https://www.pathofexile.com/passive-skill-tree/[base64url]`
   Binary format (big-endian, URL-safe base64):
     - Bytes 0-3: version uint32 (4 or 6 for PoE1)
     - Byte 4: character class (0=Scion, 1=Marauder, 2=Ranger, 3=Witch, 4=Duelist, 5=Templar, 6=Shadow)
     - Byte 5: ascendancy class index
     - Byte 6: fullscreen flag
     - Remaining: 2 bytes per allocated node (uint16 big-endian)
   Node IDs are uint16 matching the keys in PassiveTree.nodes dict.

2. **Path of Building build code** (community standard, widely shared)
   Format: zlib-compressed XML, base64-encoded (standard base64, not URL-safe)
   Parser: base64-decode → zlib-decompress → regex search for `nodes="id1,id2,..."`
   in a `<Spec>` element. Supports both standard zlib (wbits=15) and raw deflate (-15).

`PassiveTree.parse_tree_url(url_or_code)` handles both formats automatically.
Returns empty set on any parsing failure (graceful degradation).

### passive_tree_panel.py: NodeItem allocation state (Session 7)
NodeItem now tracks `_allocated: bool` alongside the existing `data(0)` search state.
Visual priority: hover > search highlight (data(0)="search") > allocated > default.
Key invariant: `clear_highlight()` clears search state but NOT allocation.
`set_allocated()` does not override active search color (preserves visual layering).
ALLOCATED_COLOR = "#ffd700" (bright gold) to distinguish from QUEST_COLOR (teal) and
SEARCH_COLOR (green).

### install.py: OAuth client_id prompt (Session 7)
`setup_state()` now prompts for `oauth_client_id` during initial install.
Optional — pressing Enter skips it. Can always be added later to `state/config.json`.
Surfaces the feature to new users without breaking non-interactive environments.

### currency_panel.py: Per-currency historical breakdown (Session 9)
`_refresh_historical()` now shows a "Top: ..." second line on the `_hist_label`
when all-time historical data exists. Displays top-3 positive earners by chaos/hr.
Threshold: 0.01c/hr (consistent with current session display threshold).
Uses `alltime["chaos_rates"]` dict already computed in the same method call.
`_hist_label.setWordWrap(True)` (set since Session 5) renders the newline correctly.

### GitHub repo visibility (Session 9)
Repo BlandStarfish/ExileHUD (now BlandStarfish/PoELens) was made public by the user during Session 9.
GITHUB_TOKEN = "" in both installer_gui.py and updater.py is correct for public repos.
If the repo is made private again, a fine-grained read-only PAT must be set in:
  - installer_gui.py line 30: GITHUB_TOKEN = "your_pat_here"
  - core/updater.py line 25: GITHUB_TOKEN = "your_pat_here"
The PAT only needs: Actions=read, Contents=read for the repo.


### state.py: get_session_stats() (Session 10)
New method added alongside get_historical_rate(). Returns snapshot_count and
total_hours from the currency log filtered by optional days cutoff.
Pattern: same cutoff logic as get_historical_rate(). Returns zeros gracefully
when no data. Used by currency_tracker.get_session_stats() -> currency_panel
_refresh_historical() to display "(N snapshots, Xh tracked)" in the all-time label.

### methods.json: recombinator method (Session 10)
Added as the 9th crafting method. Key mechanics:
- Two same-base-type items are consumed
- Each explicit mod on either input independently has a chance to appear on output
- Result has standard item affix count (not a sum of both inputs)
- Materials: Recombinator (from Expedition vendors Gwennen/Rog/Tujen or trade)
- Added 3.15 Expedition, still in game as of 2026
CraftingPanel renders it from the standard steps/materials/notes fields with no
special handling. Works in the combo box and Add to Queue workflow unchanged.

### methods.json: exalt_slam accuracy (Session 10)
"Exalted Orbs are expensive" note removed. Since 3.13 Echoes of the Atlas,
Divine Orbs replaced Exalted Orbs as the premier currency. Exalts are now
~15-25c each, making slam-and-annul loops viable for mid-tier gear crafting.
The "expensive" tag was also removed; replaced with "mid-tier".

### methods.json: fossil_guide field not rendered (Session 10)
The fossil_crafting entry has a "fossil_guide" dict with 13 fossil types and
their effects. CraftingPanel._on_method_selected() renders only steps/materials/notes
fields and ignores fossil_guide. Data is correct -- display is deferred.
Next session: detect fossil_guide field and render as extra section in method detail.

### Project rebranding: ExileHUD → PoELens (Session 11)
All source files updated: app name, User-Agent strings, window title, dialog titles,
VISION.md/TECHNICAL.md headers, zones.json comment, analytics _APP_NAME,
GitHub repo references (BlandStarfish/PoELens). GitHub repo was renamed from
ExileHUD to PoELens by the user.

### oauth.py / stash_api.py / character_api.py: GGG User-Agent compliance (Session 11)
GGG requires OAuth apps to use User-Agent format:
  OAuth {clientId}/{version} (contact: {contact})
oauth.py previously used a stale `"PoELens/1.0"` literal in _exchange_code and
_do_refresh. Fixed by adding module-level _CONTACT constant and _ua(client_id) helper:
  def _ua(client_id: str) -> str:
      return f"OAuth {client_id}/1.0 (contact: {_CONTACT})"
Applied to both methods. stash_api.py and character_api.py already use _ua() correctly.

### updater.py / installer_gui.py: GitHub zipball extraction path fix (Session 11)
GitHub's /zipball/ API endpoint names the extracted root directory
{owner}-{repo}-{sha}, NOT {repo}-{branch} as previously hardcoded.
For repo BlandStarfish/PoELens on master, the extracted dir is named e.g.
"BlandStarfish-PoELens-abc1234" -- never predictable at compile time.
Fixed in both files with dynamic discovery:
  subdirs = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
  if not subdirs:
      raise RuntimeError("Update archive has unexpected structure — no directory found.")
  extracted = os.path.join(tmp, subdirs[0])

### zones.json: atlas endgame maps (Session 11)
Added ~100 atlas map entries, Tiers 1-17 (area levels 68-84). Format:
  "MapName": {"act": null, "tier": N, "area_level": N+67, "waypoint": true,
              "boss": "Name", "type": "atlas"}
  Optional: "notes": "..." for Pinnacle Guardians and unique map encounters
Names match exact Client.txt log strings (no "Map" suffix in zone name).
All atlas maps have waypoint=true (waypoints unlock after first clear).
Tier 16 Pinnacle Guardians (Phoenix/Hydra/Minotaur/Chimera) have notes
showing which Shaper key fragment they drop.
Tier 17 maps: Abomination, Citadel, Fortress (area_level 84).

### map_panel.py: atlas zone display (Session 11)
_show_current(): atlas type now shows "Tier N Map  •  Area level N  •  ✓ Waypoint"
instead of "Act None  •  ..." which was broken for atlas maps.
_refresh_history(): now shows T{tier} prefix for atlas maps: "HH:MM  MapName  (T14, lvl 81)"
instead of the old "Act None" which would show for maps.
Notes fallback guard: `(zone_type != "atlas" and _act_resist_note(act))` prevents
_act_resist_note(None) call for atlas zones.

### core/character_api.py: Character API (added Session 10/11)
CharacterAPI wraps GGG OAuth character endpoints:
  GET /character           → list_characters() → list of {name, class, league, level, ...}
  GET /character/{name}    → get_passive_hashes(name) → set of node_id strings
  get_best_character(league) → highest-level char in league (fallback: any league)
Passive hashes from API map directly to PassiveTree.nodes keys (same namespace
as parse_tree_url output). Character name is URL-encoded for the path segment.
Scope required: account:characters. 403 → logged with re-auth instructions.

### core/screen_reader.py: OCR screen reader (added Session 10/11)
User-triggered only (button click). Uses:
  mss       — cross-platform screen capture
  Pillow    — image format conversion
  winrt     — Windows 10+ built-in OCR (winrt.windows.media.ocr)
All three are optional; is_available() returns False if any is missing.
ScreenReader.scan() → background thread → on_result callbacks → {"text", "error"} dict.
WinRT OCR requires an absolute backslash path to a temp PNG file.
currency_panel.py shows "Scan Stash Tab (experimental)" button only when winrt available.
TOS: user-triggered screen capture is Tier 2 / passive reading (same as Lailloken UI).

### price_check.py: Clipboard currency detection (added Session 10/11)
parse_item_clipboard() now extracts stack_size from "Stack Size: N/M" line.
on_currency_detected(callback) registers callbacks fired when a currency stack
is Ctrl+C'd. update_from_clipboard_scan() accepts OCR text for bulk currency parsing.
main.py wires: price_checker.on_currency_detected(lambda name, count: hud.on_currency_clipboard(name, count))
currency_panel.py handles the signal to update spinboxes.

## Open Questions

1. **Stash tab API -- OAuth implementation** ✅ IMPLEMENTED (Session 6)
2. **Character API sync** ✅ IMPLEMENTED (Sessions 10-11)
3. **Map overlay data source** ✅ RESOLVED (Session 11) — zones.json now covers all atlas
   Tier 1-17 maps. Map mod display (affixes/mods on rolled maps) remains unimplemented.
4. **PoE 2 support** — Config has `poe_version: poe1/poe2` field but no conditional logic
   exists. Passive tree data format differs. Future concern.
5. **fossil_guide rendering** ✅ RESOLVED (Session 12 discovery) — crafting_panel.py
   _on_method_selected() already renders fossil_guide as a color-coded bullet list using
   walrus-pattern `if fossil_guide := m.get("fossil_guide"):`. Implemented prior to Session 12.

### Tab indices (Session 13)
Quests=0, Tree=1, Price=2, Currency=3, Crafting=4, Map=5, XP=6, Recipe=7, Notes=8, Settings=9
show_crafting() uses index 4. show_map() uses index 5. XP/Recipe/Notes have no hotkeys.

### xp_tracker.py: polling strategy (Session 13)
XPTracker.handle_zone_change() is called from ClientLogWatcher's background thread (thread-safe).
It spawns a poll thread only if: xp_session_start is set AND _ZONE_POLL_COOLDOWN (120s) has elapsed.
XPPanel has a QTimer (every 5min) that also triggers poll() when session is active + OAuth connected.
The character API returns `experience` as total accumulated XP for the character (not level-local XP).
XP delta = current_experience - baseline_experience (simple subtraction, no XP table needed).
Time-to-level estimation deferred — requires confirmed XP table per level.

### chaos_recipe.py: item category format (Session 13)
GGG stash API item `category` field is a dict: {"armour": ["helmet"]}, {"accessories": ["ring"]},
{"weapons": ["twohanded", "axe"]}, {"offhand": ["shield"]}, etc.
Weapon slot filling: 2H weapons each fill 1 weapon slot. 1H weapons each need an offhand pair.
weapon_slots = two_handers + min(one_handers, offhands)
Items with ilvl < 60 are excluded. Rare = frameType == 2.
Chaos tier = ilvl 60-74. Regal tier = ilvl 75+. Any = ilvl 60+.
StashAPI.get_all_stash_items() skips CurrencyStash, FragmentStash, MapStash, DivinationStash,
UniqueStash, GemStash, DeliriumStash, BlightStash, MetamorphStash, BreachStash.
max_tabs=20 default limits scan time; 1s/tab rate limit = max ~20s scan.

### notes_panel.py: storage (Session 13)
state/notes.json: {"text": "..."} — gitignored (state/ is gitignored except .gitkeep).
Loads on init, saves on button click only (no auto-save).

### passive_tree.py: inline imports removed (Session 13)
Moved `math`, `base64`, `struct`, `zlib` from method bodies to module-level imports.
Removed `import re as _re` inside parse_tree_url() — `re` was already at module level.
All `_re.search(...)` calls updated to `re.search(...)`.

### settings_panel.py: on_opacity_change callback (Session 12)
SettingsPanel accepts optional `on_opacity_change: Callable[[float], None]` callback.
In hud.py, `on_opacity_change=self.setWindowOpacity` is passed directly -- QMainWindow.setWindowOpacity
accepts a float and matches the callback signature exactly. Opacity is applied immediately on save;
all other settings (path, league, hotkeys) take effect on next restart.
Hotkeys partial save: empty fields are excluded from saved dict. config.load() merges with DEFAULTS,
so clearing a hotkey field resets it to default rather than disabling it entirely.

### chaos_recipe.py: unidentified item tracking (Session 14)
count_sets() now tracks "unid" tier per slot alongside chaos/regal.
item.get("identified", True) — absent field or True = identified; False = unidentified.
Defaults to True (identified) when absent, which is the safe assumption.
"unid_sets" = _complete("unid"): minimum across all slots of unid count
(treating rings as unid//2). Requires all slots in the set to have ≥1 unid item.
A single identified item in any slot drops unid_sets to 0 for that potential set.
chaos_panel.py: "Unid" column added (5th column, teal color). Summary shows
"N fully-unid set(s) → 2× yield" when unid_sets > 0.


### state.py: _XP_TABLE (Session 15)
Module-level dict mapping level (1-100) to cumulative total XP required to reach that level.
_XP_TABLE[N] = total XP from character creation to reach level N.
GGG character API "experience" field = same unit (cumulative, not level-relative).
time_to_level = (_XP_TABLE[level+1] - experience) / xp_per_hr * 60  (minutes)
Source: PathOfBuilding community repo (ExpTable.lua).
pathofexile.wiki.gg blocks automated access (401/403). Use PoB or RePoE as fallback.

### settings_panel.py: optional state parameter (Session 15)
SettingsPanel accepts optional state=None parameter. When state is provided, a "New
Character" button is shown in the Game group. Calls state.reset_character() after
QMessageBox.question() confirmation. Backward compatible: state=None hides the button.

### state.py: reset_character() (Session 15)
Clears all character-specific fields: completed_quests, passive_points_used,
ascendancy_points_used, and all xp_* fields. Preserves currency, crafting, zone.
Fires two notifications: completed_quests ([]) and xp_session (None).
Quest panel updates immediately. XP panel updates on next 5-min timer tick (not instant).

### map_panel.py: Campaign progression banner (Session 16)
_build_ui() adds self._progress_label (QLabel, hidden) above the zone card.
_show_current() populates it:
  - atlas zones: "Endgame Atlas" in TEAL (#4ae8c8)
  - campaign acts 1-10: "Campaign   Act N / 10   [━━━━━─────]" in ACCENT (#e2b96f)
  - unknown zones (info=None): label.hide()
_update_campaign_progress(act) builds the bar from Unicode box chars:
  filled="━"*act_n, empty="─"*(10-act_n). Guards: act must be int 1-10.

### xp_tracker.py: xp_session change subscription (Session 16)
Added to __init__: state.on_change("xp_session", lambda _: self._fire_update())
Propagates new-character resets to XP panel within one event cycle.
Previously the panel waited up to 5 min for the auto-poll timer.
Pattern mirrors quest_panel.py subscribing to "completed_quests".

### poe_ninja.py: get_divination_card_data() (Session 18)
Returns {name: {"chaos": float, "stack_size": int}} for all div cards in league.
"stackSize" field in poe.ninja DivinationCard itemoverview response = full stack needed.
Does NOT use the TTL cache — called once per user-triggered scan. Separate from get_all()
to avoid polluting the price cache with the extra stack_size field.

### stash_api.py: get_divination_items() (Session 18)
Scans tabs where type == "DivinationStash" only. Returns {card_name: count}.
"DivinationStash" was previously in _EQUIPMENT_SKIP_TYPES for the chaos recipe scan.
The skip list remains unchanged — div scan uses this separate method instead.

### atlas_tracker.py: persistence (Session 18)
state/atlas_progress.json: {"visited": [sorted list], "saved_at": float timestamp}
Saves only when a NEW map is added to visited set (not every zone_change).
_load_progress() filters visited set against current atlas_zones to handle any
future zone DB changes without stale entries. os.makedirs(exist_ok=True) guards
against first-run (state/ dir exists already but guard is cheap).
session_visited tracks maps entered this session specifically (a subset of visited).

### Tab indices (Session 19)
Quests=0, Tree=1, Price=2, Currency=3, Crafting=4, Map=5, XP=6, Recipe=7,
Notes=8, Settings=9, Divs=10, Atlas=11, Bestiary=12, Heist=13, Gems=14

### hud.py: fallback QWidget() for optional panels (Session 18)
div_panel and atlas_panel accept None as first argument (for tests/fallback).
hud.py uses `DivPanel(div_tracker, ...) if div_tracker else QWidget()` pattern.
In production main.py these are always provided. The fallback is defensive only.

### bestiary_panel.py: beast family colors (Session 18)
Craicic=#e2b96f (gold), Fenumal=#c87be8 (purple), Eber=#4ae8c8 (teal),
Farric=#e86b4a (orange), Unique=#aa9e6e (dim gold). Applied as badge labels on
beast requirements. Consistent with PoE's in-game bestiary faction coloring.

### zones.json _comment guard reminder (Session 18)
The "zones" dict contains "_comment" key with string value.
AtlasTracker._load_atlas_zones() uses `isinstance(info, dict)` guard.
Any future code iterating zone_db.items() MUST use the same guard.

### poe_ninja.py: get_divination_card_data() reward field (Session 19)
poe.ninja DivinationCard itemoverview response includes "explicitModifiers" array.
First element's "text" field = card reward description (e.g. "Kirac's Choice").
Added "reward" key to returned dict. Empty string when absent.
DivPanel renders reward as DIM-colored text below card name/stack/value.

### stash_api.py: get_heist_items() (Session 19)
Scans ALL stash tabs (no type filtering — Heist items may be in any tab).
Contracts identified by typeLine.startswith("Contract:").
Blueprints identified by typeLine.startswith("Blueprint:").
Job type extracted by _extract_heist_job(): scans requirements[] for non-Level entries
matching _HEIST_JOBS frozenset. Returns ("Unknown", 0) when job not in requirements.
Wing status from _extract_wing_status(): looks for additionalProperties[name=="Wings Unlocked"]
with value like "2/4". Returns (0, 0) when absent.
Both helpers are module-level functions (not methods) — clean to test independently.

### character_api.py: get_character_items() (Session 19)
Fetches /character/{name} (same endpoint as get_passive_hashes).
Returns data.get("items", []) — equipped item list.
Socketed gems appear as item["socketedItems"] within each equipment item.
Gems: frameType == 4. Support gems: item["support"] == True.
Level/quality parsed from item["properties"] array.

### gem_planner.py: sell candidate criteria (Session 19)
Awakened gems at level 4+: high trade value, should sell or level to 5.
Any gem at level 20 + quality 20: 20/20 sell candidate.
Any gem at level 20: eligible for Vaal Orb → 20/20 conversion.
Level parsing: handles "20 (Max)" format from GGG API (.split()[0]).
Quality parsing: strips leading "+" and trailing "%" from "+20%" format.

### heist_planner.py: processing (Session 19)
_process() groups contracts by job type, sorts each group by ilvl desc.
Blueprints sorted by ilvl desc, wings_unlocked desc.
ROGUE_JOBS list defines canonical display order in HeistPanel.
Unknown job contracts (no matching requirement) grouped under "Unknown" at end.

### stash_api.py: get_map_items() + _parse_map_item() (Session 23)
MapStash tab items expose full map mod data via the official stash API.
The GGG Item object schema (confirmed from developer docs):
  explicitMods: list[str]  — human-readable explicit mod strings (e.g. "Players have -10% to all Resistances")
  properties: list[{name, values}]  — item stats including "Map Tier", "Item Quantity", "Item Rarity", "Monster Pack Size"
  rarity: str  — "Normal", "Magic", "Rare", or "Unique"
  identified: bool  — absent or True = identified; False = unidentified
  typeLine: str  — map name (without "Map" suffix in zone name)

Property values format: properties[N]["values"] = [[display_string, type], ...]
  display_string for IIQ/IIR/Pack: "+45%" (strip "+%") to get integer
  display_string for Map Tier: "14" (plain integer string)
_parse_map_item() is a module-level function in stash_api.py for clean testability.

### PoE2 passive tree data (confirmed Session 23)
GGG developer docs reference grindinggear/skilltree-export for both PoE1 and PoE2,
but the repo only has PoE1 data (master/royale branches, no poe2 branch).
No official standalone PoE2 passive tree JSON exists as of 2026-03.
Only source: extract from game client GGPK (as PathOfBuilding-PoE2 does).
PoE2 passive tree support BLOCKED until GGG publishes official export.

### Tab indices (Session 24)
Outer groups: Character(0) / Loot(1) / Endgame(2) / Info(3)
Character inner: Quests(0) / Tree(1) / XP(2) / Notes(3) / Lab(4)
Loot inner: Price(0) / Currency(1) / Recipe(2) / Divs(3) / Flip(4)
Endgame inner: Map(0) / Atlas(1) / Crafting(2) / Heist(3) / Gems(4) / MapStash(5)
Info inner: Bestiary(0) / Expedition(1) / Settings(2)

### poe_ninja.py: raw cache for currency flip (Session 24)
_raw_cache: dict[str, tuple[float, list]] stores full JSON lines from currencyoverview.
Populated in _fetch() when endpoint == "currencyoverview" alongside the price dict.
TTL re-check is implicit: _get_category("Currency") is called by get_currency_flip_data()
before reading _raw_cache, ensuring stale data is re-fetched.
set_league() clears both _cache and _raw_cache for consistency.
get_currency_flip_data() returns [] if _raw_cache is empty (network failure path).

### Currency flip semantics (Session 24)
receive.value = chaos you pay to acquire 1 unit of this currency (buy price)
pay.value = chaos you receive when selling 1 unit of this currency (sell price)
margin_pct = (pay - receive) / receive * 100
Positive margins arise during price discovery or temporary supply/demand imbalances.
In an efficient market, margins are typically negative (bid-ask spread works against you).
_EXCLUDE set in currency_flip.py filters trivial low-value currencies that show
artifically high % margins due to near-zero absolute chaos values.

### LabTracker state file (Session 24)
state/lab.json -- covered by existing state/ .gitignore glob.
Format: {"Normal": bool, "Cruel": bool, "Merciless": bool, "Eternal": bool}
on_update callbacks are no-arg (unlike QuestTracker which passes status list).
LabPanel calls tracker.get_status() directly in _refresh() rather than receiving
data via callback, which avoids coupling the callback signature to the UI refresh logic.

### ExpeditionPanel: category filter buttons (Session 25)
Quick-filter row added above the danger legend. Buttons: All / Loot Bonuses / Monster Buffs / Area Modifiers.
_active_category state tracks active filter (None = All). _on_search() applies category filter first,
then text query on the resulting pool. _set_active_filter() updates button [active='true'] property
and calls style().unpolish/polish to force Qt to re-evaluate the dynamic property stylesheet.
Button colors are static (defined inline per button); the [active='true'] rule changes the label color
and border-color to match the button's own accent color using QPushButton[active='true'] CSS selector.

### SyndicatePanel: data + panel (Session 25)
data/syndicate_members.json: 22 entries, each with name, factions (list), primary_faction,
intel_reward (string), safehouse_rewards (dict: division -> reward string), notes.
Valid factions: Transportation, Research, Fortification, Intervention.
primary_faction must appear in factions list (validated by tests).

SyndicatePanel follows BestiaryPanel/ExpeditionPanel patterns:
  - Division filter buttons with per-division colors (teal/gold/orange/red)
  - Full-text search across name, factions, intel_reward, safehouse_rewards values, notes
  - Member cards with faction abbreviation badges (first 4 chars: Tran/Rese/Fort/Inte)
  - safehouse_rewards rendered as per-division colored labels using RichText format
  - Left border accented by primary_faction color

tests/test_syndicate_panel.py: 17 data integrity tests. All tests use the fixture
pattern from conftest (load JSON once per module). Key members verified by name:
Catarina (Research), Vorici (Transportation), Elreon (Research), Aisling (Transportation).

Tab placement: Info group, index 2 (between Expedition and Settings).
_INFO_SETTINGS shifted from 2 to 3 in hud.py.

## Session 26 Additions

### New data files
- data/vendor_recipes.json — 21 vendor recipes, 4 categories (Currency/Quality/Leveling/Unique)
  Schema: {name, category, ingredients, result, notes}
- data/scarabs.json — 52 scarabs (13 mechanics × 4 tiers)
  Schema: {name, mechanic, tier, effect, atlas_passive}
  Tiers: Rusted < Polished < Gilded < Winged

### ScarabPanel grouping design
  Scarabs are grouped by mechanic (not listed flat) for readability.
  _group_by_mechanic() builds dict[mechanic, list[scarab]] sorted by tier_order.
  The panel renders one QWidget card per mechanic with tier rows inside.
  This avoids 52 individual cards scrolled separately — much better UX.
  Compare to BestiaryPanel (flat cards) vs SyndicatePanel (flat cards):
  Scarab grouping is appropriate here because tiers belong conceptually together.

### CurrencyFlipPanel auto-refresh
  QTimer(_AUTO_REFRESH_INTERVAL_MS=5min) starts/stops via QCheckBox toggled signal.
  Checking the box triggers _start_calculate() immediately and starts the timer.
  _on_auto_toggle() handles both start and stop.
  Timer is owned by the panel (self._auto_timer) so it lives as long as the panel.

### VendorRecipesPanel / ScarabPanel follow established patterns
  Both follow: _load_*() → QVBoxLayout with filter row + legend row + QScrollArea.
  Filter button active state: btn.setProperty("active",...) + unpolish/polish cycle.
  This is now the standard pattern for all static-data Info panels.

### BreachPanel / DeliriumPanel / CurrencyRefPanel — Round 4 static panels (Session 27)
  All three follow the same pattern as BestiaryPanel, ExpeditionPanel, etc.:
  _load_*() reads JSON, QVBoxLayout with search + optional filter row + QScrollArea.
  BreachPanel: left border colored by element; complex multi-section card layout.
  DeliriumPanel: mechanic_note + simulacrum_note stored in JSON root, shown as footer labels
    (not inside reward_types array) so always visible regardless of search state.
  CurrencyRefPanel: 8 category filter buttons with distinct colors; font-size 9px to fit row.

### Info group tab count (Session 27)
  9 tabs in Info group after H1-H3 addition (Bestiary/Expedition/Syndicate/Vendor/Scarabs/
  Breach/Delirium/Currency/Settings). Qt scroll buttons (setUsesScrollButtons(True)) handle
  overflow. _INFO_SETTINGS is now index 8. Shifts by +1 each expansion round.

## Session 28 Additions

### New data files
- data/incursion_rooms.json — 18 Incursion temple room chains
  Schema: {t1, t2, t3, category, priority, drops, notes}
  Valid priorities: must_have, high, medium, low
  Also: tips[] array
- data/fossils.json — 25 Delve fossils + resonator reference
  Schema: {name, rarity, min_depth, adds_tags, blocks_tags, effect, crafting_use, notes}
  Valid rarities: common, uncommon, rare, very_rare
  Also: resonators{} dict (Primitive/Potent/Powerful/Prime Alchemical Resonator), tips[]
- data/maven_invitations.json — 6 Maven invitations
  Schema: {name, difficulty, witness_groups[], reward, notes}
  witness_groups schema: {boss, found_in, notes}
  Valid difficulties: Beginner, Intermediate, Advanced, Endgame (pinnacle)
  Also: maven_fight{requirement, access, rewards, notes}, how_maven_works, tips[]

### IncursionPanel priority filter (Session 28)
  Same pattern as CurrencyRefPanel category filter. Button label -> key mapping via
  lower() + replace(" ","_"). Priority color map:
    must_have=RED (#e05050), high=ORANGE (#e8864a), medium=TEAL (#4ae8c8), low=DIM (#8a7a65)
  Cards show T1->T2->T3 chain (T3 in ACCENT gold), priority badge, and category tag.

### FossilPanel adds/blocks design (Session 28)
  adds_tags and blocks_tags shown on a single QHBoxLayout row.
  Row is omitted entirely if both lists are empty (Shuddering, Perfect, Fractured fossils
  work via mod bias or special mechanics, not tag filtering).
  Rarity border colors: common=TEAL, uncommon=ACCENT, rare=ORANGE, very_rare=RED.

### MavenPanel nested search (Session 28)
  Search checks top-level fields first, then iterates witness_groups[] on each invitation.
  Uses break after first matching witness_group to avoid appending an invitation twice.
  maven_fight footer label is placed after the scroll area (not inside it) so it is
  always visible regardless of search state. Pattern parallels DeliriumPanel footer.

### Info group tab count (Session 28)
  12 tabs after I1-I3 addition (Bestiary/Expedition/Syndicate/Vendor/Scarabs/Breach/
  Delirium/Currency/Incursion/Fossils/Maven/Settings).
  _INFO_SETTINGS is now index 11.

### Info group tab count (Session 33)
  27 tabs after N1-N3 addition:
  Bestiary/Expedition/Syndicate/Vendor/Scarabs/Breach/Delirium/Currency/Incursion/Fossils/
  Maven/Metamorph/Harvest/Rogues/Sanctum/Rare Mods/Blight/Essences/Fragments/Pantheon/
  Flasks/Vaal/Corrupt/Ascend/Keystones/Bosses/Settings
  _INFO_SETTINGS is now index 26.

### Ascendancy panel base-class color scheme (Session 33)
  Base class colors serve dual purpose: filter button active color AND card left-border color.
  Marauder=RED, Ranger=GREEN, Witch=PURPLE, Duelist=YELLOW, Templar=TEAL, Shadow=BLUE, Scion=ACCENT.
  Pattern consistent with category-filtered panels (unique_flask, map_boss, etc.).

### Keystones panel no-category-filter design (Session 33)
  Keystones don't have meaningful categories (unlike flask DPS/Defense/Utility or boss Guardian/Conqueror).
  Search-only filtering is appropriate because the primary lookup pattern is by name or effect keyword.
  20 entries is a manageable number to scroll without category subdivision.

### Map boss category colors (Session 33)
  Shaper Guardian=BLUE (cold/ethereal), Elder Guardian=PURPLE (void/chaos), Conqueror=TEAL,
  Pinnacle=ACCENT (gold/prestige). Color choices reinforce the thematic identity of each group.
