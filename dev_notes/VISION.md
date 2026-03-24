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
