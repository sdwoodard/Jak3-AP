# Jak 3 Archipelago Progression, Logic, Checks, and Player-Options Design

**Canonical repository path:** `docs/design/progression-and-logic.md`
**Target:** OpenGOAL Jak 3 + Archipelago
**Document status:** implementation specification, design version 0.3
**Primary default:** tiered open mission board, simplified route authorizations, capability shuffle, `5 of 7` relic finale, finite sanity checks, and `accessibility: full`

This document is intended to be sufficiently explicit for a human developer or another AI model to implement, review, test, and extend a Jak 3 Archipelago world. It distinguishes three things that are often accidentally conflated:

1. **Permanent AP inventory** — items whose receipt must survive save/load, death, reconnect, mission restart, and native reward reconstruction.
2. **Mission state** — vehicles, actors, transformations, tutorials, and temporary powers that a mission script needs but which should not become permanent AP items.
3. **Location checks** — finite, monotonic accomplishments that may send an Archipelago item exactly once, regardless of mission replay or source-state resets.

The conclusions below are based primarily on OpenGOAL's decompiled Jak 3 task/reward/save sources, then cross-checked against detailed walkthroughs and item guides for intended-path requirements. Source code is authoritative for identifiers, persistence, and reward hooks; walkthrough evidence is used for human-playable route requirements; conservative implementation rules resolve remaining uncertainty.

For the default-only beta, `allow_experimental_checks: true` remains rejected.
Experimental names stay documented for future audited versions; the flag does
not opt the current generator into partially implemented tables.

---

## 1. Normative language and evidence labels

`MUST`, `MUST NOT`, `SHOULD`, and `MAY` are normative implementation terms.

| Label | Meaning |
| --- | --- |
| `S` | Explicit in the OpenGOAL task, reward-command, or save source. |
| `W` | Explicitly supported by an intended-path walkthrough or item guide. |
| `B` | Mission-equipment bootstrap requirement. |
| `I` | Conservative implementation decision or inference. |
| `X` | Experimental; runtime/source audit is still required before default enablement. |

A rule may deliberately be stricter than the theoretical minimum. Under `logic_difficulty: standard`, the priority is that an ordinary player can complete every enabled location by the intended route, not that every speedrun or damage-boost skip is recognized.

---

## 2. Executive decision

### 2.1 Exact default progression pool

The recommended default has **26 progression instances**:

- **8 route authorizations**.
- **Jetboard, Jetboard Launch, Invisibility Statues, Dark Bomb, Dark Strike, and Light Flight**.
- **3 copies of Progressive Wasteland Vehicle License**.
- **Blaster and Vulcan Fury** as interchangeable reliable-ranged alternatives.
- **7 native finale relics**, of which **5 are required**.

The same 147-location default creates **28 useful items** and therefore **93 filler slots** before trap replacement. The useful pool is fixed and auditable rather than being whatever happens not to be progression:

| Useful family | Count | Exact default members | Why useful rather than progression |
| --- | --- | --- | --- |
| Non-RANGED Morph Gun mods | 10 | Scatter Gun; Wave Concussor; Plasmite RPG; Beam Reflexor; Gyro Burster; Arc Wielder; Needle Lazer; Peace Maker; Mass Imploder; Super Nova | Combat variety and power; none is needed by Standard reachability. |
| Native ammo-capacity upgrades | 8 | Two upgrades for each of red, yellow, blue, and dark ammo | Capacity only; logic never assumes a minimum ammunition reserve. |
| Progressive Armor | 4 | Armor stages 1–4 | Survivability only; no mission or check requires health/armor routing. |
| Jetboard Zap | 1 | Jetboard Zap | Board combat/convenience; Launch, not Zap, is the verified traversal gate. |
| Light Jak utility powers | 3 | Light Regeneration; Flash Freeze; Light Shield | Recovery, crowd control, and survivability; no Standard access predicate. |
| Dark Blast | 1 | Dark Blast | Combat power; the Temple access requirement is Dark Bomb. |
| Ram 'Rod / Slam Dozer ownership | 1 | Permanent Ram 'Rod / Slam Dozer unlock | Task 68 supplies the mission vehicle; permanent ownership is free-roam convenience. |

The arithmetic is therefore `147 locations - 26 progression - 28 useful = 93 filler`. Secret upgrades and secret vehicles are **not** part of this 28-item first-release pool; they enter only under later audited options. Health, armor, ammo capacity, damage output, regeneration, shields, and resource abundance are never Standard access requirements.

### 2.2 Exact default check set

The recommended first full preset has **147 network locations**, plus one non-networked Victory event:

| Category | Count | Default |
| --- | ---: | --- |
| Story mission completions | 61 | Tasks 10–35 and 37–71 |
| Major stable native reward moments | 38 | Permanent/major story rewards; excludes setup, temporary add/remove nodes, and crystal-only nodes |
| Selected finite side challenges | 24 | Source task IDs 114–137 |
| Global Precursor Orb bundles | 24 | Thresholds 25 through 600 in steps of 25 |
| Locked Victory event | 1 event | Task 72 / configured goal; no random item |

To keep the default fun, global orb thresholds above **300** are created but marked `EXCLUDED` by default. They can send filler or traps, but cannot hold progression or useful items. Thus a player is not forced into all 600 orbs for key content unless `precursor_orb_progression_cap` is raised.

### 2.3 Rejected boundaries

The following tempting designs are rejected for the default:

- **One key per mission:** too many low-impact keys and self-lock opportunities.
- **Every basic gun satisfies ranged logic:** Scatter Gun is too short-ranged; Peace Maker has too little dark ammo to be the sole reliable Standard gate.
- **Armor or health as progression:** subjective survival logic and poor accessibility.
- **All Light/Dark powers as progression:** only Dark Bomb, Dark Strike, Invisibility Statues, and Light Flight have verified Standard access roles; the rest remain useful or excluded.
- **Every vehicle as progression:** exact mission vehicles are often scripted state; capability licenses give better pacing.
- **A separate one-use final key:** redundant with the `5 of 7` relic gate. The eighth route item instead opens a broad late-game Dark Maker sequence.
- **An eighth “Star Map” relic:** the command is declared, but the audited main reward table does not grant it and the native reward path used by the main story does not implement it as an ordinary story reward.
- **Repeatable enemy drops/crates as checks:** not finite and not safely idempotent.

---

## 3. Core design philosophies

### 3.1 Broad keys, branching content

A progression item should usually open multiple checks. Route authorizations represent mission-board access and safely initialized story state, not literal physical keys. The default graph keeps source order within a mission chain while allowing selected chapters to branch.

### 3.2 Capability, not exact vehicle inventory

Logic asks whether the player has a capability:

- Basic Wasteland travel.
- Long-jump traversal.
- Armed Wasteland combat.

Missions that are explicitly introductions to a particular vehicle temporarily supply that vehicle. Free-roam, Temple access, Stronghold access, and armed Wasteland content use permanent capability licenses.

### 3.3 Lesson missions cannot require their own reward

When a mission teaches a power mid-mission, the task starts without that permanent AP item. At the lesson node, the game grants a temporary overlay through mission completion. Later missions require the permanent AP item.

Examples:

- Task 11 teaches Dark Bomb/Dark Blast after its opening; it does not require shuffled Dark Bomb at mission start.
- Task 27 awards Invisibility Statues near its resolution and temporarily retains it for the return teleport.
- Task 29 awards Jetboard, Launch, and Zap; it does not require them.
- Task 42 teaches Dark Strike; it does not require Dark Strike at mission start.
- Task 61 teaches Light Flight; it does not require Light Flight at mission start.

### 3.4 Useful items remain meaningful

Weapons, armor, powers, and vehicles should materially improve play even when they are not logic. This makes remote items exciting without making the access graph subjective.

### 3.5 Finite, monotonic checks only

A location check MUST have a durable identity and become permanently complete. Replay, reload, task-node reset, or enemy respawn MUST NOT create another check.

### 3.6 AP inventory is authoritative

Native story code and save reconstruction may re-run reward commands. In AP mode, the persistent AP ledger wins. Every load, reconnect, mission exit, and bootstrap cleanup reconciles native inventory from the AP ledger.

### 3.7 Logical relics and native story props are separate

In `simplified_authorizations`, the seven AP relics are logical finale collectibles. Native scripts still expect specific passes, amulets, the Seal portal state, Cipher/story flags, and all five Astro-Viewer artifacts at fixed moments. The adapter maintains a **shadow native story-state layer** for those script/presentation dependencies. Shadow grants never create AP receipts, never increase `RELICS(n)`, and are removed or reconciled independently of the AP item ledger. `story_item_mode: canonical` disables this abstraction and instead uses exact native-item rules.

---

## 4. Archipelago `full` accessibility contract

`accessibility: full` is not a substitute for correct rules. It asks Archipelago's accessibility sweep to make every location in that player's world reachable and also make the game beatable. Any item that can appear in an access rule—including either side of an `OR`—must be classified as progression. `EXCLUDED` locations cannot receive progression or useful items.

The Jak 3 world MUST satisfy these invariants:

1. Every enabled network location is finite, monotonic, persistent, and idempotent.
2. Every enabled location is reachable in `get_all_state()` under its selected options.
3. Victory is reachable.
4. Every item referenced by a rule is progression-classified for that option set.
5. A reward/lesson check never requires the item taught at that check.
6. No route authorization can be available only inside the route it unlocks.
7. AP-delivered currency does not advance local-world collectible checks.
8. Native purchase costs are free or logically modeled; the default is free.
9. A source task with no durable completion state is not a network location unless the mod adds a durable AP flag.
10. Excluding a location changes placement eligibility, not its access rule. Under `accessibility: full`, an enabled `EXCLUDED` location still must be reachable; it merely cannot hold progression/useful items.
11. Shadow native story state never satisfies an AP item predicate or AP relic count.
12. Every option combination either generates with a tested rule set or fails early with a clear `OptionError`.

---

## 5. Logic vocabulary

The implementation should define these shared predicates rather than duplicating raw item names throughout rules:

```python
RANGED = has("Blaster") or has("Vulcan Fury")
BOARD_BOOST = has("Jetboard") and has("Jetboard Launch")
TEMPLE_ORACLE = has("Invisibility Statues") and has("Dark Bomb")
VEHICLE(n) = count("Progressive Wasteland Vehicle License") >= n
RELICS(n) = count_group("Finale Relics") >= n
DONE(task_id) = has(f"Mission Complete Event {task_id}")
```

`RANGED` deliberately excludes Scatter Gun and Peace Maker in Standard logic. `BOARD_BOOST` is separate from base-board access because task 30 explicitly uses the charged L1+X launch. `TEMPLE_ORACLE` models the intended, non-skip route. `DONE()` is a hidden locked event used by the generator. At runtime, the mission board uses the corresponding durable local task/AP-completion flag.

---
## 6. Exact progression items

### 6.1 Route authorizations

| Item | Count | Classification | Content opened | Decision |
| --- | --- | --- | --- | --- |
| Spargus Field Orders | 1 | progression | Tasks 14–24 and related Wasteland checks | Large early branch; required by the Temple convergence. |
| Temple Expedition Orders | 1 | progression | Tasks 25–34 | Separates Temple/Mines from general Spargus content. |
| Haven City Access | 1 | progression | Tasks 35–44 and Haven free roam | Creates the second early branch; runtime adapter initializes safe Act II world state. |
| Freedom League Orders | 1 | progression | Tasks 45–51 | Opens the mid-Haven branch after task 44. |
| Wasteland Artifact Intel | 1 | progression | Tasks 52–57 | Runs in parallel with Freedom League after task 44. |
| War Factory Coordinates | 1 | progression | Tasks 58–60 | Convergence gate after both midgame branches. |
| Precursor Network Access | 1 | progression | Tasks 61–63 | Opens late Temple/Spargus/Astro-Viewer sequence. |
| Dark Maker Targeting Data | 1 | progression | Tasks 64–70 | Broad late-game route gate; replaces a redundant one-use final key. |

The default uses these custom items rather than shuffling the native passes/amulets directly. The OpenGOAL adapter sets the minimum native pass, act, task-mask, level-open, and mission-introduction state required by an authorized mission. It MUST NOT mark the mission's network completion check merely to initialize the world.

`story_item_mode: canonical` is an experimental alternative that removes these authorizations and instead shuffles native passes and War Amulet pieces. It requires a separate physical-gate audit and should not be the first implementation.

### 6.2 Capability progression

| Item | Count | Classification | Required content | Decision |
| --- | --- | --- | --- | --- |
| Jetboard | 1 | progression | Tasks 30, 35, 42, 43, 57, 67; Jetboard side checks | Base board traversal, water travel, and rails are verified gates. |
| Jetboard Launch | 1 | progression | Task 30 and any audited boost-jump sanity | Temple Tests explicitly requires the L1+X boost jump to clear a high ledge. Kept separate from base Jetboard; Zap remains useful. |
| Invisibility Statues | 1 | progression | Tasks 28 and 30 | Permanent story ability used at Dark Statues to pass Guardian Eyes. Task 27 receives a temporary post-lesson overlay so it can exit. |
| Dark Bomb | 1 | progression | Task 28 | Intended Temple Oracle route requires Dark Bomb for the guardian-robot ring. Task 11 supplies it only after its lesson node. |
| Dark Strike | 1 | progression | Tasks 61 and 67 | Breaks specific doors/walls; lesson is temporarily overlaid in task 42. |
| Light Flight | 1 | progression | Tasks 67 and 70 | Verified late traversal; lesson is temporarily overlaid in task 61. |
| Progressive Wasteland Vehicle License | 3 | progression | Count 2: Temple/Stronghold/Rescue Seem; count 3: armed-vehicle story and side checks | Capability-based licenses avoid one key per buggy. |
| Blaster | 1 | progression_skip_balancing | RANGED alternative | Reliable medium/long range and normal ammo economy. |
| Vulcan Fury | 1 | progression_skip_balancing | RANGED alternative | Second reliable ranged alternative. One of the pair is forced local in sphere zero. |

