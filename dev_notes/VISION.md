# ExileHUD — Vision Document

## Original Vision & Goals

ExileHUD is a **TOS-compliant** Path of Exile overlay that provides real-time information and quality-of-life tools without violating GGG's Terms of Service. It runs as a transparent, always-on-top PyQt6 window. It never reads game memory, sends input events to the game process, intercepts packets, or does anything that gives an unfair competitive advantage.

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

### 2. Passive Tree Viewer ✅ IMPLEMENTED (partial)
- Full PoE passive tree rendered in QGraphicsView
- Pan (drag) + zoom (scroll wheel)
- Node hover tooltip (name, type, stats)
- Click pins node detail
- Search bar highlights matching nodes
- Color-coded by node type (keystone, notable, normal, jewel, mastery, ascendancy)
- Quest integration: shows quest point summary on tree panel ✅ (added Session 1)
- Tree data downloaded from GGG CDN or official export repo on first run
- **Missing: Player allocated node tracking (requires stash/character API or manual input)**
- **Priority: HIGH — core viewing done; player-allocated nodes future work**

### 3. Price Checking ✅ IMPLEMENTED
- Ctrl+C in PoE copies item tooltip to clipboard
- Hotkey (default Ctrl+D) reads clipboard, parses item name/type/rarity
- poe.ninja lookup (fast, cached, TTL-based)
- Official trade API search (live listings, top 5 prices)
- Displays ninja price + live listings + trade link
- **Priority: HIGH — complete and functional**

### 4. Currency Per Hour ✅ IMPLEMENTED (manual input)
- User manually enters current currency counts (stash + inventory)
- "Start Session" sets baseline; "Snapshot" records deltas
- Calculates per-currency rates and total chaos/hr via poe.ninja conversion
- **Missing: Stash tab API integration (would auto-read currency from official API)**
- **Priority: MEDIUM — works but manual entry is friction**

### 5. Crafting System ✅ IMPLEMENTED
- Cheat sheet browser: 8 methods (alteration spam, essence, fossil, divine, harvest, exalt slam, metacraft, chaos spam)
- Each method shows steps, materials, and live cost estimate from poe.ninja
- Personal task queue: add items with chosen method + quantity
- Task management: mark done, remove, reorder
- Total pending queue cost display
- **Priority: MEDIUM — complete for core use cases**

### 6. Map Overlay ✅ IMPLEMENTED (v2)
- Zone identity card: name (gold, prominent), act, area level, waypoint status, boss info
- Zone-specific notes for mechanically significant zones (Kitava resistance warnings, key quest hints)
- Act-based resistance penalty reminder for acts 6-10 (static, always accurate)
- Session zone history (last 15 zones, timestamped, towns dimmed)
- Triggered by zone_change events from Client.txt
- Data source: static data/zones.json (~120 campaign zones, Acts 1-10)
- **Missing: Atlas map mods data (endgame content, would require poedb scrape or community data)**
- **Priority: LOW for atlas mods — campaign data complete**

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
- No process injection, memory reading, input simulation, or packet interception — ever
- Overlay is passive display only

## Target User Experience

A player can open ExileHUD during a session and:
1. See which quest passive points they haven't collected yet
2. Browse and search the full passive tree
3. Price check any item in under 2 seconds
4. Track how much currency they're earning per hour
5. Follow a crafting method step-by-step with live cost estimates

The overlay should feel like a natural part of the PoE experience — dark-themed, PoE-gold accents, unobtrusive.
