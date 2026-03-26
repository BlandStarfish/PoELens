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

## Expansion Roadmap Round 3 (Auto-Approved 2026-03-25)

These features were auto-approved after all F1–F3 items reached completion. Implement in priority order listed.

### G1. Syndicate Member Planner ✅ IMPLEMENTED (Session 25)
- Static reference + optional manual tracking for Betrayal/Syndicate encounters
- Lists all 22 Syndicate members: their division affinities (Transportation, Research, Fortification, Intervention), safehouse rewards per division, and intel rewards
- Search by member name, reward type, or division
- Optional manual tracker: user can note which member is in which division slot for the current league
- Data source: data/syndicate_members.json (static, curated from GGG data)
- ui/widgets/syndicate_panel.py; add to Info group
- **Rationale:** Betrayal is permanent; players frequently need to look up "which member gives which reward" and plan their division placements. Having it in the overlay eliminates alt-tabbing to the wiki mid-encounter.

### G2. Vendor Recipe Browser ✅ IMPLEMENTED (Session 26)
- Static reference for all important PoE vendor recipes
- Categories: Currency recipes (chromatics, fusings, etc.), Leveling recipes (flasks, links), Quality recipes (whetstones, scraps), Unique recipes (specific uniques from vendor)
- Search by ingredient or result
- Data source: data/vendor_recipes.json (static, curated, 21 recipes)
- ui/widgets/vendor_recipes_panel.py; added to Info group as "Vendor" tab
- **Rationale:** Vendor recipes are an always-available resource optimization; players frequently look up "what do I vendor for X?" Having it in the overlay during play is more convenient than alt-tabbing.

### G3. Scarab Browser ✅ IMPLEMENTED (Session 26)
- Static reference for all PoE scarab types and their effects
- Shows: scarab mechanic, tier (Rusted/Polished/Gilded/Winged), effect description, which Atlas passive cluster synergizes
- Filter by tier; search by mechanic, effect, or atlas passive
- Grouped by mechanic (one card per mechanic, tiers listed within)
- Data source: data/scarabs.json (static, curated, 13 mechanics × 4 tiers = 52 scarabs)
- ui/widgets/scarab_panel.py; added to Info group as "Scarabs" tab
- **Rationale:** Scarabs replaced maps as the primary Atlas economy driver; players choosing which scarabs to run benefit from a quick effect reference without leaving the game window.

---

## Expansion Roadmap Round 5 (Auto-Approved 2026-03-25)

These features were auto-approved after all H1–H3 items reached 9+/10 completion. Implement in priority order listed.

### I1. Incursion Temple Room Reference ✅ IMPLEMENTED (Session 28)
- Static reference for all 18 Alva temple room chains (T1 → T2 → T3)
- Each entry shows: full upgrade chain names, T3 drop summary, upgrade priority (must_have/high/medium/low), category, and notes
- Priority filter: Must Have / High / Medium / Low + full-text search
- Data source: data/incursion_rooms.json (18 room chains, curated)
- ui/widgets/incursion_panel.py; added to Info group as "Incursion" tab
- **Rationale:** Incursion is a permanent mechanic. During Incursion encounters, players must decide in real time which architect to kill (keeping one room chain, removing the other). A quick priority reference eliminates guesswork and maximises temple value.

### I2. Delve Fossil Guide ✅ IMPLEMENTED (Session 28)
- Static reference for all major Delve fossils (25 entries) with add tags, block tags, min depth, and crafting applications
- Rarity filter: Common / Uncommon / Rare / Very Rare + full-text search (name, tag, crafting use)
- Resonator slot reference (Primitive through Prime) shown as compact header row
- Data source: data/fossils.json (25 fossils, resonators, tips)
- ui/widgets/fossil_panel.py; added to Info group as "Fossils" tab
- **Rationale:** Delve fossil crafting is a premier crafting method. The adds/blocks tag system is complex and not visible in-game. Having a searchable fossil reference in the overlay ("which fossil blocks chaos?") saves significant time vs wiki lookups.