### 6.3 Finale relics

The following seven items are native, implemented story rewards. Each is `progression_skip_balancing`; the default finale requires any five.

| Relic | Vanilla source moment | Classification | Default role |
| --- | --- | --- | --- |
| Seal of Mar | task 29 | progression_skip_balancing | Member of Finale Relics; any 5 of 7 |
| Cipher Glyph | task 51 | progression_skip_balancing | Member of Finale Relics; any 5 of 7 |
| Holo Cube | task 52 | progression_skip_balancing | Member of Finale Relics; any 5 of 7 |
| Quantum Reflector | task 54 | progression_skip_balancing | Member of Finale Relics; any 5 of 7 |
| Beam Generator | task 55 | progression_skip_balancing | Member of Finale Relics; any 5 of 7 |
| Precursor Prism | task 56 | progression_skip_balancing | Member of Finale Relics; any 5 of 7 |
| Time Map | task 61 | progression_skip_balancing | Member of Finale Relics; any 5 of 7 |

Five of seven is the recommended balance:

- Four of seven is too easy to satisfy before the late routes matter.
- Seven of seven recreates a last-relic hunt and makes optional routing irrelevant.
- Five of seven makes most branches relevant while allowing two relics to be late or remote.

The relic threshold MUST be validated against the number of enabled relics. `0` disables the relic gate; values `1` through `7` are supported.

### 6.4 Progression classification by option

Classification and predicates are option-dependent, but the implementation MUST resolve them before item creation and rule assignment:

- With `gun_logic: reliable_ranged` and shuffled guns, Blaster and Vulcan Fury are both `progression_skip_balancing` because either side of `RANGED = Blaster OR Vulcan Fury` appears in logic. With `gun_logic: none`, both are useful. With `gun_shuffle: vanilla`, no AP gun item satisfies `RANGED`; a hidden `Native Reliable Ranged Acquired` event becomes true only after the native Blaster/Vulcan grant path has actually executed (normally the task-11 throne reward is sufficient), and `early_ranged_gun` is ignored.
- With `jetboard_shuffle: true`, Jetboard is progression. With it false/vanilla, rules use a hidden post-task-29 native Jetboard event. With `jetboard_upgrade_shuffle: true`, Launch is progression; with it false, rules use a distinct post-task-29 native Launch event. Zap remains useful whenever shuffled.
- With `invisibility_statues_shuffle: true`, Invisibility Statues is progression. With it false, rules use the hidden native event created only after task 27's resolution reward. Task 27 itself still gets only its temporary return-path overlay.
- `dark_power_shuffle: vanilla` uses hidden native events after the task-11 Dark Bomb lesson and task-42 Dark Strike lesson. `key_powers` shuffles Dark Bomb and Dark Strike as progression but leaves Dark Blast native. `all` additionally shuffles Dark Blast as useful. Base Dark Jak/Dark Eco is opening state in every mode.
- `light_power_shuffle: vanilla` uses hidden native events, including Light Flight only after the task-61 oracle lesson. `key_powers` shuffles Light Flight as progression and leaves the three utility powers native. `all` additionally shuffles Light Regeneration, Flash Freeze, and Light Shield as useful. Base Light state is dependency state, not an item.
- With `vehicle_shuffle: progressive_licenses`, all three license copies are progression. With `vanilla`, `VEHICLE(1..3)` maps to hidden events created by the actual native vehicle reward paths; a route cannot assume a vehicle merely because its vanilla task is logically available. `individual_experimental` must classify every exact vehicle referenced by a rule as progression.
- Relics are progression only when the selected goal/finale threshold references them. Canonical passes/amulets become progression only in `story_item_mode: canonical`.
- Every item used in an Expert alternative is progression for that option set. In particular, if task 28 permits `Dark Bomb OR Wave Concussor`, Wave Concussor changes from useful to progression. If a verified route permits Flash Freeze, a secret vehicle, or another normally useful item as an access alternative, that item likewise becomes progression even though the route is optional.

---

## 7. Complete item-line audit

### 7.1 Morph Gun mods

| Item | Native tier | Default classification | Logic decision |
| --- | --- | --- | --- |
| Scatter Gun | Red 1 | useful | Short-range crowd control. Does not satisfy RANGED; task 11 supplies its tutorial copy. |
| Wave Concussor | Red 2 | useful | Charged area control; never required. |
| Plasmite RPG | Red 3 | useful | High-damage explosive option; never required. |
| Blaster | Yellow 1 | progression_skip_balancing | One of two RANGED alternatives; one local copy is guaranteed in sphere zero. |
| Beam Reflexor | Yellow 2 | useful | Strong ricochet upgrade, but base Blaster already satisfies logic. |
| Gyro Burster | Yellow 3 | useful | Deployable area weapon; never required. |
| Vulcan Fury | Blue 1 | progression_skip_balancing | One of two RANGED alternatives. |
| Arc Wielder | Blue 2 | useful | High-damage continuous weapon; never required. |
| Needle Lazer | Blue 3 | useful | Homing projectiles; never required. |
| Peace Maker | Dark 1 | useful | Long range but extremely limited dark ammo makes it unsafe as the sole Standard ranged gate. |
| Mass Imploder | Dark 2 | useful | Powerful crowd control; never required. |
| Super Nova | Dark 3 | useful | Screen-clearing weapon with severe ammo cost; never required. |
| Ammo Capacity Upgrade | 2 per color / 8 total | useful | Capacity and convenience only; ammunition is not modeled in reachability. |

**Why only Blaster and Vulcan Fury satisfy `RANGED`:** the intended Reach Port via Sewer route contains forced Jetboard traversal and distant fans/targets; detailed walkthroughs recommend yellow or blue fire and explicitly distinguish the short-range red option. Blaster has dependable range and ammo economy. Vulcan Fury has dependable range, although greater ammo consumption. Peace Maker is powerful and medium/long-range, but its tiny dark-ammo reserve makes it unsuitable as the only guaranteed Standard weapon.

Gun courses and gun-introduction arenas use temporary exact loadouts. This prevents a gun reward from being required to reach itself and keeps course scoring consistent.

### 7.2 Dark and Light powers

| State/item | Default classification | Decision |
| --- | --- | --- |
| Dark Jak / Dark Eco base state | precollected state | Opening state, not shuffled. Reconstructed on every load. |
| Dark Bomb | progression | Required by the intended Temple Oracle route in task 28; a temporary lesson overlay prevents task 11 self-lock. |
| Dark Blast | useful | Combat power; no access rule. |
| Invisibility Statues | progression | Required to pass Guardian Eyes in tasks 28 and 30; temporarily supplied only after task 27 awards it. |
| Dark Strike / Dark Jak Punch | progression | Required for verified doors/walls in tasks 61 and 67. |
| Dark projectile tracking / invincibility | excluded/experimental | Secret/cheat effects are not in the first pool and never appear in Standard logic. |
| Light Jak / Light Eco base state | dependency state | Not a separate AP item. Receiving any Light power ensures base Light state. |
| Light Regeneration | useful | Health recovery only. |
| Flash Freeze | useful | Useful for obstacles and challenges; Expert alternative routes only after technique audit. |
| Light Shield | useful | Survivability only. |
| Light Flight | progression | Required for tasks 67 and 70; lesson overlay prevents task 61 self-lock. |

The bridge MUST enforce dependency closure: applying Light Regeneration, Flash Freeze, Light Shield, or Light Flight also enables base Light Jak and Light Eco state. Applying a Dark power ensures base Dark Jak/Dark Eco state, although those are already opening state in the default.

### 7.3 Jetboard

| Item/state | Default classification | Decision |
| --- | --- | --- |
| Jetboard | progression | Verified traversal gate in several missions and side checks. |
| Jetboard Launch | progression | Task 30 explicitly requires the L1+X boost jump to clear a high ledge. This is conservatively separate from base-board access. |
| Jetboard Zap | useful | Combat/convenience; no Standard rule. |
| Board Training | hidden event | Tutorial state, not inventory. |
| Board Trail | temporary mission event | Added and removed by task 43; never an AP item. |

### 7.4 Vehicles

| Item/stage | Capability | Default classification | Decision |
| --- | --- | --- | --- |
| License stage 1 — Basic Wasteland Permit | Tough Puppy/free-roam baseline | progression | Needed by enabled free-roam vehicle sanity; supplies a stable first vehicle. |
| License stage 2 — Jump Endorsement | Dune Hopper | progression | Required for Temple access, Stronghold and Rescue Seem routes. |
| License stage 3 — Combat Endorsement | Sand Shark + Gila Stomper capability | progression | Required for Front Gate and armed-vehicle side content. |
| Ram 'Rod / Slam Dozer | Heavy ramming vehicle | useful | Task 68 supplies it temporarily; permanent ownership is convenience. |
| Heat Seeker | Secret buggy | useful, optional | Never logic; secret purchase or AP item after grant hook audit. |
| Dust Demon | Secret buggy | useful, optional | Never logic. |
| Desert Screamer | Secret buggy | useful, optional | Never logic; may enable unintended Temple skips, which Standard logic ignores. |

OpenGOAL's audited reward aliases map as follows: `turtle` → Tough Puppy, `snake` → Sand Shark, `toad` → Dune Hopper, `scorpion` → Gila Stomper, and `rhino` → Ram 'Rod/Slam Dozer. The default license order is capability-oriented rather than vanilla reward order; introduction missions are bootstrapped, so no story mission asks for a license before the player has a fair chance to receive it.

### 7.5 Armor, health, and survivability

| Item | Count/mode | Classification | Decision |
| --- | --- | --- | --- |
| Progressive Armor | 4 | useful | Each native armor stage increases health. No mission or check requires survivability upgrades. |
| Secret vehicle toughness upgrade | option-dependent | useful | Never logic; included only by audited secret-upgrade mode. |
| Health refill | repeatable filler | filler | Immediate resource effect; safe and idempotent after capping. |

No Standard rule may say “requires armor,” “requires X health,” or “requires regeneration.” Those are player-skill and damage-routing assumptions rather than access capabilities.

### 7.6 Native passes, amulets, crystals, and artifacts

| Family | Default treatment | Reason |
| --- | --- | --- |
| Six native area passes | Hidden state controlled by route adapter | Fine-grained physical keys create brittle story-state coupling. |
| War Amulet pieces 1–3 | Hidden story state in simplified mode | Citizenship/story presentation, not default AP progression. |
| Light Eco Crystals ×4 | Excluded by default | Native item guide describes them as doing nothing directly. |
| Dark Eco Crystals ×4 | Excluded by default | Same. |
| Seal, Cipher, Holo Cube, Quantum Reflector, Beam Generator, Prism, Time Map | Finale relic progression | Seven implemented native story rewards; AP ownership is a logical finale count in simplified mode. |
| Star Map | Excluded | Declared command without an audited native main-story reward/application path. |
| Eco Power Sphere | Story presentation/event | Not a separate default AP inventory item. |

In simplified mode, exact native story uses are supplied by shadow state rather than by AP relic ownership:

- Task 30 receives the native Seal/amulet portal presentation after its AP route and capability rule is met.
- Task 63 receives the five Astro-Viewer artifact flags/props needed by the mission script, regardless of which AP relics the player owns.
- Cipher, passes, amulets, opened-level flags, and similar script prerequisites are supplied only where the authorized mission requires them.
- None of those shadow flags increment the AP relic ledger, satisfy `RELICS(n)`, or send a location.
- Canonical mode removes these shadow substitutions and must require each exact native story item at every audited use.

An optional `eco_crystal_shuffle: relic_tokens` mode may convert the eight crystals into AP-only relic tokens. That is a custom design, not native behavior, and should be disabled for the first implementation.

### 7.7 Secret upgrades and menu unlocks

The first implementation keeps `secret_upgrade_shuffle: off`. The following table is the complete gameplay/menu secret catalogue from the audited guide. `useful candidate` means the effect may enter a later useful-only pool after a stable native grant, cap, save-reconstruction, and removal test; it never appears in Standard access logic.


