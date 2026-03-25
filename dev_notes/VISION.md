# PoELens — Vision Document

## Original Vision & Goals

PoELens is a **TOS-compliant** Path of Exile overlay that provides real-time information and quality-of-life tools without violating GGG's Terms of Service. It runs as a transparent, always-on-top PyQt6 window. It never reads game memory, sends input events to the game process, intercepts packets, or does anything that gives an unfair competitive advantage.

The overlay is organized as tabs (one per module) inside a frameless window, positioned top-right by default, draggable, and opacity-adjustable.

---

## Feature Roadmap

### 1. Quest Passive Point Tracker ✅ IMPLEMENTED
- Lists all PoE quests that award or deduct passive skill points (Acts 1–10)
- Tracks completion via Client.txt log events (passive, read-only)
- Manual toggle for each quest (for new characters or offline tracking)
- Shows earned/deducted/net totals and remaining available points
- Guides user to next uncollected quest with step-by-step directions
- **Priority: HIGH — complete and functional**

### 2. Passive Tree Viewer ✅ IMPLEMENTED
- Full PoE passive tree rendered in QGraphicsView
- Pan (drag) + zoom (scroll wheel)
- Node hover tooltip (name, type, stats)
- Click pins node detail
- Search bar highlights matching nodes
- Color-coded by node type (keystone, notable, normal, jewel, mastery, ascendancy)
- Quest integration: shows quest point summary on tree panel ✅ (added Session 1)
- Tree data downloaded from GGG CDN or official export repo on first run
- **Build import: paste PoE tree URL or Path of Building code to highlight allocated nodes** ✅ (added Session 7)
  - Accepts full PoE tree URL (from in-game export Ctrl+C in skill tree window)
  - Accepts Path of Building build code (zlib XML base64)
  - Allocated nodes shown in bright gold, distinct from search highlights
  - Allocation and search highlights coexist without interference
- **Character API sync: auto-import allocated nodes from logged-in PoE account** ✅ (added Session 10/11)
  - Uses OAuth account:characters scope
  - Dropdown to select character; imports passive hashes directly from GGG API
- **Priority: HIGH — complete and functional**

### 3. Price Checking ✅ IMPLEMENTED
- Ctrl+C in PoE copies item tooltip to clipboard
- Hotkey (default Ctrl+D) reads clipboard, parses item name/type/rarity
- poe.ninja lookup (fast, cached, TTL-based)
- Official trade API search (live listings, top 5 prices)
- Displays ninja price + live listings + trade link
- **Clipboard currency detection**: Ctrl+C on a currency stack auto-fires on_currency_detected callback ✅ (added Session 10/11)
- **Priority: HIGH — complete and functional**

### 4. Currency Per Hour ✅ IMPLEMENTED (manual + optional OAuth auto-fill)
- User manually enters current currency counts (stash + inventory)
- "Start Session" sets baseline; "Snapshot" records deltas
- Calculates per-currency rates and total chaos/hr via poe.ninja conversion
- Cross-session aggregation: 7-day and all-time average chaos/hr from history
- **Optional OAuth auto-fill (Session 6)**: if oauth_client_id is configured in config.json,
  "Connect PoE Account" button opens browser for GGG OAuth 2.1 PKCE auth,
  "Auto-fill from Stash" then reads currency amounts directly from the official stash tab API
- **Clipboard currency detection (Session 10/11)**: Ctrl+C on a currency stack in-game auto-populates the matching spinbox
- **Experimental OCR scan (Session 10/11)**: "Scan Stash Tab" button (shown only when winrt/mss/Pillow installed) captures screen and OCRs currency counts
- **Priority: MEDIUM — manual entry works; OAuth auto-fill improves UX significantly**

### 5. Crafting System ✅ IMPLEMENTED
- Cheat sheet browser: 9 methods (alteration spam, essence, fossil, divine, harvest, exalt slam, metacraft, chaos spam, recombinator)
- Each method shows steps, materials, and live cost estimate from poe.ninja
- Personal task queue: add items with chosen method + quantity
- Task management: mark done, remove, reorder
- Total pending queue cost display
- **Priority: MEDIUM — complete for core use cases**

### 7. XP Rate Tracker ✅ IMPLEMENTED (Session 13)
- Tracks experience per hour for the current session
- Uses Character API (OAuth, `account:characters` scope) to poll XP/level
- Polls every 5 min via QTimer + on zone_change events (120s cooldown)
- Displays: current character, level, XP/hr, XP gained this session, elapsed time
- Level-up detection: shows "Level N → M" when character leveled during session
- Requires OAuth connection (shows connect prompt if not authenticated)
- Time-to-level deferred (requires confirmed XP-per-level table)