### I3. Maven Boss Witness Guide ✅ IMPLEMENTED (Session 28)
- Static reference for all 6 Maven invitations: witness requirements, how to access each boss, reward summary
- Full-text search across invitation names, boss names, and access locations
- Maven fight unlock requirements shown as always-visible footer
- Data source: data/maven_invitations.json (6 invitations, maven_fight, tips)
- ui/widgets/maven_panel.py; added to Info group as "Maven" tab
- **Rationale:** Maven progression requires completing specific sets of boss witnesses. Players frequently forget which invitation requires which bosses, or how to access fragment-gated bosses (Shaper, Elder, Breach Lords). An in-overlay reference replaces repeated wiki trips.

---

## Expansion Roadmap Round 6 (Auto-Approved 2026-03-25)

These features were auto-approved after all I1–I3 items reached 9+/10 completion. Implement in priority order listed.

### J1. Metamorph Catalyst Reference ✅ IMPLEMENTED (Session 29)
- Static reference for all 12 Metamorph catalyst types
- Each entry shows: which modifier category the catalyst improves, example mods affected, best build use case, and which organ family to target for drops
- Full-text search across catalyst name, improves, examples, best_for, organ_source
- Data source: data/metamorph_catalysts.json (12 catalysts, curated)
- ui/widgets/metamorph_panel.py; added to Info group as "Metamorph" tab
- **Rationale:** Catalysts add quality to specific mod categories on jewellery. Players frequently need "which catalyst improves life?" or "which organ gives Fertile Catalyst?" without leaving the game window.

### J2. Harvest Craft Reference ✅ IMPLEMENTED (Session 29)
- Static reference for all major Harvest craft operations: Reforge, Augment, Remove/Add, Set Numeric Value, Split/Duplicate, Enchant
- Each craft shows: effect, category badge, value tier (Extremely High → Low), lifeforce requirement, and notes
- Category filter buttons + full-text search
- Data source: data/harvest_crafts.json (33 crafts across 5 categories, curated)
- ui/widgets/harvest_panel.py; added to Info group as "Harvest" tab
- **Rationale:** Harvest crafting is a premier crafting method with complex semantics. Players need to quickly recall "what does Reforge Keeping Prefixes do?" and "which crafts need Sacred Lifeforce?" during active crafting sessions.

### J3. Heist Rogue Skills Quick Reference ✅ IMPLEMENTED (Session 29)
- Static reference for all 11 Heist rogues: primary/secondary job, max level caps, specialty description, reward type, and usage notes
- Job-type filter buttons (one per job skill) + full-text search
- Complements the existing Heist Blueprint Organizer with rogue-level guidance
- Data source: data/heist_rogues.json (11 rogues, curated)
- ui/widgets/heist_rogues_panel.py; added to Info group as "Rogues" tab
- **Rationale:** Heist planning requires knowing which rogue has which job skill and at what level. Players forget which rogues are interchangeable (Tullina vs Vinderi for Trap Disarmament) and which are unique specialists (Tibbs, Gianna, Nenet). An in-overlay reference replaces repeated wiki trips.

---

## Expansion Roadmap Round 7 (Auto-Approved 2026-03-25)

These features were auto-approved after all J1–J3 items reached 9+/10 completion. Implement in priority order listed.

### K1. Sanctum Affliction & Boon Reference ✅ IMPLEMENTED (Session 30)
- Static reference for all major Sanctum afflictions (penalties) and boons (bonuses)
- Each affliction shows: severity (Critical/Dangerous/Moderate/Minor), category, effect, and strategic notes
- Each boon shows: value tier (High/Medium/Low), category, effect, and usage notes
- Section toggle (Both/Afflictions/Boons) + full-text search
- Data source: data/sanctum_afflictions.json (20 afflictions, 12 boons, curated)
- ui/widgets/sanctum_panel.py; added to Info group as "Sanctum" tab
- **Rationale:** The Sanctum is a permanent mechanic with a complex affliction/boon system. Players frequently need "what does Blind Devotion do?" or "which boon counters Eroding Soul?" during active runs. An in-overlay reference replaces alt-tabbing to the wiki mid-floor.