| Category | Secret/menu entry | AP classification | Decision |
| --- | --- | --- | --- |
| Weapon upgrade | Increased Red Ammo Capacity | useful candidate | Included only by `secret_upgrade_shuffle: useful` after a stable grant hook; never logic. |
| Weapon upgrade | Increased Yellow Ammo Capacity | useful candidate | Same. |
| Weapon upgrade | Increased Blue Ammo Capacity | useful candidate | Same. |
| Weapon upgrade | Increased Dark Ammo Capacity | useful candidate | Same. |
| Weapon upgrade | Blaster Damage Upgrade | useful candidate | Damage only; never access logic. |
| Weapon upgrade | Scatter Gun Rate-of-Fire Upgrade | useful candidate | Rate only; never access logic. |
| Weapon upgrade | Vulcan Fury Damage Upgrade | useful candidate | Damage only; never access logic. |
| Weapon upgrade | Peace Maker Increased Radius | useful candidate | Combat power only; never access logic. |
| Weapon upgrade | Reflexor Increased Deflections | useful candidate | Combat power only; never access logic. |
| Weapon upgrade | Concussor Damage Upgrade | useful candidate | Combat power only. It does not make Wave Concussor a Standard Temple gate. |
| Weapon upgrade | Arc Wielder Robot Shock | useful candidate | Combat power only; never access logic. |
| Weapon upgrade | Mass Inverter Duration Upgrade | useful candidate | Menu name for the Mass Imploder-family duration modifier; never logic. |
| Weapon upgrade | Gyro Burster Duration Upgrade | useful candidate | Combat power only; never access logic. |
| Weapon upgrade | Plasmite RPG Ammo Efficiency | useful candidate | Economy only; never access logic. |
| Weapon upgrade | Needle Lazer Ammo Efficiency | useful candidate | Economy only; never access logic. |
| Weapon upgrade | Super Nova Ammo Efficiency | useful candidate | Economy only; never access logic. |
| Content unlock | Ratchet and Clank Gun Courses | hidden gate / purchase check | Not a random AP item by default. Free sanity mode pre-opens it when purchase sanity is off; modeled purchase opens it otherwise. |
| Vehicle upgrade | Upgrade Vehicle Toughness | useful candidate | Included only after stable grant/reconciliation audit; never logic. |
| Vehicle unlock | Unlock Heat Seeker | useful candidate | Permanent convenience vehicle; never Standard logic. |
| Vehicle unlock | Unlock Dust Demon | useful candidate | Permanent convenience vehicle; never Standard logic. |
| Vehicle unlock | Unlock Desert Screamer | useful candidate | Permanent convenience vehicle; skips it enables are ignored by Standard logic. |
| Cheat-like vehicle modifier | Unlimited Vehicle Turbos | excluded | Unbounded resource cheat; not in normal item pool. |
| Cosmetic/novelty | Toggle Jak's Goatee | excluded | No AP gameplay value. |
| Cosmetic/novelty | Big Head Mode | excluded | No AP gameplay value. |
| Cosmetic/novelty | Small Head Mode | excluded | No AP gameplay value. |
| Cosmetic/novelty | Kleiver's Diaper | excluded | No AP gameplay value. |
| Cosmetic/novelty | Bad Weather | excluded | World modifier; could be a trap/cosmetic option, never an item or logic gate. |
| Cosmetic/novelty | Mirror World | excluded | Global control/geometry presentation modifier; unsafe as an ordinary item. |
| Cosmetic/novelty | Fast Movies | excluded | Presentation only. |
| Cosmetic/novelty | Slow Movies | excluded | Presentation only. |
| Expert/debug | Level Select Act I | excluded | Bypasses mission graph and invalidates AP state. |
| Expert/debug | Level Select Act II | excluded | Bypasses mission graph and invalidates AP state. |
| Expert/debug | Level Select Act III | excluded | Bypasses mission graph and invalidates AP state. |
| Expert/debug | Hero Mode | excluded | Replays/respawns content and is incompatible with first-time location identity. |
| Cheat | Turbo Jetboard in Desert | excluded/novelty | Changes movement and could create unintended access; optional novelty mode only, never Standard logic. |
| Cheat | Dark Jak Homing Attacks | excluded/novelty | Combat modifier; optional novelty mode only. |
| Cheat | Dark Jak Invisibility | excluded/novelty | Not the same as Invisibility Statues; must never satisfy Temple statue logic. |
| Cheat | Unlimited Ammo | excluded | Unbounded resource cheat. |
| Cheat | Invulnerability | excluded | Would erase combat challenge and break meaningful item balance. |
| Cheat | Unlimited Dark Jak | excluded | Unbounded resource cheat. |
| Cheat | Unlimited Light Jak | excluded | Unbounded resource cheat. |
| Gallery | Scrap Book | excluded | Non-gameplay menu content. |
| Gallery | Mega Scrap Book | excluded | Non-gameplay menu content. |
| Gallery | Jak and Daxter Model Viewer | excluded | Non-gameplay menu content. |
| Gallery | Jak II Model Viewer | excluded | Non-gameplay menu content. |
| Gallery | Jak III Model Viewer | excluded | Non-gameplay menu content. |
| Gallery | Scene Player Act I | excluded | Can replay scenes but is not a location or progression item. |
| Gallery | Scene Player Act II | excluded | Can replay scenes but is not a location or progression item. |
| Gallery | Scene Player Act III | excluded | Can replay scenes but is not a location or progression item. |
| Gallery | Animator's Commentary | excluded | Non-gameplay menu content. |

### 7.8 Currency and consumable filler

Recommended filler families:

- Precursor Orb packs: 5, 10, and 25.
- Skull Gem packs: 1, 3, and 5.
- Red/yellow/blue/dark ammo refills.
- Health refill.
- Light Eco refill.
- Dark Eco refill.
- Vehicle repair.
- Vehicle turbo/fuel refill.

Consumables MUST be safe to receive during missions, cutscenes, vehicle use, death/restart, and load transitions. Unsafe effects are queued until a safe application state.

### 7.9 Things that are explicitly not AP items

| Source state | Treatment |
| --- | --- |
| Jak C / alternate story actor state | Initialize/restore as mission state. |
| Daxter/sidekick add or remove | Script state only. |
| Leaper, Flut-Flut/glider, Haven zoomers, train, missile, fighter, mech, walker, Dark Maker suit | Mission actors/loadouts; bootstrap. |
| Board Trail | Temporary task-43 add/remove overlay. |
| Finale Jetboard removal/restoration | Temporary script mutation; AP ledger wins after cleanup. |
| Light/Dark Eco crystals | Native inventory tokens with no direct gameplay effect; excluded by default. |
| Star Map command | Declared in the command enum but not granted by the main reward table and not found in the native dispatcher path used by audited rewards; excluded. |
---

## 8. Default route graph


The default `tiered_open_board` graph preserves source order within each mission chain and source branch convergence, while allowing two early branches and two midgame branches.

```text
Prologue / Spargus initiation (6–13)
   ├─ Spargus Field Orders → 14–24
   │      └─ Temple Expedition Orders + DONE(20) → 25–28
   │             └─ DONE(24) + DONE(28) → 29–34
   └─ Haven City Access → 35–44
                         ├─ Freedom League Orders → 45–51
                         └─ Wasteland Artifact Intel → 52–57

DONE(51) + DONE(57) + War Factory Coordinates → 58–60
Precursor Network Access + DONE(60) → 61–63
Dark Maker Targeting Data + DONE(63) → 64–70
DONE(70) + any 5 of 7 relics → 71 → 72 Victory
```

`Haven City Access` is the only major deliberate break from the native global story parent chain: the mission-board adapter initializes a safe Act II Haven snapshot without falsely completing tasks 14–34. This snapshot must be verified for level geometry, actors, passages, cutscenes, task masks, and return-to-hub state. Until that adapter passes integration tests, a fallback preset `mission_order: vanilla` should remain available.

The generator forces an **immediately actionable** route item to a local sphere-zero location and forces one of Blaster/Vulcan Fury locally in sphere zero. For the first implementation, `early_route_item: guaranteed_local` places **Spargus Field Orders**; Haven City Access may substitute only when Jetboard is already precollected or independently guaranteed in sphere zero. This avoids presenting Haven access as the player's only direction while its first mission is still blocked by Jetboard.

---

## 9. Mission-by-mission Standard logic

**Location policy:** tasks 10–35 and 37–71 are default mission-completion checks. Tasks 6–9 are prologue/setup, task 36 lacks a durable source `close-task`, and task 72 is the locked Victory event.