### 8. Chaos Recipe Counter ✅ IMPLEMENTED (Session 13)
- Scans equipment stash tabs via OAuth stash API to count rare item sets
- Full set = helmet + chest + gloves + boots + belt + 2×ring + amulet + weapon slot
- Weapon slot = 1× two-handed OR 1× one-handed + 1× offhand
- Tracks chaos-tier (ilvl 60-74), regal-tier (ilvl 75+), and any-tier counts per slot
- Shows which slots are missing for the next complete set
- User-triggered scan (respects API rate limits)

### 9. Build Notes Panel ✅ IMPLEMENTED (Session 13)
- Personal plain-text notepad inside the overlay
- Saves to state/notes.json (gitignored)
- Boss strategies, league goals, build reminders, map target lists
- No external dependencies, no API calls

---

## Expansion Roadmap (Auto-Approved 2026-03-25)

These features were auto-approved by the development agent after all original roadmap items reached 9+/10 completion. Implement in priority order listed.

### E1. Divination Card Tracker ✅ IMPLEMENTED (Session 18)
- Scan DivinationStash tab via OAuth Stash API for divination card stacks
- For each card, show: current stack count vs full stack size, completion %, and chaos value
- Sort by completion % — groups: near-complete (≥75%), in-progress, singles
- poe.ninja DivinationCard endpoint provides stack_size + chaos value (no static file needed)
- modules/div_cards.py + ui/widgets/div_panel.py + stash_api.get_divination_items()
- **Rationale:** Divination farming is a core PoE endgame activity; completing card sets is satisfying and this makes it trackable without leaving the overlay

### E2. Atlas Map Completion Tracker ✅ IMPLEMENTED (Session 18)
- Tracks which atlas map zones have been entered via Client.txt zone_change events
- Cross-references zones.json atlas entries; persists in state/atlas_progress.json
- Display: visited/total count, % bar, unvisited maps grouped by tier
- No new APIs — purely Client.txt + existing zones.json
- modules/atlas_tracker.py + ui/widgets/atlas_panel.py
- **Rationale:** Natural extension of the map overlay; "which maps haven't I done yet?" is a common player question, and all data is already in the codebase

### E3. Bestiary Recipe Browser ✅ IMPLEMENTED (Session 18)
- Static reference tool: browse Bestiary crafting recipes by modifier or beast name
- Show: beast names (color-coded by faction), result, category, notes
- Search/filter by modifier, result, category, or beast name
- Data source: data/bestiary_recipes.json (25 recipes curated from GGG data)
- No API calls — purely static data, zero latency
- ui/widgets/bestiary_panel.py
- **Rationale:** Bestiary is permanently in PoE; players frequently look up "which beast gives this mod" — having it in the overlay is more convenient than alt-tabbing to the wiki

### E4. Heist Blueprint Organizer ✅ IMPLEMENTED (Session 19)
- Scan stash tabs for Heist Contracts and Blueprints via stash API
- Group by rogue job type (Lockpicking, Agility, etc.) and show coverage
- For Blueprints: show which wings are unlocked, recommended rogues, target reward types
- Highlight high-value reward types (Replica Uniques, Trinkets, Currency)
- Uses existing OAuth + stash_api.py; adds minimal parsing logic for Heist item mods
- **Rationale:** Heist planning is an inventory management challenge; showing blueprint status in the overlay reduces the need to manually inspect each blueprint

### E5. Gem Level Planner ✅ IMPLEMENTED (Session 19)
- Read equipped gem data from the Character API (OAuth account:characters scope)
- Display: gem name, current level, current quality, XP to next level
- Highlight gems worth selling (high-level Awakened, 20/20 gems)
- Show total gem XP earned this session if polling is active
- Requires parsing the `items` field from character API response (already uses account:characters)
- **Rationale:** Leveling valuable gems in off-hand slots is a passive income source; a quick summary surfaces gems that are ready to sell without opening the character sheet

### E6. Map Stash Scanner ✅ IMPLEMENTED (Session 23)
- Scan MapStash tab via OAuth Stash API for all maps with rolled mod information
- Display: name, tier, rarity, IIQ/IIR/Pack Size bonus %, and full explicit mod list
- Grouped by tier descending, maps sorted alphabetically within each tier
- Unidentified maps shown with "(Unidentified)" indicator (no mod list)
- stash_api.get_map_items() + modules/map_stash.py + ui/widgets/map_stash_panel.py
- Tab: Endgame > MapStash
- **Rationale:** Closes the long-standing "map mod display" gap; players can scan their map stash and see exactly what affixes are on each map without opening the game stash

---

## Expansion Roadmap Round 2 (Auto-Approved 2026-03-25)

These features were auto-approved after all E1–E6 items reached completion. Implement in priority order listed.