### K2. Rare Mod Reference ✅ IMPLEMENTED (Session 30)
- Static reference for 25 Archnemesis-style rare monster modifiers integrated into PoE core
- Each mod shows: danger level (Extreme/High/Moderate/Low), category, effect, dangerous combo warnings, and tactical notes
- Danger level filter buttons + full-text search
- Data source: data/rare_mods.json (25 mods, curated)
- ui/widgets/rare_mods_panel.py; added to Info group as "Rare Mods" tab
- **Rationale:** Archnemesis mods (now core rare modifiers) can be lethal if the player doesn't know what they do. A quick reference ("Vampiric heals on hit — use DoT") prevents unexpected deaths to unfamiliar mod combinations.

### K3. Blight Oil Reference ✅ IMPLEMENTED (Session 30)
- Static reference for all 11 Blight oil tiers (Clear through Opalescent) with rarity, market value, and usage notes
- Key notable anoint recipes (Constitution, Divine Flesh, Resolute Technique, etc.) with oil combinations and value tier
- Section toggle (Both/Oils/Anoints) + full-text search
- Anoint mechanic footer explaining amulet/ring/blighted map uses
- Data source: data/blight_oils.json (11 oils, 11 key anoints, curated)
- ui/widgets/blight_panel.py; added to Info group as "Blight" tab
- **Rationale:** Blight Oil anointing is a significant character power lever. Players frequently ask "which oils do I need for X notable?" and "is Opalescent Oil worth saving?" Having it in the overlay prevents unnecessary wiki lookups during crafting sessions.

---

## Expansion Roadmap Round 8 (Auto-Approved 2026-03-25)

These features were auto-approved after all K1–K3 items reached 9+/10 completion. Implement in priority order listed.

### L1. Essence Reference ✅ IMPLEMENTED (Session 31)
- Static reference for all 20 Essence types with stat focus, guaranteed mod, best slots, and crafting use
- Standard Essences (Weeping through Deafening) plus 4 Delirium Essences (Horror/Hysteria/Insanity/Delirium)
- Category filter (Life/Physical/Cold/Fire/Lightning/Chaos/Utility/Defense/Delirium) + full-text search
- Cards show: stat category, tier range, key mod, primary slots, best_for, and notes
- Data source: data/essences.json (20 essences, curated)
- ui/widgets/essence_panel.py; added to Info group as "Essences" tab
- **Rationale:** Essence crafting requires knowing which Essence guarantees which mod on which slot. "Which Essence gives movement speed on boots?" is a frequent question. In-overlay reference prevents wiki lookups during active crafting sessions.

### L2. Fragment Sets Reference ✅ IMPLEMENTED (Session 31)
- Static reference for all major Vaal/Shaper/Elder/Breach/Pantheon fragment sets
- Each entry shows: boss name, fragment list, area level, how to obtain fragments, notable drops, and notes
- Type filter (Vaal/Shaper/Elder/Breach/Pantheon) + full-text search
- Includes: Apex of Sacrifice, The Alluring Abyss, The Shaper's Realm, Elder, all 5 Breach lords, Divine Vessel
- Data source: data/fragment_sets.json (10 sets, curated)
- ui/widgets/fragment_panel.py; added to Info group as "Fragments" tab
- **Rationale:** Fragment combinations for endgame encounters are complex and easily forgotten between leagues. Players frequently need "which 4 fragments open Shaper?" or "how many Chayula splinters?" during active play.

### L3. Pantheon Powers Reference ✅ IMPLEMENTED (Session 31)
- Static reference for all 4 Major Gods and 8 Minor Gods with base powers, upgrade requirements, and defensive use cases
- Each god shows: unlock method, defensive speciality, base powers, upgrade powers with capture target + map name, and notes
- Section toggle (Both/Major/Minor) + full-text search across names, powers, and capture targets
- Footer swap tip ("swap freely from any town")
- Data source: data/pantheon_powers.json (4 major, 8 minor, curated)
- ui/widgets/pantheon_panel.py; added to Info group as "Pantheon" tab
- **Rationale:** The Pantheon capture system requires killing specific map bosses with a Divine Vessel. Players frequently ask "which Minor God counters Poison?" or "which map do I capture Shakari's upgrade from?" An in-overlay reference eliminates wiki trips and reminds players to swap defensively for specific encounters.