| ID | Display name | Source alias | Chapter | Standard access rule | Bootstrap/decision | Evidence | Check policy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | Opening | `city-start` | Prologue | Start | Opening story state, Dark Jak, Dark Eco and sidekick state are initialized; no network check. | S/B | No default check |
| 7 | Desert Interceptors | `desert-interceptors` | Prologue | DONE(6) | Fixed desert combat/vehicle sequence; no default check. | S/B | No default check |
| 8 | Vehicle Tutorial 1 | `desert-vehicle-training-1` | Prologue | DONE(6) | Vehicle tutorial loadout is temporary; no default check. | S/B | No default check |
| 9 | Vehicle Tutorial 2 | `desert-vehicle-training-2` | Prologue | DONE(6) | Vehicle tutorial loadout is temporary; no default check. | S/B | No default check |
| 10 | Complete Arena Training | `arena-training-1` | Spargus Initiation | DONE(6) | Native arena training loadout. | S/B | Network location |
| 11 | Earn 1st War Amulet | `arena-fight-1` | Spargus Initiation | DONE(10) | Temporary Scatter Gun at introduction; Dark Bomb and Dark Blast are temporarily enabled from their lesson node through mission exit. The mission never requires shuffled copies. | S/B | Network location |
| 12 | Catch Kanga-Rats | `wascity-chase` | Spargus Initiation | DONE(11) | Leaper/Kanga-Rat mission actor is supplied. | S/B | Network location |
| 13 | Unlock Satellite | `wascity-pre-game` | Spargus Initiation | DONE(12) | Fixed turret/minigame state is supplied. | S/B | Network location |
| 14 | Learn to Drive a Vehicle | `desert-turtle-training` | Spargus Field | Spargus Field Orders + DONE(13) | Temporary Tough Puppy for the training mission; permanent vehicle license is not required to learn. | S/B | Network location |
| 15 | Beat Kleiver in Desert Race | `desert-course-race` | Spargus Field | DONE(14) | Kleiver race vehicle and restrictions are supplied by the mission profile. | S/B | Network location |
| 16 | Race for Artifacts | `desert-artifact-race-1` | Spargus Field | DONE(15) | Race vehicle supplied. Armor reward is shuffled but not required. | S/B | Network location |
| 17 | Beat Monks in Leaper Race | `wascity-leaper-race` | Spargus Field | DONE(16) | Leaper supplied. | S/B | Network location |
| 18 | Destroy Metal Head Beasts | `desert-hover` | Spargus Field | DONE(17) | Sand Shark supplied for its introduction mission. | S/B | Network location |
| 19 | Earn 2nd War Amulet | `arena-fight-2` | Spargus Field | DONE(18) | Gun-training overlay supplies the intended mod; no permanent gun gate. | S/B | Network location |
| 20 | Corral Wild Leapers | `desert-catch-lizards` | Spargus Field | DONE(19) | Sand Shark/Leaper mission state supplied. Dune Hopper reward may be elsewhere. | S/B | Network location |
| 21 | Rescue Wastelanders | `desert-rescue` | Spargus Field | DONE(20) | Mission vehicle and satellite-fight loadout supplied. | S/B | Network location |
| 22 | Beat Turret Challenge | `wascity-gungame` | Spargus Field | DONE(21) | Mounted turret challenge; fixed loadout supplied. | S/B | Network location |
| 23 | Defeat Marauders in Arena | `arena-fight-3` | Spargus Field | DONE(22) | Arena training loadout supplied so the blue-gun lesson cannot self-lock. | S/B | Network location |
| 24 | Destroy Eggs in Nest | `nest-eggs` | Spargus Field | DONE(23) | Gila Stomper supplied for its introduction mission. | S/B | Network location |
| 25 | Climb Monk Temple Tower | `temple-climb` | Temple / Mines | Temple Expedition Orders + DONE(20) + VEHICLE(2) | Dune Hopper capability is retained as the normal route to Monk Temple; secret-vehicle skips are not logic. | S/W | Network location |
| 26 | Glide to Volcano | `desert-glide` | Temple / Mines | DONE(25) | Flut-Flut/glider supplied. | S/B | Network location |
| 27 | Find Satellite in Volcano | `volcano-darkeco` | Temple / Mines | DONE(26) | Flut-Flut and Daxter sections are supplied. At the reward node, Invisibility Statues is temporarily overlaid through the return teleport and mission exit; later missions require the permanent AP item. | S/W/B | Network location |
| 28 | Find Oracle in Monk Temple | `temple-oracle` | Temple / Mines | DONE(27) + Invisibility Statues + Dark Bomb | The intended route uses Dark Statues to pass Guardian Eyes and Dark Bomb to destroy the guardian-robot ring. The Invisibility + Wave Concussor alternative is Expert-only after runtime proof. Light Regeneration is overlaid only from its lesson node. | S/W/B | Network location |
| 29 | Defend Ashelin at Oasis | `desert-oasis-defense` | Temple / Mines | DONE(24) + DONE(28) | Fixed oasis defense/turret state. Jetboard reward is shuffled and is not required to reach its own check. | S/B | Network location |
| 30 | Complete Monk Temple Tests | `temple-tests` | Temple / Mines | DONE(29) + VEHICLE(2) + Invisibility Statues + Jetboard + Jetboard Launch | The normal return follows the Oracle route, uses the Seal portal, collects Jetboard symbols, and requires the documented L1+X boost jump. Seal/amulet presentation is supplied as shadow native story state in simplified mode. Flash Freeze is overlaid only from its lesson node. | S/W/B | Network location |
| 31 | Travel Through Catacomb Subrails | `comb-travel` | Temple / Mines | DONE(30) | Subrail sequence supplied. | S/B | Network location |
| 32 | Explore Eco Mine | `mine-explore` | Temple / Mines | DONE(31) | Mine rail/elevator state supplied; armor is never logic. | S/B | Network location |
| 33 | Escort Bomb Train | `mine-blow` | Temple / Mines | DONE(32) + RANGED | Bomb train supplied. Red bridge targets are out of Scatter Gun range on the intended route, so reliable ranged fire is a hard gate. | S/W/B | Network location |
| 34 | Defeat Veger's Precursor Robot | `mine-boss` | Temple / Mines | DONE(33) | Precursor robot encounter and exact boss vehicle/loadout supplied. | S/B | Network location |
| 35 | Reach Port via Sewer | `sewer-met-hum` | Haven Recon | Haven City Access + Jetboard + RANGED | Verified forced Jetboard traversal and distant fans/targets that a short-range Scatter Gun cannot reliably hit. | S/W | Network location |
| 36 | Haven Hover-Zone Tutorial | `city-vehicle-training` | Haven Recon | DONE(35) | Source task does not expose a durable close-task node; tutorial event only, never a default network location. | S/B | No default check |
| 37 | Destroy Incoming Blast Bots | `city-port-fight` | Haven Recon | DONE(35) | Blast Bot/fixed mission state supplied. | S/B | Network location |
| 38 | Destroy Barrier with Missile | `city-port-attack` | Haven Recon | DONE(37) | Missile vehicle supplied. | S/B | Network location |
| 39 | Beat Gun Course 1 | `city-gun-course-1` | Haven Recon | DONE(38) | Gun-course loadout supplied; owning course guns is not required. | S/B | Network location |
| 40 | Destroy Sniper Cannons | `city-sniper-fight` | Haven Recon | DONE(38) + RANGED | Conservative ranged-objective rule; exact mission weapon may also be overlaid if source audit proves fixed. | W/I | Network location |
| 41 | Reach Metal Head Area via Sewer | `sewer-kg-met` | Haven Recon | DONE(39) + DONE(40) + RANGED | No Jetboard requirement on the main route; ranged combat is retained for standard safety. | S/W | Network location |
| 42 | Destroy Dark Eco Tanks | `city-destroy-darkeco` | Haven Recon | DONE(41) + Jetboard + RANGED | Jetboard traversal is part of the intended route. Dark Strike is taught mid-mission and temporarily supplied after that node. | S/W/B | Network location |
| 43 | Kill Dark Plants in Forest | `forest-kill-plants` | Haven Recon | DONE(42) + Jetboard | Jetboard is required; Board Trail is an explicitly temporary add/remove mission ability. | S/W/B | Network location |
| 44 | Destroy Eco Grid with Jinx | `city-destroy-grid` | Haven Recon | DONE(43) + RANGED | Jinx and mission vehicle/state supplied; ranged combat retained conservatively. | S/W/B | Network location |
| 45 | Hijack Eco Vehicle | `city-hijack-vehicle` | Freedom League | Freedom League Orders + DONE(44) | Eco vehicle is mission-specific and supplied. | S/B | Network location |
| 46 | Defend Port from Attack | `city-port-assault` | Freedom League | Freedom League Orders + DONE(44) + RANGED | Port-defense mission state is supplied; ranged combat retained for standard completion. | S/W/B | Network location |
| 47 | Beat Gun Course 2 | `city-gun-course-2` | Freedom League | DONE(46) | Gun-course loadout supplied. | S/B | Network location |
| 48 | Break Barrier with Blast Bot | `city-blow-barricade` | Freedom League | DONE(45) + DONE(47) | Blast Bot mission actor supplied. | S/B | Network location |
| 49 | Defend HQ from Attack | `city-protect-hq` | Freedom League | DONE(48) + RANGED | Large on-foot defense encounter; conservative standard combat gate. | W/I | Network location |
| 50 | Find Switch in Sewers | `sewer-hum-kg` | Freedom League | DONE(49) + RANGED | Walkthrough evidence explicitly permits the normal route without Jetboard; ranged combat remains. | S/W | Network location |
| 51 | Find Cipher in Eco Grid | `city-power-game` | Freedom League | DONE(50) | Eco-grid minigame state supplied. | S/B | Network location |
| 52 | Race for More Artifacts | `desert-artifact-race-2` | Wasteland Artifacts | Wasteland Artifact Intel + DONE(44) | Race vehicle supplied. | S/B | Network location |
| 53 | Destroy Metal-pedes in Nest | `nest-hunt` | Wasteland Artifacts | DONE(52) | Gila Stomper supplied. | S/B | Network location |
| 54 | Chase Down Metal Head Beasts | `desert-beast-battle` | Wasteland Artifacts | DONE(53) | Beast-chase vehicle/turret state supplied. | S/B | Network location |
| 55 | Defend Spargus Front Gate | `desert-jump-mission` | Wasteland Artifacts | DONE(52) + VEHICLE(3) | Intended mission requires an armed Wasteland buggy; Tough Puppy cannot shoot. | S/W | Network location |
| 56 | Take Out Marauder Stronghold | `desert-chase-marauders` | Wasteland Artifacts | DONE(55) + VEHICLE(2) + RANGED | Dune Hopper capability is required to reach the stronghold; on-foot arena combat uses RANGED. | S/W | Network location |
| 57 | Beat Pillar Ring Challenges | `forest-ring-chase` | Wasteland Artifacts | DONE(54) + DONE(56) + Jetboard | The standard route is a five-course Jetboard challenge. Flash Freeze-only routing is Expert-only after audit. | S/W | Network location |
| 58 | Destroy War Factory Defenses | `factory-sky-battle` | War Factory | War Factory Coordinates + DONE(51) + DONE(57) | Freedom Guard fighter supplied. | S/B | Network location |
| 59 | Explore War Factory | `factory-assault` | War Factory | DONE(58) | Daxter, factory vehicle and mech states supplied. | S/B | Network location |
| 60 | Defeat Cyber-Errol | `factory-boss` | War Factory | DONE(59) | Cyber-Errol encounter loadout supplied. | S/B | Network location |
| 61 | Rescue Seem at Temple | `temple-defend` | Precursor Network | Precursor Network Access + DONE(60) + VEHICLE(2) + Dark Strike + RANGED | Dune Hopper reaches the Temple; Dark Strike opens pre-oracle doors. Light Flight is taught and overlaid only after the oracle. | S/W/B | Network location |
| 62 | Defend Spargus | `wascity-defend` | Precursor Network | DONE(61) | Fixed Spargus turret supplied; no permanent combat-vehicle license requirement. | S/W/B | Network location |
| 63 | Activate Astro-Viewer | `forest-turn-on-machine` | Precursor Network | DONE(62) + RANGED | Astro-Viewer mission has substantial combat. In simplified mode, the five native viewer-artifact flags/props are supplied as shadow story state; AP relic ownership is not an exact task-63 requirement. | S/W/B | Network location |
| 64 | Destroy Dark Ship Shield | `precursor-tour` | Dark Maker War | Dark Maker Targeting Data + DONE(63) | Dark Maker suit is mission-specific and supplied. | S/B | Network location |
| 65 | Blow Open Tower Door | `city-blow-tower` | Dark Maker War | DONE(64) | Mounted shooter/loadout supplied. | S/B | Network location |
| 66 | Destroy Metal Head Tower | `tower-destroy` | Dark Maker War | DONE(65) + RANGED | Tower climb includes substantial ranged combat; conservative standard gate. | W/I | Network location |
| 67 | Reach Catacombs via Palace Ruins | `palace-ruins-patrol` | Dark Maker War | DONE(66) + Dark Strike + Light Flight + Jetboard + RANGED | Verified cracked walls, Light Flight gaps and at least one normal-path Jetboard rail transfer. | S/W | Network location |
| 68 | Break Through Ruins | `palace-ruins-attack` | Dark Maker War | DONE(67) | Ram 'Rod/Slam Dozer supplied for its introduction mission. | S/B | Network location |
| 69 | Reach Precursor Core | `comb-wild-ride` | Dark Maker War | DONE(68) | Precursor subrail supplied. | S/B | Network location |
| 70 | Destroy Dark Ship | `precursor-destroy-ship` | Dark Maker War | DONE(69) + Light Flight + RANGED | Light Flight is explicitly needed in the ship; Jetboard is not required for the escape. | S/W | Network location |
| 71 | Destroy Final Boss | `desert-final-boss` | Finale | DONE(70) + RELICS(5) + RANGED | Sand Shark, walker and temporary final-board state supplied. Five of seven relics avoids a single last-key hunt. | S/W/B | Network location |
| 72 | City Win | `city-win` | Finale | DONE(71) | Locked Victory event; no random item is placed here. | S | Victory event |

### 9.1 Casual and Expert deltas

`logic_difficulty: casual` uses the same hard traversal gates but may additionally bootstrap RANGED for combat-heavy missions and marks high-skill challenges `EXCLUDED`. It never removes a verified traversal requirement such as Jetboard or Light Flight.

`logic_difficulty: expert` may add audited alternatives, for example Flash Freeze-assisted movement for task 57. An Expert technique is not accepted until it has:

- A written input/setup description.
- Repeatability from a clean save and after death.
- No out-of-bounds dependency unless an explicit OoB option exists.
- A runtime test showing the mission cannot corrupt or skip required close-task state.
- A corresponding logic test.

---

## 10. Mission-equipment bootstrap specification

`mission_equipment: bootstrap` is the default and is part of the logic contract, not merely a convenience cheat.

### 10.1 Bootstrap these

- Exact tutorial/introduction vehicles.
- Leaper, Flut-Flut/glider, Daxter sequences.
- Haven zoomers and mission-only vehicles.
- Subrails, train, missile, fighter, mech, walker, Dark Maker suit.
- Gun-course and mounted-gun loadouts.
- Dark Bomb/Dark Blast from their task-11 lesson node through mission exit.
- Invisibility Statues from task 27's reward node through the return teleport and mission exit.
- Dark Strike from its task-42 lesson node and Light Flight from its task-61 lesson node.
- Flash Freeze from its task-30 lesson node where the mission immediately consumes it.
- Board Trail in task 43.
- Final-boss board removal/restoration.

### 10.2 Do not bootstrap these before their permanent gate

- Jetboard or Jetboard Launch for missions that use them as cross-world progression.
- Invisibility Statues before task 27's lesson or in tasks 28/30.
- Dark Bomb before task 11's lesson or at task 28.
- Dune Hopper capability to enter Temple/Stronghold/Rescue Seem.
- Armed Wasteland capability for Front Gate or armed side challenges.
- Dark Strike after task 42's lesson mission.
- Light Flight after task 61's lesson mission.
- Blaster/Vulcan for checks whose Standard rule explicitly requires RANGED, except in Casual combat-assist mode.

### 10.3 Overlay lifecycle

1. Persist the authoritative AP ledger and current received-item index.
2. Record the mission's temporary overlay descriptor.
3. Apply only the exact scripted equipment/state.
4. On success, failure, abort, death, save load, level transition, or disconnect, remove the overlay.
5. Rebuild permanent inventory from the AP ledger.
6. If the permanent copy arrived during the mission, retain it after cleanup.
7. Never send a location merely because the overlay granted an ability.

The overlay cleanup MUST be idempotent.

### 10.4 Shadow native story-state lifecycle

Shadow state is a separate overlay class from mission equipment. It may set native pass/amulet/artifact flags that a script reads, but it MUST NOT grant AP inventory. In simplified mode:

1. Derive the exact native flags needed by the selected mission profile.
2. Record which flags were already present before the profile.
3. Set only the missing script/presentation flags.
4. Never route these writes through the AP received-item grant path.
5. Never count them toward `RELICS(n)` or reward checks.
6. On mission exit/load, restore transient flags and preserve only world-state changes that the mission legitimately completed.
7. Reconcile all actual shuffled inventory from the AP ledger afterward.

Task-30 Seal handling and task-63 Astro-Viewer artifact handling require dedicated integration tests.

---

## 11. Location checks and sanity options

### 11.1 Story mission completion sanity

| Option value | Checks | Notes |
| --- | ---: | --- |
| `off` | 0 | Story tasks still run but do not send completion locations. |
| `story` | 61 | Default: tasks 10–35 and 37–71. |
| `include_prologue` | 65 | Adds tasks 6–9 only after the mod supplies durable AP completion flags. |

Task 36 remains excluded until it has a durable completion flag. Task 72 is always an event for goals that use it.

### 11.2 Native reward sanity

The source contains 51 task nodes with reward commands. The default policy creates 38 major checks. `all_stable` adds eight crystal-only moments for 46 total. Five setup/temporary add-remove nodes are never reward checks.