### F1. Expedition Remnant Browser (HIGH)
- Static reference tool: browse all Expedition remnant keywords and what they do
- Search by keyword name or effect (e.g., "which keyword gives extra currency?")
- Data source: data/expedition_remnants.json (curated from GGG data / community sources)
- No API calls — purely static data, zero latency, always accurate
- ui/widgets/expedition_panel.py; add to Info group alongside Bestiary
- **Rationale:** Expedition is a permanent mechanic; players constantly need to look up what each remnant keyword does. Having it in the overlay is more convenient than alt-tabbing to the wiki during mapping.

### F2. Currency Flip Calculator (MEDIUM)
- Calculate the most profitable currency exchange opportunities using poe.ninja data
- Show top N flip pairs sorted by profit margin (e.g., "Buy 100 Chaos → sell as Alchs → +X% profit")
- Respects poe.ninja bulk exchange endpoint (already wired in poe_ninja.py)
- Pure calculation — no new API calls, reuses price data already in memory
- modules/currency_flip.py + ui/widgets/currency_flip_panel.py; add to Loot group
- **Rationale:** Currency flipping is a passive income activity many players do; surfacing profitable flips directly in the overlay saves time vs checking external tools

### F3. Lab Tracker (LOW)
- Track Normal/Cruel/Merciless/Eternal lab completion status for the current character
- Uses Client.txt zone_change events for lab area entries (same passive reading pattern as quest_tracker)
- Manual override toggle for each difficulty (for lab-runner characters or offline tracking)
- Shows Pantheon minor gods unlocked (passive note-taking, not automated)
- modules/lab_tracker.py + ui/widgets/lab_panel.py; add to Character group
- **Rationale:** Lab is required for ascendancy points every league; a quick checklist of which difficulties have been completed prevents accidentally running a lab you already cleared

---

### 6. Map Overlay ✅ IMPLEMENTED (v3)
- Zone identity card: name (gold, prominent), act/tier, area level, waypoint status, boss info
- Zone-specific notes for mechanically significant zones (Kitava resistance warnings, key quest hints, Pinnacle Guardian drops)
- Act-based resistance penalty reminder for acts 6-10 (static, always accurate)
- Session zone history (last 15 zones, timestamped, towns dimmed)
- Triggered by zone_change events from Client.txt
- Data source: static data/zones.json
  - ~120 campaign zones, Acts 1-10
  - ~100 atlas endgame maps, Tiers 1-17 (added Session 11)
  - Atlas maps display as "Tier N Map • Area level N • ✓ Waypoint"
  - History shows T{tier} prefix for atlas maps instead of Act number
- **Priority: LOW for atlas mods (map mod display) — zone identity complete**

### 10. Uninstaller / Cleaner ✅ IMPLEMENTED
- `Uninstall PoELens.bat` written to the install folder by the installer at install time
- Terminates any running PoELens process via `taskkill`
- Removes Desktop and Start Menu shortcuts
- Prompts for CONFIRM before deleting anything
- Recursively deletes the install folder (`rd /s /q`)
- Implemented as a Windows bat script (written by `_write_uninstaller()` in installer_gui.py)
- No registry entries exist to clean (installer never writes to registry)

---

## Technical Architecture Decisions

- **Framework**: PyQt6 (not tkinter for main UI — installer uses tkinter for zero-dep distribution)
- **Event bus**: ClientLogWatcher emits named events; all modules subscribe, none read the log directly
- **State persistence**: `state/profile.json` (quests, crafting queue, zone) + `state/currency_log.json`
- **Config**: `state/config.json` overrides `config.py` defaults; never touch source for user config
- **API strategy**: poe.ninja for fast cached prices, official trade API for live listings
- **Hotkeys**: `keyboard` library (fires even when PoE has focus)
- **Crash handling**: global excepthook → JSONL log + PyQt6 dialog
- **Auto-updater**: GitHub API SHA comparison → download ZIP → preserve state/ → restart
- **Passive tree data**: Downloaded from GGG CDN or fallback to official export repo

## TOS Compliance

- Read-only file access (Client.txt, clipboard)
- Only public official APIs (trade API, poe.ninja)
- OAuth 2.1 PKCE for account-scoped APIs (stash, characters) — fully GGG-approved
- Screen OCR is user-triggered only (same Tier 2 / passive-reading as Lailloken UI)
- No process injection, memory reading, input simulation, or packet interception — ever
- Overlay is passive display only

## Target User Experience

A player can open PoELens during a session and:
1. See which quest passive points they haven't collected yet
2. Browse and search the full passive tree (or import their current build)
3. Price check any item in under 2 seconds
4. Track how much currency they're earning per hour
5. Follow a crafting method step-by-step with live cost estimates
6. See zone info (act, level, boss, resistance notes) for any area they enter

The overlay should feel like a natural part of the PoE experience — dark-themed, PoE-gold accents, unobtrusive.