---

## Expansion Roadmap Round 9 (Auto-Approved 2026-03-25)

These features were auto-approved after all L1–L3 items reached 9+/10 completion. Implement in priority order listed.

### M1. Unique Flask Reference ✅ IMPLEMENTED (Session 32)
- Static reference for 18 important unique flasks — effect, best builds, when to use, and value tier
- Category filter (DPS / Defense / Utility) + full-text search across name, base, effect, builds, notes
- Cards show: flask name (gold), base type, category badge, value tier, effect, when to use (green), best builds (teal), notes (dim)
- Data source: data/unique_flasks.json (18 flasks, curated)
- ui/widgets/unique_flask_panel.py; added to Info group as "Flasks" tab
- **Rationale:** Unique flask selection is one of the most impactful character optimisation decisions. Players frequently ask "what does Dying Sun do?" or "when should I use Progenesis vs Forbidden Taste?" Having it in the overlay prevents wiki lookups during build setup.

### M2. Vaal Skill Reference ✅ IMPLEMENTED (Session 32)
- Static reference for 20 Vaal skills — element, soul requirements (normal/merciless), effect, when to use, best builds, and notes
- Element filter buttons (All / Lightning / Fire / Cold / Physical / Chaos / Aura / Armour) + full-text search
- Cards show: skill name, element badge, soul cost, effect, when to use (green), best builds (teal), notes (dim)
- Data source: data/vaal_skills.json (20 skills, curated)
- ui/widgets/vaal_skill_panel.py; added to Info group as "Vaal" tab
- **Rationale:** Vaal skills have unique soul requirements and usage windows that are easy to forget. "Which Vaal skill needs fewest souls?" and "when do I pop Vaal Haste vs Vaal Molten Shell?" are common questions during boss progression.

### M3. Item Corruption Reference ✅ IMPLEMENTED (Session 32)
- Static reference for what Vaal Orb corruption does to each item type (Gems, Maps, Equipment, Flasks, Jewels)
- Each entry shows outcome possibilities with probability tiers (Always/High/Medium/Low) and explanatory notes
- Notable Corrupted Implicits section: Corrupted Blood immunity, explode on kill, Vulnerability on hit, Elemental Weakness on hit
- Section toggle (Both / Outcomes / Implicits) + full-text search
- Data source: data/corruption_reference.json (6 item types, 4 notable implicits, curated)
- ui/widgets/corruption_panel.py; added to Info group as "Corrupt" tab
- **Rationale:** Corruption is one of the most consequential and irreversible actions in PoE. Players constantly ask "what can happen if I Vaal this gem/map/item?" Having an outcome reference in the overlay prevents costly mistakes and teaches players about valuable outcomes like white sockets and Corrupted Blood immunity jewels.

---

## Expansion Roadmap Round 10 (Auto-Approved 2026-03-25)

These features were auto-approved after all M1–M3 items reached 9+/10 completion. Implement in priority order listed.

### N1. Ascendancy Class Reference ✅ IMPLEMENTED (Session 33)
- Static reference for all 19 Ascendancy classes across 7 base classes (Marauder/Ranger/Witch/Duelist/Templar/Shadow/Scion)
- Each entry shows: base class, playstyle description, key notable passives, primary defence layer, and top builds
- Base class filter buttons (color-coded per base class) + full-text search
- Data source: data/ascendancy_classes.json (19 classes, curated)
- ui/widgets/ascendancy_panel.py; added to Info group as "Ascend" tab
- **Rationale:** Ascendancy choice is the most impactful character decision. New and returning players frequently ask "which Ascendancy for Summons?" or "is Elementalist or Occultist better for poison?" Having it in the overlay prevents wiki trips during character creation and league planning.