| Node ID | Source node | Task | Native effects | Reward-sanity status | Reason |
| --- | --- | --- | --- | --- | --- |
| 1 | city-start-start | city-start | Jak C/story state, Dark Jak base state, Dark Eco base state, Daxter/sidekick state | Never | Opening setup, not a collectible reward. |
| 10 | arena-fight-1-introduction | arena-fight-1 | Scatter Gun | Major (default) | Stable one-time story/reward moment. |
| 11 | arena-fight-1-fight | arena-fight-1 | Dark Blast, Dark Bomb | Major (default) | Stable one-time story/reward moment. |
| 12 | arena-fight-1-throne | arena-fight-1 | Spargus Front Gate Pass, War Amulet 1, Blaster | Major (default) | Stable one-time story/reward moment. |
| 18 | wascity-pre-game-resolution | wascity-pre-game | Dark Eco Crystal | All-stable only | Crystal-only native moment; no direct gameplay effect. |
| 23 | desert-turtle-training-introduction | desert-turtle-training | Tough Puppy | Major (default) | Stable one-time story/reward moment. |
| 36 | desert-artifact-race-1-resolution | desert-artifact-race-1 | Jak C/story state, Armor 1 | Major (default) | Stable one-time story/reward moment. |
| 38 | wascity-leaper-race-resolution | wascity-leaper-race | Light Eco Crystal | All-stable only | Crystal-only native moment; no direct gameplay effect. |
| 39 | desert-hover-introduction | desert-hover | Sand Shark | Major (default) | Stable one-time story/reward moment. |
| 40 | desert-hover-resolution | desert-hover | Dark Eco Crystal | All-stable only | Crystal-only native moment; no direct gameplay effect. |
| 41 | arena-fight-2-introduction | arena-fight-2 | Red Ammo Upgrade 1, Wave Concussor | Major (default) | Stable one-time story/reward moment. |
| 44 | arena-fight-2-resolution | arena-fight-2 | War Amulet 2, Yellow Ammo Upgrade 1, Beam Reflexor | Major (default) | Stable one-time story/reward moment. |
| 48 | desert-catch-lizards-resolution | desert-catch-lizards | Dune Hopper | Major (default) | Stable one-time story/reward moment. |
| 55 | desert-rescue-resolution | desert-rescue | Dark Eco Crystal | All-stable only | Crystal-only native moment; no direct gameplay effect. |
| 58 | wascity-gungame-resolution | wascity-gungame | Light Eco Crystal | All-stable only | Crystal-only native moment; no direct gameplay effect. |
| 63 | arena-fight-3-introduction | arena-fight-3 | Vulcan Fury | Major (default) | Stable one-time story/reward moment. |
| 67 | nest-eggs-introduction | nest-eggs | Gila Stomper | Major (default) | Stable one-time story/reward moment. |
| 84 | volcano-darkeco-resolution | volcano-darkeco | Invisibility Statues | Major (default) | Stable one-time story/reward moment. |
| 93 | temple-oracle-powerup | temple-oracle | Light Regeneration, Light Jak base state, Light Eco base state | Major (default) | Stable one-time story/reward moment. |
| 98 | desert-oasis-defense-resolution | desert-oasis-defense | Jetboard Zap, Jetboard Launch, Jetboard, Seal of Mar | Major (default) | Stable one-time story/reward moment. |
| 102 | temple-tests-oracle | temple-tests | Flash Freeze | Major (default) | Stable one-time story/reward moment. |
| 109 | comb-travel-resolution | comb-travel | Light Shield | Major (default) | Stable one-time story/reward moment. |
| 113 | mine-explore-armor | mine-explore | Armor 2 | Major (default) | Stable one-time story/reward moment. |
| 119 | mine-boss-resolution | mine-boss | Blue Ammo Upgrade 1, Arc Wielder | Major (default) | Stable one-time story/reward moment. |
| 129 | city-port-attack-resolution | city-port-attack | Port–Industrial A Pass | Major (default) | Stable one-time story/reward moment. |
| 132 | city-gun-course-1-resolution | city-gun-course-1 | Yellow Ammo Upgrade 2, Gyro Burster | Major (default) | Stable one-time story/reward moment. |
| 145 | city-destroy-darkeco-dark-punch | city-destroy-darkeco | Dark Strike | Major (default) | Stable one-time story/reward moment. |
| 146 | city-destroy-darkeco-resolution | city-destroy-darkeco | Port–Metal Head Pass | Major (default) | Stable one-time story/reward moment. |
| 147 | forest-kill-plants-introduction | forest-kill-plants | Board Trail (temporary) | Never | Adds temporary Board Trail. |
| 149 | forest-kill-plants-armor | forest-kill-plants | Armor 3 | Major (default) | Stable one-time story/reward moment. |
| 150 | forest-kill-plants-resolution | forest-kill-plants | Remove Board Trail | Never | Removes temporary Board Trail. |
| 152 | city-destroy-grid-resolution | city-destroy-grid | Blue Ammo Upgrade 2, Needle Lazer, Industrial A–B Pass | Major (default) | Stable one-time story/reward moment. |
| 162 | city-gun-course-2-resolution | city-gun-course-2 | Red Ammo Upgrade 2, Plasmite RPG | Major (default) | Stable one-time story/reward moment. |
| 167 | city-blow-barricade-resolution | city-blow-barricade | Peace Maker, Industrial B–Slums A Pass | Major (default) | Stable one-time story/reward moment. |
| 175 | city-power-game-resolution | city-power-game | Cipher Glyph | Major (default) | Stable one-time story/reward moment. |
| 182 | desert-artifact-race-2-race | desert-artifact-race-2 | Holo Cube | Major (default) | Stable one-time story/reward moment. |
| 187 | nest-hunt-get-crystal | nest-hunt | Light Eco Crystal | All-stable only | Crystal-only native moment; no direct gameplay effect. |
| 191 | desert-beast-battle-resolution | desert-beast-battle | Quantum Reflector | Major (default) | Stable one-time story/reward moment. |
| 195 | desert-jump-mission-resolution | desert-jump-mission | Beam Generator | Major (default) | Stable one-time story/reward moment. |
| 200 | desert-chase-marauders-resolution | desert-chase-marauders | Precursor Prism | Major (default) | Stable one-time story/reward moment. |
| 231 | factory-boss-resolution | factory-boss | Light Eco Crystal | All-stable only | Crystal-only native moment; no direct gameplay effect. |
| 232 | temple-defend-introduction | temple-defend | Dark Ammo Upgrade 1, Mass Imploder | Major (default) | Stable one-time story/reward moment. |
| 238 | temple-defend-oracle | temple-defend | Light Flight | Major (default) | Stable one-time story/reward moment. |
| 240 | temple-defend-resolution | temple-defend | Time Map | Major (default) | Stable one-time story/reward moment. |
| 243 | wascity-defend-resolution | wascity-defend | War Amulet 3, Armor 4 | Major (default) | Stable one-time story/reward moment. |
| 252 | city-blow-tower-resolution | city-blow-tower | Dark Ammo Upgrade 2, Super Nova | Major (default) | Stable one-time story/reward moment. |
| 255 | tower-destroy-resolution | tower-destroy | Dark Eco Crystal | All-stable only | Crystal-only native moment; no direct gameplay effect. |
| 256 | palace-ruins-patrol-introduction | palace-ruins-patrol | Slums B-Gen B Pass (`add-pass-slumb-genb`) | Major (default) | Stable one-time story/reward moment. |
| 259 | palace-ruins-attack-introduction | palace-ruins-attack | Ram 'Rod / Slam Dozer | Major (default) | Stable one-time story/reward moment. |
| 267 | desert-final-boss-introduction | desert-final-boss | Remove Jetboard | Never | Temporarily removes the Jetboard for script safety. |
| 268 | desert-final-boss-walker | desert-final-boss | Jetboard | Never | Temporarily restores the Jetboard during the finale. |

When AP mode intercepts a permanent native reward, the hook sends the location and suppresses only the permanent grant. Dialogue, animation, cutscene, task closure, and unrelated state continue. Applying an AP item may call the same native reward dispatcher under an `ap-applying-item` recursion guard.

### 11.3 Mission milestone sanity

Do **not** automatically turn all 410 task nodes into locations. Many nodes are setup, resettable, mutually exclusive, or seconds apart. `mission_milestone_checks: major` uses a reviewed whitelist; it is disabled by default until runtime persistence testing is complete.

Candidate whitelist:

| Task | Source node | Display concept | Release condition |
| --- | --- | --- | --- |
| 21 | desert-rescue-satellite-fight | Reached satellite defense | Enable only after first-close AP bit, death/retry, and save/load tests |
| 24 | nest-eggs-wall | Broke the nest wall | Enable only after first-close AP bit, death/retry, and save/load tests |
| 27 | volcano-darkeco-indax-1 | Completed Daxter volcano section 1 | Enable only after first-close AP bit, death/retry, and save/load tests |
| 27 | volcano-darkeco-indax-2 | Completed Daxter volcano section 2 | Enable only after first-close AP bit, death/retry, and save/load tests |
| 28 | temple-oracle-watchers-complete | Defeated Temple watchers | Enable only after first-close AP bit, death/retry, and save/load tests |
| 28 | temple-oracle-pole-half | Cleared half of pole room | Enable only after first-close AP bit, death/retry, and save/load tests |
| 28 | temple-oracle-powerup | Reached Light Regeneration lesson | Enable only after first-close AP bit, death/retry, and save/load tests |
| 30 | temple-tests-hover-training | Completed Jetboard training room | Enable only after first-close AP bit, death/retry, and save/load tests |
| 30 | temple-tests-door-2 | Cleared second Temple test door | Enable only after first-close AP bit, death/retry, and save/load tests |
| 30 | temple-tests-door-3 | Cleared third Temple test door | Enable only after first-close AP bit, death/retry, and save/load tests |
| 32 | mine-explore-elevator | Reached mine elevator | Enable only after first-close AP bit, death/retry, and save/load tests |
| 32 | mine-explore-armor | Reached armor chamber | Enable only after first-close AP bit, death/retry, and save/load tests |
| 41 | sewer-kg-met-button0-pressed | Pressed first sewer button | Enable only after first-close AP bit, death/retry, and save/load tests |
| 41 | sewer-kg-met-button1-pressed | Pressed second sewer button | Enable only after first-close AP bit, death/retry, and save/load tests |
| 42 | city-destroy-darkeco-dark-punch | Reached Dark Strike lesson | Enable only after first-close AP bit, death/retry, and save/load tests |
| 43 | forest-kill-plants-pillars | Activated forest plant pillars | Enable only after first-close AP bit, death/retry, and save/load tests |
| 45 | city-hijack-vehicle-infiltrate | Infiltrated eco vehicle | Enable only after first-close AP bit, death/retry, and save/load tests |
| 45 | city-hijack-vehicle-escape | Escaped with eco vehicle | Enable only after first-close AP bit, death/retry, and save/load tests |
| 50 | sewer-hum-kg-switch-off | Disabled sewer switch | Enable only after first-close AP bit, death/retry, and save/load tests |
| 56 | desert-chase-marauders-get-to-stronghold | Reached Marauder stronghold | Enable only after first-close AP bit, death/retry, and save/load tests |
| 56 | desert-chase-marauders-ambush | Cleared stronghold ambush | Enable only after first-close AP bit, death/retry, and save/load tests |
| 56 | desert-chase-marauders-chase | Started leader chase | Enable only after first-close AP bit, death/retry, and save/load tests |
| 57 | forest-ring-chase-statue-3 | Completed third pillar course | Enable only after first-close AP bit, death/retry, and save/load tests |
| 57 | forest-ring-chase-statue-5 | Completed fifth pillar course | Enable only after first-close AP bit, death/retry, and save/load tests |
| 58 | factory-sky-battle-wave2 | Cleared factory defense waves | Enable only after first-close AP bit, death/retry, and save/load tests |
| 59 | factory-assault-indax-2 | Completed Daxter factory section 2 | Enable only after first-close AP bit, death/retry, and save/load tests |
| 59 | factory-assault-indax-4 | Completed Daxter factory section 4 | Enable only after first-close AP bit, death/retry, and save/load tests |
| 59 | factory-assault-get-vehicle | Reached factory vehicle | Enable only after first-close AP bit, death/retry, and save/load tests |
| 61 | temple-defend-door-2 | Opened second Temple door | Enable only after first-close AP bit, death/retry, and save/load tests |
| 61 | temple-defend-door-4 | Opened fourth Temple door | Enable only after first-close AP bit, death/retry, and save/load tests |
| 61 | temple-defend-oracle | Reached Light Flight lesson | Enable only after first-close AP bit, death/retry, and save/load tests |
| 63 | forest-turn-on-machine-spawners | Disabled Astro-Viewer spawners | Enable only after first-close AP bit, death/retry, and save/load tests |
| 67 | palace-ruins-patrol-stadium | Reached Palace stadium | Enable only after first-close AP bit, death/retry, and save/load tests |
| 70 | precursor-destroy-ship-escape | Started Dark Ship escape | Enable only after first-close AP bit, death/retry, and save/load tests |
| 71 | desert-final-boss-walker | Completed vehicle phase | Enable only after first-close AP bit, death/retry, and save/load tests |
| 71 | desert-final-boss-climb | Completed walker phase | Enable only after first-close AP bit, death/retry, and save/load tests |

`all_audited` may add further nodes, but every node requires a durable first-time AP bit. The source node itself may reset; the AP check must not.

### 11.4 Side-mission sanity

OpenGOAL enumerates source task IDs 73–137. They are finite task records with close-task resolution nodes; task 88 contains a source alias mismatch in which the task enum says `desert-bbush-get-to-19` while its node records use `wascity-bbush-get-to-19`, so the implementation must normalize the node alias to native task ID 88.

Option values:

| Value | IDs | Count | Release status |
| --- | --- | ---: | --- |
| `off` | none | 0 | Supported |
| `selected` | 114–137 | 24 | Default; finite challenge set |
| `orb_hunts` | 73–113 | 41 | Experimental until every target position is audited |
| `all` | 73–137 | 65 | Experimental; union of both |

| ID | Display name | Source alias | Region | Source unlock parent | Conservative access rule | Option set | `challenge_progression: safe` placement |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 73 | Orb Hunt / Get-To Challenge 01 | `desert-bbush-get-to-1` | Wasteland | task 20 | task 20 + Spargus Field Orders + VEHICLE(3) + Jetboard + RANGED (conservative all-capability rule) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 74 | Orb Hunt / Get-To Challenge 02 | `desert-bbush-get-to-2` | Wasteland | task 29 | task 29 + Spargus Field Orders + VEHICLE(3) + Jetboard + RANGED (conservative all-capability rule) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 75 | Orb Hunt / Get-To Challenge 03 | `desert-bbush-get-to-3` | Wasteland | task 18 | task 18 + Spargus Field Orders + VEHICLE(3) + Jetboard + RANGED (conservative all-capability rule) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 76 | Orb Hunt / Get-To Challenge 04 | `desert-bbush-get-to-4` | Wasteland | task 19 | task 19 + Spargus Field Orders + VEHICLE(3) + Jetboard + RANGED (conservative all-capability rule) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 77 | Orb Hunt / Get-To Challenge 05 | `desert-bbush-get-to-5` | Wasteland | task 20 | task 20 + Spargus Field Orders + VEHICLE(3) + Jetboard + RANGED (conservative all-capability rule) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 78 | Orb Hunt / Get-To Challenge 06 | `desert-bbush-get-to-6` | Wasteland | task 56 | task 56 + Spargus Field Orders + VEHICLE(3) + Jetboard + RANGED (conservative all-capability rule) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 79 | Orb Hunt / Get-To Challenge 07 | `desert-bbush-get-to-7` | Wasteland | task 29 | task 29 + Spargus Field Orders + VEHICLE(3) + Jetboard + RANGED (conservative all-capability rule) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 80 | Orb Hunt / Get-To Challenge 08 | `desert-bbush-get-to-8` | Wasteland | task 15 | task 15 + Spargus Field Orders + VEHICLE(3) + Jetboard + RANGED (conservative all-capability rule) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 81 | Orb Hunt / Get-To Challenge 09 | `desert-bbush-get-to-9` | Wasteland | task 18 | task 18 + Spargus Field Orders + VEHICLE(3) + Jetboard + RANGED (conservative all-capability rule) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 82 | Orb Hunt / Get-To Challenge 10 | `desert-bbush-get-to-11` | Wasteland | task 44 | task 44 + Spargus Field Orders + VEHICLE(3) + Jetboard + RANGED (conservative all-capability rule) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 83 | Orb Hunt / Get-To Challenge 11 | `desert-bbush-get-to-12` | Wasteland | task 19 | task 19 + Spargus Field Orders + VEHICLE(3) + Jetboard + RANGED (conservative all-capability rule) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 84 | Orb Hunt / Get-To Challenge 12 | `desert-bbush-get-to-14` | Wasteland | task 56 | task 56 + Spargus Field Orders + VEHICLE(3) + Jetboard + RANGED (conservative all-capability rule) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 85 | Orb Hunt / Get-To Challenge 13 | `desert-bbush-get-to-16` | Wasteland | task 52 | task 52 + Spargus Field Orders + VEHICLE(3) + Jetboard + RANGED (conservative all-capability rule) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 86 | Orb Hunt / Get-To Challenge 14 | `desert-bbush-get-to-17` | Wasteland | task 54 | task 54 + Spargus Field Orders + VEHICLE(3) + Jetboard + RANGED (conservative all-capability rule) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 87 | Orb Hunt / Get-To Challenge 15 | `wascity-bbush-get-to-18` | Spargus | task 18 | task 18 + Spargus Field Orders + VEHICLE(1) + Jetboard + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 88 | Orb Hunt / Get-To Challenge 16 | `wascity-bbush-get-to-19` | Spargus | task 52 | task 52 + Spargus Field Orders + VEHICLE(1) + Jetboard + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 89 | Orb Hunt / Get-To Challenge 17 | `wascity-bbush-get-to-20` | Spargus | task 20 | task 20 + Spargus Field Orders + VEHICLE(1) + Jetboard + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 90 | Orb Hunt / Get-To Challenge 18 | `wascity-bbush-get-to-21` | Spargus | task 18 | task 18 + Spargus Field Orders + VEHICLE(1) + Jetboard + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 91 | Orb Hunt / Get-To Challenge 19 | `wascity-bbush-get-to-22` | Spargus | task 52 | task 52 + Spargus Field Orders + VEHICLE(1) + Jetboard + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 92 | Orb Hunt / Get-To Challenge 20 | `wascity-bbush-get-to-23` | Spargus | task 13 | task 13 + Spargus Field Orders + VEHICLE(1) + Jetboard + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 93 | Orb Hunt / Get-To Challenge 21 | `wascity-bbush-get-to-24` | Spargus | task 18 | task 18 + Spargus Field Orders + VEHICLE(1) + Jetboard + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 94 | Orb Hunt / Get-To Challenge 22 | `wascity-bbush-get-to-25` | Spargus | task 29 | task 29 + Spargus Field Orders + VEHICLE(1) + Jetboard + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 95 | Orb Hunt / Get-To Challenge 23 | `city-bbush-get-to-26` | Haven | task 34 | task 34 + Haven City Access + Jetboard + Dark Strike + Light Flight + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 96 | Orb Hunt / Get-To Challenge 24 | `city-bbush-get-to-27` | Haven | task 48 | task 48 + Haven City Access + Jetboard + Dark Strike + Light Flight + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 97 | Orb Hunt / Get-To Challenge 25 | `city-bbush-get-to-28` | Haven | task 67 | task 67 + Haven City Access + Jetboard + Dark Strike + Light Flight + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 98 | Orb Hunt / Get-To Challenge 26 | `city-bbush-get-to-29` | Haven | task 67 | task 67 + Haven City Access + Jetboard + Dark Strike + Light Flight + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 99 | Orb Hunt / Get-To Challenge 27 | `city-bbush-get-to-30` | Haven | task 34 | task 34 + Haven City Access + Jetboard + Dark Strike + Light Flight + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 100 | Orb Hunt / Get-To Challenge 28 | `city-bbush-get-to-31` | Haven | task 49 | task 49 + Haven City Access + Jetboard + Dark Strike + Light Flight + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 101 | Orb Hunt / Get-To Challenge 29 | `city-bbush-get-to-32` | Haven | task 51 | task 51 + Haven City Access + Jetboard + Dark Strike + Light Flight + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 102 | Orb Hunt / Get-To Challenge 30 | `city-bbush-get-to-33` | Haven | task 64 | task 64 + Haven City Access + Jetboard + Dark Strike + Light Flight + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 103 | Orb Hunt / Get-To Challenge 31 | `city-bbush-get-to-34` | Haven | task 48 | task 48 + Haven City Access + Jetboard + Dark Strike + Light Flight + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 104 | Orb Hunt / Get-To Challenge 32 | `city-bbush-get-to-35` | Haven | task 57 | task 57 + Haven City Access + Jetboard + Dark Strike + Light Flight + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 105 | Orb Hunt / Get-To Challenge 33 | `city-bbush-get-to-36` | Haven | task 44 | task 44 + Haven City Access + Jetboard + Dark Strike + Light Flight + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 106 | Orb Hunt / Get-To Challenge 34 | `city-bbush-get-to-37` | Haven | task 45 | task 45 + Haven City Access + Jetboard + Dark Strike + Light Flight + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 107 | Orb Hunt / Get-To Challenge 35 | `city-bbush-get-to-38` | Haven | task 44 | task 44 + Haven City Access + Jetboard + Dark Strike + Light Flight + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 108 | Orb Hunt / Get-To Challenge 36 | `city-bbush-get-to-39` | Haven | task 38 | task 38 + Haven City Access + Jetboard + Dark Strike + Light Flight + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 109 | Orb Hunt / Get-To Challenge 37 | `city-bbush-get-to-40` | Haven | task 41 | task 41 + Haven City Access + Jetboard + Dark Strike + Light Flight + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 110 | Orb Hunt / Get-To Challenge 38 | `city-bbush-get-to-41` | Haven | task 35 | task 35 + Haven City Access + Jetboard + Dark Strike + Light Flight + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 111 | Orb Hunt / Get-To Challenge 39 | `city-bbush-get-to-42` | Haven | task 37 | task 37 + Haven City Access + Jetboard + Dark Strike + Light Flight + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 112 | Orb Hunt / Get-To Challenge 40 | `city-bbush-get-to-43` | Haven | task 44 | task 44 + Haven City Access + Jetboard + Dark Strike + Light Flight + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 113 | Orb Hunt / Get-To Challenge 41 | `city-bbush-get-to-44` | Haven | task 39 | task 39 + Haven City Access + Jetboard + Dark Strike + Light Flight + RANGED (conservative) | Experimental orb-hunt set | `EXCLUDED` under safe; experimental orb-hunt set |
| 114 | Desert Ring Challenge 1 | `desert-bbush-ring-1` | Wasteland | task 54 | DONE(54) + Jetboard + VEHICLE(1) | Default selected | Progression-eligible under safe |
| 115 | Desert Ring Challenge 2 | `desert-bbush-ring-2` | Wasteland | task 29 | DONE(29) + Jetboard + VEHICLE(1) | Default selected | Progression-eligible under safe |
| 116 | Spargus Ring Challenge 3 | `wascity-bbush-ring-3` | Spargus | task 22 | DONE(22); fixed race vehicle bootstrap | Default selected | Progression-eligible under safe |
| 117 | Spargus Ring Challenge 4 | `wascity-bbush-ring-4` | Spargus | task 12 | DONE(12); fixed race vehicle bootstrap | Default selected | Progression-eligible under safe |
| 118 | Haven Ring Challenge 5 | `city-bbush-ring-5` | Haven | task 48 | DONE(48); fixed Haven vehicle bootstrap | Default selected | Progression-eligible under safe |
| 119 | Haven Ring Challenge 6 | `city-bbush-ring-6` | Haven | task 45 | DONE(45); fixed Haven vehicle bootstrap | Default selected | Progression-eligible under safe |
| 120 | Egg Spider Challenge | `desert-bbush-egg-spider-1` | Wasteland | task 52 | DONE(52) + VEHICLE(1) + RANGED | Default selected | Progression-eligible under safe |
| 121 | Desert Spirit Chase | `desert-bbush-spirit-chase-1` | Wasteland | task 18 | DONE(18) + VEHICLE(1) + Jetboard | Default selected | Progression-eligible under safe |
| 122 | Spargus Spirit Chase | `wascity-bbush-spirit-chase-2` | Spargus | task 29 | DONE(29) + VEHICLE(1) + Jetboard | Default selected | Progression-eligible under safe |
| 123 | Haven Spirit Chase | `city-bbush-spirit-chase-3` | Haven | task 48 | DONE(48) + Jetboard; fixed city vehicle if required | Default selected | Progression-eligible under safe |
| 124 | Desert Timer Chase | `desert-bbush-timer-chase-1` | Wasteland | task 29 | DONE(29) + VEHICLE(1) + Jetboard | Default selected | Progression-eligible under safe |
| 125 | Spargus Timer Chase | `wascity-bbush-timer-chase-2` | Spargus | task 52 | DONE(52) + VEHICLE(1) + Jetboard | Default selected | Progression-eligible under safe |
| 126 | Single Air-Time Challenge | `desert-bbush-air-time` | Wasteland | task 18 | DONE(18) + VEHICLE(1) | Default selected | Progression-eligible under safe |
| 127 | Total Air-Time Challenge | `desert-bbush-total-air-time` | Wasteland | task 18 | DONE(18) + VEHICLE(1) | Default selected | `EXCLUDED` under safe; enabled but filler/trap placement only |
| 128 | Single Jump-Distance Challenge | `desert-bbush-jump-distance` | Wasteland | task 18 | DONE(18) + VEHICLE(1) | Default selected | Progression-eligible under safe |
| 129 | Total Jump-Distance Challenge | `desert-bbush-total-jump-distance` | Wasteland | task 18 | DONE(18) + VEHICLE(1) | Default selected | `EXCLUDED` under safe; enabled but filler/trap placement only |
| 130 | Vehicle Roll-Count Challenge | `desert-bbush-roll-count` | Wasteland | task 18 | DONE(18) + VEHICLE(1) | Default selected | `EXCLUDED` under safe; enabled but filler/trap placement only |
| 131 | Wasteland Time Trial | `desert-bbush-time-trial-1` | Wasteland | task 15 | DONE(15) + VEHICLE(1) | Default selected | `EXCLUDED` under safe; enabled but filler/trap placement only |
| 132 | Wasteland Rally | `desert-bbush-rally` | Wasteland | task 18 | DONE(18) + VEHICLE(1) | Default selected | `EXCLUDED` under safe; enabled but filler/trap placement only |
| 133 | Port Attack Challenge | `city-bbush-port-attack` | Haven | task 38 | DONE(38); fixed port-attack loadout bootstrap | Default selected | Progression-eligible under safe |
| 134 | Wastelander Rescue Challenge | `desert-rescue-bbush` | Wasteland | task 29 | DONE(29) + VEHICLE(3) | Default selected | Progression-eligible under safe |
| 135 | Gun Course Free Play | `city-gun-course-play-for-fun` | Haven | task 39 | DONE(39); gun-course loadout bootstrap | Default selected | Progression-eligible under safe |
| 136 | Jetboard Challenge | `city-jetboard-bbush` | Haven | task 38 | DONE(38) + Jetboard | Default selected | `EXCLUDED` under safe; enabled but filler/trap placement only |
| 137 | Destroy Interceptors Challenge | `desert-bbush-destroy-interceptors` | Wasteland | task 54 | DONE(54) + VEHICLE(3) | Default selected | Progression-eligible under safe |

Side-mission kiosks cost Skull Gems in vanilla. The default `sanity_costs: free` bypasses the cost while preserving the challenge. This prevents progression from being locked behind repeatable enemy farming. `vouchers` is a future alternative that consumes finite AP vouchers; `vanilla` is supported only as an explicitly grind-permitting option.