### N2. Keystone Passive Reference ✅ IMPLEMENTED (Session 33)
- Static reference for 20 major Keystone passives on the main skill tree
- Each entry shows: keystone name, effect (positive + trade-off), which builds require it, which builds are broken by it, and location on tree
- Full-text search across name, effect, trade-off, and build types
- Data source: data/keystones.json (20 keystones, curated)
- ui/widgets/keystones_panel.py; added to Info group as "Keystones" tab
- **Rationale:** Keystones fundamentally change how a build works. "What does Eldritch Battery do?" and "does Iron Reflexes work with evasion builds?" are common questions. An in-overlay reference makes keystones understandable without leaving the game.

### N3. Map Boss Quick Reference ✅ IMPLEMENTED (Session 33)
- Static reference for 16 key endgame map bosses — 4 Shaper Guardians, 4 Elder Guardians, 4 Conquerors, 4 Pinnacle bosses (Sirus, Maven, Shaper, Elder)
- Each entry shows: boss name, map, key mechanics, dangerous abilities, recommended preparation, and notes
- Category filter (Shaper Guardian/Elder Guardian/Conqueror/Pinnacle) + full-text search
- Data source: data/map_bosses.json (16 bosses, curated)
- ui/widgets/map_boss_panel.py; added to Info group as "Bosses" tab
- **Rationale:** Many players are unfamiliar with mechanics for specific map bosses, especially after returning from a break. A quick "what does this boss do and how do I prepare?" reference reduces unnecessary deaths to mechanics that could have been anticipated.

---

## Expansion Roadmap Round 4 (Auto-Approved 2026-03-25)

These features were auto-approved after all G1–G3 items reached 9+/10 completion. Implement in priority order listed.

### H1. Breach Domain Reference ✅ IMPLEMENTED (Session 27)
- Static reference for all 5 Breach domains (Xoph/Tul/Esh/Uul-Netol/Chayula)
- Each entry shows: element, splinter name, breachstone name, keystone + effect, blessing + effect, notable unique items, build notes
- Color-coded by element (Fire=orange, Cold=teal, Lightning=gold, Physical=gray, Chaos=purple)
- Full-text search across deity, element, keystone, blessing, and unique names
- Breachstone tier legend (Normal → Charged → Enriched → Pure → Flawless)
- Data source: data/breaches.json (5 entries, curated)
- ui/widgets/breach_panel.py; added to Info group as "Breach" tab
- **Rationale:** Breach is a permanent mechanic. Players farming splinters or planning around blessings frequently need to check which deity gives which keystone/blessing. Having it in the overlay eliminates alt-tabbing mid-map.

### H2. Delirium Reward Type Reference ✅ IMPLEMENTED (Session 27)
- Static reference for all Delirium reward cluster types (Currency, Jewels, Maps, Scarabs, Gems, etc.)
- Each entry shows: description, high-value drops, best strategy, notes
- Full-text search across reward type name and drop descriptions
- Simulacrum splinter note always visible (collect 300 to form Simulacrum fragment)
- Data source: data/delirium_rewards.json (12 types, curated)
- ui/widgets/delirium_panel.py; added to Info group as "Delirium" tab
- **Rationale:** Delirium Orb stacking is a core endgame strategy. Choosing which cluster type to apply requires knowing what each type generates. Delirium is permanent and the reward type system is complex enough to warrant a reference.

### H3. Currency Quick Reference ✅ IMPLEMENTED (Session 27)
- Static reference for all major PoE currency orbs: effect, primary crafting use, notes
- Category filter: Basic, Crafting, Trade, Sockets, Maps, Unique, Flasks, Pantheon
- Full-text search across name, effect, use, and notes
- 25 currencies covering everything from Scrolls of Wisdom to Mirror of Kalandra
- Data source: data/currency_reference.json (25 entries, curated)
- ui/widgets/currency_ref_panel.py; added to Info group as "Currency" tab
- **Rationale:** New players frequently need to look up what a currency orb does before using it. Experienced players benefit from edge-case reminders (e.g., Scouring vs Annulment, Enkindling vs Instilling). Faster than alt-tabbing to the wiki.

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