The Ratchet & Clank gun-course unlock is handled explicitly:

- With `sanity_costs: free` and purchase sanity off, the hidden course-access flag is pre-opened; no purchase location is auto-checked.
- With `secret_purchase_sanity: individual_free`, the zero-cost first-time purchase check opens the course content after the player activates it.
- With vanilla costs, the purchase and every dependent course/medal check require the modeled orb economy; otherwise generation rejects the combination.
- Shadow course access never counts as an AP item. If a future option makes it a shuffled item, it becomes progression whenever any R&C course check is enabled.

### 11.5 Medal sanity

Explicit persistent medal nodes occur for:

- Spargus pre-game course.
- Spargus gun game.
- Haven Gun Course 1.
- Haven Gun Course 2.
- Eco Grid power game.
- Two course sets in gun-course free play.

This yields seven bronze/silver/gold sets:

| Value | Count |
| --- | ---: |
| `off` | 0 |
| `gold_only` | 7 |
| `silver_and_gold` | 14 |
| `all_explicit` | 21 |

Default is `off`; medal checks are high-skill optional content. Under `challenge_progression: safe`, all gold medals and all six Ratchet & Clank course medal checks are `EXCLUDED`. `challenge_progression: all` removes only these automatic placement exclusions; it does not weaken their access rules.

### 11.6 Precursor Orb sanity

Jak 3 has 600 Precursor Orbs. The first implementation should use a monotonic **local-world earned orb total** rather than individual pickup identities.

| Mode | Behavior |
| --- | --- |
| `off` | No orb checks. |
| `global_bundles` | One check at each multiple of `precursor_orb_bundle_size`, capped at 600. Default. |
| `global_milestones` | Curated thresholds: 25, 50, 100, 150, 200, 250, 300, 400, 500, 600. |
| `regional_bundles` | Experimental; requires reliable region attribution. |
| `individual_static` | Experimental; requires stable per-pickup IDs and a source-derived finite table. |

Rules:

- AP-delivered Orb Packs increase spendable balance but **not** the local-world earned total.
- Native one-time mission/challenge orb rewards may increase the local-world total.
- The threshold flag remains set after spending.
- With the default 25-step bundles, 24 checks are created.
- `precursor_orb_progression_cap: 300` marks thresholds above 300 `EXCLUDED` so they cannot contain progression/useful items.
- Orb glitches or replay behavior cannot send duplicate locations because each threshold has a permanent AP bit.
- Retail guides/community reports indicate Jak 3's 600 orbs are not permanently missable, unlike Jak II; nevertheless, the AP mission-board adapter MUST prove that all 600 local-world orbs/rewards remain obtainable on one post-game AP save. If that acceptance test fails, the first release MUST cap generated orb locations at the proven obtainable total rather than relying on Hero Mode or an orb glitch.

### 11.7 Skull Gem sanity

Individual Skull Gem enemy drops are repeatable and MUST NOT be locations.

Supported modes:

| Mode | Behavior |
| --- | --- |
| `off` | Default. |
| `cumulative_milestones` | Finite checks at configured monotonic locally-earned totals; AP Gem Packs do not count. |
| `secret_purchases` | First-time secret purchases are checks. |
| `both` | Union. |
| `individual_static` | Experimental only for source-audited non-respawning gem entities. |

The default remains off because cumulative gems are farmable even though the threshold locations themselves are finite.

### 11.8 Secret-purchase sanity

| Mode | Behavior |
| --- | --- |
| `off` | Default. |
| `milestones_free` | Checks for first, third, sixth, and all enabled purchases; costs bypassed. |
| `individual_free` | One check per audited purchase; costs bypassed. |
| `individual_vanilla_costs` | Explicit grind/economy mode. |

Purchases are read from persistent save state. A purchase check sends once even if a secret is toggled off or the menu is revisited.

### 11.9 Never-valid checks

The world MUST NOT use:

- Repeatable enemy drops or kill counts without a finite first-time objective.
- Respawning crates, vases, or ammo boxes.
- Random Marauder spawns.
- Replay rewards.
- Arbitrary score ticks.
- Actor memory addresses or spawn order as stable identity.
- Coordinates alone as identity.
- Mutually exclusive one-shot outcomes when `accessibility: full` would require both.
- Hero Mode re-spawns as new locations.

---

## 12. Location presets and progression-placement safety

| Preset | Approximate checks | Composition |
| --- | ---: | --- |
| `story` | 99 | 61 story + 38 major rewards |
| `standard` | 147 | Story + major rewards + selected side challenges + 25-orb bundles |
| `dense_safe` | 188 | Standard plus all 41 orb-hunt tasks, after audit |
| `completionist` | 209+ | Dense plus all 21 medal nodes and optional audited milestones |

The world should support location progress types:

- Orb thresholds above the configured progression cap → `EXCLUDED`.
- Under `challenge_progression: safe`, all gold medals, all six Ratchet & Clank medal checks, source side-task IDs **127, 129, 130, 131, 132, and 136**, and all still-experimental orb-hunt IDs 73–113 are `EXCLUDED`.
- Under `challenge_progression: none`, every side-mission and medal check is `EXCLUDED`.
- Under `challenge_progression: all`, no challenge is automatically excluded, although user exclusions and orb caps still apply.
- User `priority_locations` and `exclude_locations` still apply, but cannot make an impossible rule possible.

`EXCLUDED` is a placement classification, not a disabled check. With `accessibility: full`, all 147 default checks—including the 12 orb thresholds above 300 and the six selected side tasks excluded by `challenge_progression: safe`—remain part of the reachability contract. A player may skip them during ordinary progression because they contain only filler/traps, but an all-state sweep and a real completed save must still be able to reach them.

---

## 13. Region model

Recommended logical regions:

```text
Menu
Spargus Initiation
Spargus Hub
Arena
Wasteland
Wasteland Ruins
Metal Head Nest
Monk Temple
Volcano
Oasis
Catacombs / Comb
Eco Mines
Haven Hub
Sewers
Port
Industrial Zone
Metal Head City
Forest
War Factory
Tower
Palace Ruins
Precursor Interior
Dark Ship
Finale
```

These are logical access containers. They do not need to match physical loading zones one-to-one. Physical entrance shuffle is out of scope for the first release.

---

## 14. Generation algorithm

Recommended generation order:

1. Resolve and validate option interactions in `generate_early()`.
2. Select the mission/check tables and assign location progress types.
3. Create regions and entrances.
4. Create network locations.
5. Create hidden mission-completion event locations/items.
6. Create the locked Victory event.
7. Create option-dependent progression items.
8. Create useful items.
9. Fill remaining non-event locations with weighted filler.
10. Replace the configured percentage of filler with traps.
11. Force one immediately actionable early route item and one reliable ranged gun locally when configured; do not choose Haven City Access as the sole early route unless Jetboard is also sphere-zero/precollected.
12. Apply all rules.
13. Assert item-pool count equals unfilled network-location count.
14. Run generation-time all-state reachability checks in debug/tests.
15. Export versioned runtime slot data.

Pseudocode:

```python
class Jak3World(World):
    game = "Jak 3"

    def generate_early(self):
        self.resolved = resolve_options(self.options)
        validate_options(self.resolved)

    def create_regions(self):
        build_regions(self.multiworld, self.player, self.resolved)
        build_locations(self.multiworld, self.player, self.resolved)
        build_hidden_events(self.multiworld, self.player, self.resolved)

    def create_items(self):
        pool = build_progression(self.resolved)
        pool += build_useful(self.resolved)
        pool += build_filler_to_size(self.resolved, self.unfilled_location_count - len(pool))
        self.multiworld.itempool += pool
        prefill_early_guarantees(self.resolved)

    def set_rules(self):
        apply_route_rules(self.resolved)
        apply_mission_rules(self.resolved)
        apply_sanity_rules(self.resolved)
        self.multiworld.completion_condition[self.player] = (
            lambda state: state.has("Victory", self.player)
        )
```

---

## 15. Player-option catalogue

The accompanying commented YAML is the normative default template. Supported world-specific options are summarized here.

### 15.1 Progression and mission options

| Option | Values | Default |
| --- | --- | --- |
| `goal` | `complete_city_win`, `defeat_final_boss`, `all_story_tasks`, `relic_hunt` | `complete_city_win` |
| `mission_order` | `vanilla`, `tiered_open_board`, `chapter_shuffle`, `full_shuffle_experimental` | `tiered_open_board` |
| `logic_difficulty` | `casual`, `standard`, `expert` | `standard` |
| `mission_equipment` | `bootstrap`, `require_unlocks`, `vanilla` | `bootstrap` |
| `story_item_mode` | `simplified_authorizations`, `canonical`, `vanilla` | `simplified_authorizations` |
| `finale_relic_requirement` | 0–7 | 5 |
| `early_route_item` | `guaranteed_local`, `sphere_zero`, `none` | `guaranteed_local` (Spargus-first/actionable) |
| `early_ranged_gun` | `guaranteed_local`, `sphere_zero`, `none` | `guaranteed_local` |

### 15.2 Check/sanity options

| Option | Values | Default |
| --- | --- | --- |
| `mission_completion_checks` | `off`, `story`, `include_prologue` | `story` |
| `vanilla_reward_checks` | `off`, `major`, `all_stable` | `major` |
| `mission_milestone_checks` | `off`, `major`, `all_audited` | `off` |
| `side_mission_sanity` | `off`, `selected`, `orb_hunts`, `all` | `selected` |
| `sanity_costs` | `free`, `vouchers`, `vanilla` | `free` |
| `challenge_progression` | `safe`, `all`, `none` | `safe` |
| `medal_sanity` | `off`, `gold_only`, `silver_and_gold`, `all_explicit` | `off` |
| `precursor_orb_sanity` | `off`, `global_bundles`, `global_milestones`, `regional_bundles`, `individual_static` | `global_bundles` |
| `precursor_orb_bundle_size` | 10–100 | 25 |
| `precursor_orb_progression_cap` | 0–600 | 300 |
| `skull_gem_sanity` | `off`, `cumulative_milestones`, `secret_purchases`, `both`, `individual_static` | `off` |
| `skull_gem_bundle_size` | 5–100 | 25 |
| `secret_purchase_sanity` | `off`, `milestones_free`, `individual_free`, `individual_vanilla_costs` | `off` |
| `allow_experimental_checks` | Boolean | `false` |

### 15.3 Item options

| Option | Values | Default |
| --- | --- | --- |
| `gun_shuffle` | `vanilla`, `base_and_upgrades`, `individual_mods` | `individual_mods` |
| `gun_logic` | `none`, `reliable_ranged`, `color_specific_experimental` | `reliable_ranged` |
| `ammo_upgrade_shuffle` | Boolean | `true` |
| `armor_shuffle` | `vanilla`, `useful`, `progression_experimental` | `useful` |
| `jetboard_shuffle` | Boolean | `true` |
| `jetboard_upgrade_shuffle` | Boolean | `true` |
| `invisibility_statues_shuffle` | Boolean | `true` |
| `light_power_shuffle` | `vanilla`, `key_powers`, `all` | `all` |
| `dark_power_shuffle` | `vanilla`, `key_powers`, `all` | `all` |
| `vehicle_shuffle` | `vanilla`, `progressive_licenses`, `individual_experimental` | `progressive_licenses` |
| `eco_crystal_shuffle` | `off`, `useful_tokens`, `relic_tokens` | `off` |
| `secret_upgrade_shuffle` | `off`, `useful` | `off` |

### 15.4 Network/trap options

| Option | Values | Default |
| --- | --- | --- |
| `trap_percentage` | 0–100 | 0 |
| `trap_duration` | 5–120 seconds | 20 |
| `filler_item_weights` | per-filler integer weights | supplied |
| `trap_weights` | per-trap integer weights | supplied, inactive at 0% |
| `death_link` | Boolean | `false` |

### 15.5 Required option validation

Generation MUST reject or normalize:

- Relic requirement greater than enabled relic count.
- `gun_logic: reliable_ranged` while no shuffled/precollected reliable ranged item exists.
- `jetboard_upgrade_shuffle: true` without a Jetboard Launch item/grant path, or false without the native post-task-29 Launch event in logic.
- `invisibility_statues_shuffle: true` without the task-27 temporary-exit overlay, or false without the native post-task-27 event in logic.
- `mission_equipment: require_unlocks` with missions whose exact equipment has no item/rule implementation.
- Experimental sanity modes while `allow_experimental_checks: false`.
- Canonical story mode without its separate gate table.
- `individual_static` collectible modes without stable ID tables matching the client hash.
- A progression cap outside the collectible maximum.
- `early_route_item: guaranteed_local` choosing Haven City Access without Jetboard already precollected or guaranteed sphere zero; normalize to Spargus Field Orders.
- Trap replacement greater than the number of filler slots; clamp after mandatory items, never before.
- `start_inventory_from_pool` counts exceeding pool counts.
- Mutually incompatible `local_items` and `non_local_items` declarations.

---

## 16. APWorld package layout

```text
worlds/jak3/
├── __init__.py
├── archipelago.json
├── client.py
├── game_id.py
├── items.py
├── locations.py
├── missions.py
├── milestones.py
├── options.py
├── presets.py
├── regions.py
├── rules.py
├── slot_data.py
├── source_aliases.py
├── agents/
│   ├── repl_client.py
│   ├── memory_reader.py
│   └── protocol.py
├── docs/
│   ├── setup_en.md
│   └── en_Jak 3.md
└── test/
    ├── test_generation.py
    ├── test_items.py
    ├── test_locations.py
    ├── test_logic.py
    ├── test_options.py
    ├── test_protocol.py
    └── test_source_tables.py
```

Stable IDs MUST be explicit, versioned, never derived from list order, and never reused. Disabled or retired entries remain reserved in the ID table.

Recommended data objects:

```python
@dataclass(frozen=True)
class MissionData:
    task_id: int
    source_alias: str
    display_name: str
    region: str
    route_item: str | None
    parent_events: tuple[str, ...]
    requirements: tuple[str, ...]
    bootstrap_profile: str | None
    completion_location_id: int | None
    evidence: tuple[str, ...]

@dataclass(frozen=True)
class ItemData:
    code: int
    default_classification: ItemClassification
    native_command: str | None
    family: str
    max_native_count: int
    progressive_group: str | None = None
```

---

## 17. OpenGOAL integration architecture

The existing official Jak and Daxter Archipelago world is the closest architectural precedent: its client uses the OpenGOAL REPL for server-to-game item delivery and a memory reader for game-to-server checks. Jak 3 should reuse that pattern but expose a purpose-built GOAL AP ledger/outbox rather than depending only on transient native variables.

### 17.1 Game → server

1. Native task close, audited task-node close, purchase, or threshold fires.
2. GOAL checks and sets a persistent AP location bit.
3. GOAL appends the location ID to a persistent outbox.
4. Python reads the outbox and sends `LocationChecks`.
5. Duplicate sends are acceptable; the server treats already-checked IDs idempotently.

### 17.2 Server → game

1. Python receives `ReceivedItems` with an index.
2. It verifies the expected index or requests synchronization.
3. The item/index is persisted before or atomically with application.
4. Safe items apply through a native command/custom grant mapping under an AP recursion guard.
5. Unsafe effects queue until the game is in a safe state.
6. GOAL records AP item counts independently of native inventory caps.

### 17.3 Reward interception

```text
native game-task-node reward command
  ├─ AP mode off → native behavior
  └─ AP mode on
       ├─ temporary/script command → allow through mission overlay
       ├─ shuffled permanent command → send AP reward-location check; suppress native grant
       └─ AP item application guard set → perform native grant without sending a check
```

### 17.4 Save reconstruction

Jak 3 save reconstruction can replay task reward state. During AP load:

1. Enter `ap-reconciling-save` guard.
2. Suppress shuffled native reward grants or allow them then overwrite deterministically.
3. Rebuild permanent inventory from AP counts.
4. Restore base dependencies.
5. Clear stale temporary mission/trap modifiers.
6. Exit guard.

---

## 18. Persistence and seed binding

A sidecar is safest for the first implementation. Key it by:

- OpenGOAL save slot.
- Seed/room identifier.
- Team and slot.
- AP protocol/data-table version.

Persist:

```text
protocol_version
item_table_hash
location_table_hash
mission_table_hash
seed_identifier
team
slot
last_received_item_index
received_item_counts
checked_location_bitset
pending_location_outbox
pending_item_queue
active_bootstrap_overlay
active_shadow_story_state
pending_traps
goal_completed
goal_status_sent
```

On a seed mismatch, refuse to apply items. Only a fresh/unbound AP save may be explicitly bound. Never silently reuse state from another seed.

---

## 19. Network correctness

Archipelago `ReceivedItems` packets are indexed. The client MUST persist and process them idempotently. Index zero may represent a complete inventory replay after synchronization.

```python
def handle_received_items(packet):
    if packet.index == 0:
        replace_ap_ledger_from_full_replay(packet.items)
        next_expected_index = len(packet.items)
        reconcile_game_inventory()
        return

    if packet.index != next_expected_index:
        request_sync()
        resend_all_checked_locations()
        return

    for item in packet.items:
        persist_receipt(item, next_expected_index)
        enqueue_or_apply(item)
        next_expected_index += 1
```

Test duplicate packets, packet gaps, reconnects, offline checks, OpenGOAL restart, AP client restart, and goal-status resend.

---

## 20. Traps

Traps are disabled by default. Safe candidates:

- Sandstorm Trap.
- Low Gravity Trap.
- Gun Jam Trap.
- Eco Leak Trap.
- Vehicle Wobble Trap.

A trap MUST NOT remove a permanent unlock, decrement AP item count, force an unsafe ejection, fail a mission directly, save a temporary modifier as permanent, or activate during load/death/cutscene/transition. It is queued until `safe_to_apply_trap()`.

Control inversion is not recommended by default for accessibility reasons.

---

## 21. Testing and acceptance criteria

### 21.1 Generation tests

For every supported option matrix and preset:

- Item pool equals unfilled network locations.
- All progression-referenced items have progression classification.
- All enabled locations are reachable in all-state.
- Victory is reachable.
- No progression item is locked behind itself.
- No disabled/retired ID is reused.
- Slot data and table hashes are deterministic.
- Excluded locations cannot receive progression/useful items.
- Early guarantees produce at least one local route item and one local RANGED alternative when configured.

Fuzz at least 10,000 seeds for the default and 1,000 for each supported option combination. Record:

- Sphere-zero check count; target 6–12.
- Number of independent early branches; target at least 2.
- Checks opened by each route item.
- Maximum progression drought by substantial mission completions.
- Relic sphere distribution.
- Frequency of progression at difficult challenges.
- Frequency of a single item opening only one location.

### 21.2 Runtime item tests

For every item:

- First receipt.
- Duplicate receipt.
- Receipt beyond native cap.
- Receipt during cutscene, vehicle use, death, level load, and mission restart.
- Save/reload immediately after receipt.
- Full inventory replay from index zero.
- Native reward reconstruction followed by AP reconciliation.

### 21.3 Location tests

For every location:

- Sends exactly once.
- Replaying content does not resend as a new location.
- Offline completion enters outbox.
- Reconnect sends pending checks.
- Save/load preserves completion.
- Suppressing a native permanent reward does not block task closure.

### 21.4 Bootstrap tests

For every profile:

- Start without permanent item.
- Complete, fail, retry, abort, die, and load.
- Receive permanent copy while overlay is active.
- Confirm final inventory equals AP ledger.
- Confirm no location fires from temporary grant.
- Task 11 can finish without permanent Dark Bomb and later task 28 cannot start without it.
- Task 27 can use the return statue/teleport without permanent Invisibility Statues and task 28 cannot start without it.
- Task 30 requires Launch when shuffled and receives only shadow Seal/amulet state.
- Task 63 receives all required native viewer props without increasing the AP relic count.

### 21.5 Full-accessibility acceptance

A release candidate is not accepted until:

```python
state = multiworld.get_all_state()
assert multiworld.has_beaten_game(state, player)
for location in multiworld.get_locations(player):
    assert location.can_reach(state), location.name
assert multiworld.fulfills_accessibility(state)
```

Equivalent official test helpers should be used where available.

---

## 22. Implementation sequence

### Phase 1 — protocol vertical slice

- 5–10 story completion checks.
- Jetboard, Blaster, Armor 1, Orb Pack.
- Persistent received index and check outbox.
- One goal event.
- Save/reconnect/full replay tests.

### Phase 2 — first playable default

- All 61 story completion checks.
- 38 major reward checks.
- Tiered open mission board and eight route authorizations.
- Exact 26-item progression model, 28 useful items, and 93 default filler slots.
- Mission bootstrap profiles.
- Seven relics, 5 required.
- Selected 24 side challenges.
- Global orb bundles with progression cap.
- No traps or DeathLink by default.

### Phase 3 — expanded safe content

- Audited milestone whitelist.
- Medal checks.
- Secret purchase checks.
- Secret upgrades/vehicles.
- DeathLink and safe traps.
- In-game AP status, received-item, and mission-board UI.

### Phase 4 — experimental

- Canonical pass/amulet mode.
- Individual vehicle mode.
- Orb-hunt sanity after per-target audit.
- Regional/individual static collectible sanity.
- Chapter/full mission shuffle.
- Expert movement alternatives.
- Physical entrance shuffle.

---

## 23. Known audit risks

1. **Haven early-branch snapshot:** must prove that task 35 can start safely without falsely closing Act I tasks.
2. **Task 36:** no durable source close-task; requires a custom AP flag or remains excluded.
3. **Task 88 alias mismatch:** the task enum is `desert-bbush-get-to-19`, its node aliases are `wascity-bbush-get-to-19-*`, and its source parent is confirmed as task 52. Normalize the runtime name without losing the native task ID.
4. **Jetboard Launch semantics:** the intended walkthrough explicitly requires the L1+X boost jump in task 30 and the source exposes a separate Launch command; runtime must verify that the flag controls that move. Standard remains conservatively gated until proven otherwise.
5. **Shadow story state:** verify Seal/amulet portal, Cipher use, all five Astro-Viewer props, and every route pass without leaking AP relic ownership.
6. **Exact native reward dispatcher coverage:** verify secret commands and Star Map behavior in the compiled/runtime path.
7. **Individual collectibles:** stable source IDs must be extracted before individual sanity.
8. **OpenGOAL Jak 3 project maturity:** integration should pin a compatible OpenGOAL commit/table hash.
9. **Mission bootstrap cleanup:** especially final-boss board mutations, Daxter transitions, and death during scripted vehicles.
10. **Native save reconstruction:** ensure shuffled rewards cannot leak back into permanent inventory.

---

## 24. Source map

Primary implementation sources:

1. [OpenGOAL / jak-project repository](https://github.com/open-goal/jak-project)
2. [Jak 3 task enums, task-node flags, and reward-command enum (`game-task-h.gc`)](https://github.com/open-goal/jak-project/blob/master/goal_src/jak3/engine/game/task/game-task-h.gc)
3. [Jak 3 task definitions and reward table (`game-task.gc`)](https://github.com/open-goal/jak-project/blob/master/goal_src/jak3/engine/game/task/game-task.gc)
4. [Jak 3 save implementation (`game-save.gc`)](https://github.com/open-goal/jak-project/blob/master/goal_src/jak3/engine/game/game-save.gc)
5. [Archipelago World API](https://github.com/ArchipelagoMW/Archipelago/blob/main/docs/world%20api.md)
6. [Archipelago network protocol](https://github.com/ArchipelagoMW/Archipelago/wiki/Archipelago-Network-Protocol)
7. [Archipelago accessibility sweep implementation](https://github.com/ArchipelagoMW/Archipelago/blob/main/BaseClasses.py)
8. [Official Jak and Daxter Archipelago world](https://github.com/ArchipelagoMW/Archipelago/tree/main/worlds/jakanddaxter)
9. [Jak 3 detailed walkthrough by renshai](https://gamefaqs.gamespot.com/ps2/919901-jak-3/faqs/33481)
10. [Jak 3 Weapon/Armor/Item/Power FAQ by essellAY](https://gamefaqs.gamespot.com/ps2/919901-jak-3/faqs/34258)
11. [Jak 3 Vehicle Challenge FAQ](https://gamefaqs.gamespot.com/ps2/919901-jak-3/faqs/36318)
12. [Jak 3 Precursor Orb guide](https://gamefaqs.gamespot.com/ps2/919901-jak-3/faqs/34231)
13. [Astro-Viewer artifact-name reference](https://jakanddaxter.fandom.com/wiki/Astro-Viewer)
14. [Find the Oracle in the Monk Temple walkthrough reference](https://jakanddaxter.fandom.com/wiki/Find_Oracle_in_Monk_Temple)
15. [Complete Monk Temple Tests walkthrough reference](https://jakanddaxter.fandom.com/wiki/Complete_Monk_Temple_Tests)
16. [Jak 3 walkthrough at Neoseeker](https://www.neoseeker.com/jak3/faqs/122793-jak-3-walkthrough.html)
17. [Precursor artifact reference](https://jakanddaxter.fandom.com/wiki/Precursor_artifact)
18. [Jak 3 orb missability discussion](https://www.reddit.com/r/jakanddaxter/comments/7x4iyj/are_there_any_missable_orbs_in_jak_3/)
19. [Jak II/Jak 3 missable-orb comparison discussion](https://gamefaqs.gamespot.com/boards/649670-jak-and-daxter-collection/61928558)

Secondary walkthrough/wiki/community sources were used only to corroborate intended-path mission requirements. Source code remains authoritative for IDs, flags, and reward hooks.

---

## 25. Final normative summary

The first implemented default SHOULD be:

- `accessibility: full`.
- `tiered_open_board`.
- Eight broad route authorizations.
- Jetboard, Jetboard Launch, Invisibility Statues, Dark Bomb, Dark Strike, and Light Flight.
- Three progressive vehicle-license copies.
- Blaster/Vulcan as the two RANGED alternatives, with one guaranteed local early.
- Seven native relics, five required, with exact native story props supplied only as non-counting shadow state.
- 61 story checks, 38 major reward checks, 24 selected side checks, and 24 orb bundles.
- Orb progression capped at 300 by default.
- Exactly 26 progression instances, 28 useful items, and 93 filler slots in the 147-check default; secret upgrades remain off for the first release.
- Exact mission equipment and lesson abilities bootstrapped temporarily.
- No repeatable checks, no individual enemy drops, and no volatile actor identities.
- AP ledger/outbox persistence with indexed, idempotent network handling.

This boundary gives Jak 3 a recognizable Archipelago progression curve without turning every mission reward into a key or requiring fragile speedrun techniques.
