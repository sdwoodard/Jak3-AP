# Jak 3 Archipelago — Revised Remaining Project Milestones

**Applies after:** Milestones 0–3  
**Reviewed repository state:** public `main` at commit `49748856f6e26ca4396c9603fb3e515210e95aa0`  
**Design target:** OpenGOAL Jak 3 + Archipelago, design version 0.3  
**First-release scope:** one supported default profile only

This document replaces the previous Milestones 4–22. Milestones 0–3 remain completed and should not be reopened unless a regression is discovered.

---

## 1. Recommended project goal

The design goal is sound and should remain the target:

- A default-only Jak 3 Archipelago integration for OpenGOAL.
- A tiered, branching mission board using broad route authorizations.
- Permanent AP inventory separated from native mission state.
- Temporary mission equipment supplied through reversible overlays.
- Shadow native story state separated from AP relic ownership.
- Finite, persistent, monotonic, idempotent locations.
- The documented default pool of 26 progression instances, 28 useful instances, and 93 filler instances when all 147 default network locations are enabled.
- A five-of-seven relic finale.
- `accessibility: full`.
- Unsupported and experimental options rejected before generation.
- Fresh/unprogressed native saves for first-release binding; importing a progressed vanilla save is out of scope.

The first public target should be described as a **default-only beta**, not as a feature-complete 1.0 release. The project becomes a release candidate only after one full generated default seed has been completed with ordinary save/load, a deliberate disconnect, a game restart, a client restart, and a full item replay.

### Conditional parts of the target

Three design assumptions must remain conditional until runtime evidence exists:

1. **Independent early Haven branch.**  
   Keep it as the preferred design. If the Haven snapshot cannot be proven safe, the recommended fallback is to make Haven converge after the Act I branch while still requiring `Haven City Access`. Do not falsify Act I task completion merely to preserve the original graph.

2. **All 24 orb thresholds through 600.**  
   Keep all IDs reserved. If a normal AP save cannot obtain all 600 locally earned orbs without Hero Mode, replay exploits, or a glitch, generate thresholds only through the highest proven obtainable multiple of 25 and recalculate the filler count.

3. **Jetboard Launch as an independent shuffled capability.**  
   Keep it separate only if runtime proves that its native flag can be granted, removed, reconstructed, and tested independently from the base Jetboard. If it is demonstrably not independent, revise the design explicitly, reserve the retired Launch ID, merge the capability into Jetboard, and recalculate the item/filler counts. Do not ship a logical item that the game cannot represent.

No other major design change is recommended before runtime testing. In particular, do not add extra progression merely to reduce the 93-slot filler pool; use seed statistics and playtesting first, then add only audited useful content in a later release if pacing is too sparse.

---

## 2. Cross-cutting agent execution contract

Every milestone prompt should begin with these requirements:

1. Read the repository-root `AGENTS.md`.
2. Read the canonical design and default YAML.
3. Inspect the current milestone status and risk log.
4. Implement only the requested milestone.
5. Do not edit the immutable reference trees.
6. Check Git status before and after reading Git-backed reference trees.
7. Do not claim runtime verification unless the relevant OpenGOAL build and runtime test were actually performed.
8. Add tests for every behavioral change.
9. Run targeted tests, relevant full tests, formatting, linting, and type checks.
10. Review the complete diff.
11. Report:
    - Files changed.
    - Commands run.
    - Test results.
    - Assumptions.
    - Deferred work.
    - Unresolved runtime risks.
12. Update:
    - `docs/development/milestone_status.md`.
    - `docs/JAK3_AP_RISKS.md` when a source/runtime discrepancy is found.

A milestone must not be marked complete merely because code compiles. Its completion gate must be demonstrated. A sub-grouped milestone must be delivered as separate reviewable agent tasks; one agent run must not silently continue into the next subgroup.

---

## 3. Roadmap changes from the prior document

| Previous milestone | Revised treatment |
| --- | --- |
| 4 — Persistent state | Moved to Milestone 6. It now depends on a final registry and slot-data contract. |
| 5 — Received items | Moved to Milestone 8, after a runtime-state and idempotent-command layer exists. |
| 6 — Location outbox | Moved to Milestone 9. “Acknowledgment” is replaced with reconciliation against server checked-location state. |
| 7 — Vertical slice | Moved to Milestone 10 and strengthened to include one real native reward interception. |
| 8 — Complete APWorld data | Split between Milestones 4 and 5 and moved before persistence. |
| 9 — Pure logic | Moved to Milestone 12, after high-risk runtime assumptions are tested. |
| 10 — One reward interception | Folded into Milestone 10 so the first vertical slice proves the real substitution model. |
| 11 — All reward interception | Becomes Milestone 16 and remains subdivided into small chapter tasks. |
| 12 — Generic overlays | Becomes Milestone 15 so lesson-state handling exists before all reward nodes are intercepted. |
| 13 — Bootstrap profiles | Becomes Milestone 18, after the route-board subsystem exists. |
| 14 — Route authorizations | Split into an early feasibility spike in Milestone 11 and production implementation in Milestone 17. |
| 15 — Shadow story state | Becomes Milestone 19, with early proof work in Milestone 11. |
| 16 — Story checks | Becomes Milestone 20. |
| 17 — Side challenges | Becomes Milestone 21. |
| 18 — Orb thresholds | Split into an obtainability audit in Milestone 11 and production implementation in Milestone 22. |
| 19 — Goal/finale | Becomes Milestone 23. |
| 20 — Full integration | Becomes Milestone 24 with tiered CI/fuzzing requirements. |
| 21 — Diagnostics | Basic observability becomes mandatory throughout; final player-facing polish is Milestone 25. |
| 22 — Release packaging | Becomes Milestone 26 and focuses on hardening the package pipeline that already exists. |
| Missing from prior roadmap | Milestone 13 implements every permanent default item; Milestone 14 implements exactly-once filler and consumable delivery. |

---
# Milestone 4 — Consolidate Normative Sources and Freeze the Versioned Data Contract

## Human-readable summary

Before the mod saves Archipelago progress, every item, location, mission, and protocol field needs a stable identity.

The current repository has a dependable handshake and explicit legacy IDs, but its active APWorld still describes the retired 131-location scaffold. The persistence milestone cannot safely store table hashes until the first-release registry and slot-data format are defined.

This milestone creates one clear source of truth and a versioned contract shared by the generator, client, game integration, tests, and future save sidecars. It does not add gameplay behavior.

## Technical objective

Create the canonical first-release registry and compatibility contract without yet making the complete 147-location generator active.

## Required work

### Canonical documentation

- Commit or update a repository-root `AGENTS.md`.
- Select one canonical in-repository design path and one canonical YAML path.
- Recommended canonical paths:
  - `docs/design/progression-and-logic.md`
  - `config/templates/Jak3.yaml`
- Update `AGENTS.md` so it names the actual repository paths.
- Store this roadmap under `docs/development/`.
- Remove, redirect, or clearly label duplicate specification copies.
- Add a semantic parity test for the supported defaults instead of depending on an optional sibling-workspace file.
- Correct option comments so `mission_equipment` describes temporary equipment/lesson overlays only, while `story_item_mode: simplified_authorizations` owns shadow native story props.
- State plainly that `allow_experimental_checks: true` remains rejected in the default-only beta even if experimental names stay documented.

### Stable registry

Define explicit, immutable records for:

- Every unique default progression item definition and its pool multiplicity, totaling 26 progression instances.
- Every unique default useful item definition and its pool multiplicity, totaling 28 useful instances.
- All filler and future trap item names.
- The 61 default story-completion locations.
- The 38 major reward locations.
- The 24 selected side-challenge locations.
- The 24 orb-threshold locations.
- Hidden mission-completion events.
- The locked Victory event.
- Mission bootstrap profile identifiers.
- Shadow-story profile identifiers.

Rules:

- IDs must be literal and must not derive from list order.
- An existing legacy ID may be retained only for the exact same network concept.
- Every removed or changed legacy concept remains reserved and documented.
- Task 36's legacy location ID is retired/reserved.
- Task 72 is not a normal network location.
- Task 88 retains native task ID 88 and its normalized runtime alias.
- Event items and event locations use `None`, not network IDs.

### Version and hash contract

Define:

```text
protocol_version
game_integration_version
slot_data_version
state_schema_version
item_table_version
location_table_version
mission_table_version
item_table_hash
location_table_hash
mission_table_hash
resolved_options_hash
design_version
```

Hashing must use canonical serialization with deterministic ordering and documented encoding.

### Slot-data schema

Replace the legacy slot-data shape with a versioned first-release schema containing only runtime-required information, such as:

- Required protocol/integration versions.
- Table versions and hashes.
- Resolved option values needed by the client.
- Enabled feature flags.
- Goal and relic threshold.
- Enabled location families.
- Orb threshold configuration.
- Challenge placement policy.
- Trap duration, even though traps remain disabled.
- Any runtime mission-profile version required by the GOAL bridge.

Do not place redundant item/location name mappings in slot data when the Archipelago data package already supplies them.

### Continuous integration

Add a normal push/pull-request CI workflow that performs the repository's available:

- Unit tests.
- Package import tests.
- Stable-ID and hash tests.
- Default-YAML tests.
- Formatting/lint/type checks.
- APWorld package build.

OpenGOAL runtime smoke tests may remain a separate manually triggered job if the toolchain cannot reasonably run in standard CI.

## Required tests

- Canonical default YAML values match the design.
- YAML comments preserve the architectural separation between mission overlays and shadow story state.
- Duplicate names and IDs fail.
- Registry serialization is deterministic.
- Hashes are stable across repeated runs.
- Reordering source declarations does not alter IDs.
- Retired IDs cannot be reused.
- Task 36 is retired.
- Task 72 is an event.
- Task 88 preserves native ID 88.
- Slot-data serialization is deterministic and JSON-safe.
- The repository works from a standalone checkout without optional sibling specification files.
- CI runs on a pull request or equivalent local workflow validation.

## Non-goals

- Do not apply received items.
- Do not send locations.
- Do not implement persistence.
- Do not implement mission logic.
- Do not change native game state.

## Completion gate

The APWorld, client, and GOAL integration can all import or consume the same version constants, registry hashes, and slot-data schema. The new registry is authoritative for compatibility and persistence. The legacy generator may remain temporarily isolated only until Milestone 5; no persistence or runtime protocol code may treat it as authoritative.

## Suggested Codex prompt

```text
/plan

Read AGENTS.md and the canonical design/default YAML first.

Then read the Project-Milestones-Revised.md file for a list of project milestones.

Implement only Milestone 4: consolidate the normative source paths and create
the versioned first-release item/location/mission registry and slot-data
contract. Preserve or reserve every existing legacy ID. Do not add runtime item
delivery, location submission, persistence, mission hooks, or logic.

Add deterministic hash and compatibility tests, plus ordinary CI for the
available Python/APWorld checks.

Before completion, run all relevant tests and checks, review the full diff, and
update milestone_status.md and JAK3_AP_RISKS.md.
```

---

# Milestone 5 — Activate the Exact Default Static APWorld Pool

## Human-readable summary

The repository's current generator still creates the old 131-location mission-unlock world. That scaffold was useful for verifying package structure, but it is not the intended Jak 3 Archipelago game.

This milestone switches the active generator to the documented default static pool: the right item names, classifications, counts, location families, exclusions, and Victory event. Logic may remain deliberately permissive until Milestone 12, but generated seeds must no longer describe the retired mission-unlock design.

## Technical objective

Make the active APWorld generate the exact default data defined by the Milestone 4 registry.

## Required work

- Remove legacy per-mission unlock items from the active item pool.
- Create the eight route authorizations.
- Create all capability, weapon, relic, useful, and filler entries.
- Create the 147 network locations:
  - 61 story completions.
  - 38 major reward moments.
  - 24 selected side challenges.
  - 24 orb thresholds.
- Create hidden mission-completion events.
- Create one locked Victory event with no network address.
- Assign documented default classifications.
- Mark orb thresholds above 300 `EXCLUDED`.
- Mark selected side tasks 127, 129, 130, 131, 132, and 136 `EXCLUDED`.
- Build filler by the supported weighted configuration.
- Keep traps at zero under the supported default.
- Export the Milestone 4 slot-data contract.
- Clearly label any temporary permissive region/rule behavior as non-playable scaffolding.

## Exact default assertions

```text
network locations = 147
progression instances = 26
useful instances = 28
filler instances = 93
trap instances = 0
Victory events = 1
```

## Required tests

- Exact counts and classifications.
- Explicit stable IDs.
- Deterministic generation for fixed seeds.
- Item-pool count equals unfilled network-location count.
- No legacy mission-unlock item is generated.
- Task 36 has no active location.
- Task 72 is Victory and consumes no item-pool slot.
- Orb thresholds are 25 through 600 in steps of 25.
- Excluded locations cannot receive progression or useful items.
- Default filler weighting is deterministic for a fixed seed.
- Package import, registration, and `.apworld` build still succeed.
- Legacy IDs remain reserved.

## Non-goals

- Do not implement final mission reachability rules.
- Do not implement game hooks.
- Do not implement route authorization behavior.
- Do not claim the generated world is playable yet.

## Completion gate

A generated default Jak 3 slot contains exactly the documented first-release static pool and no longer exposes the retired 131-location generator as active behavior.

## Suggested Codex prompt

```text
/plan

Implement only Milestone 5 using the versioned registry from Milestone 4.

Replace the active legacy 131-location mission-unlock generator with the exact
documented default static pool: 147 network locations, 26 progression
instances, 28 useful instances, 93 filler instances, and one non-networked
Victory event.

Final Standard logic and runtime hooks are explicitly out of scope. Preserve
all stable-ID reservations and add exact count/classification tests.
```

---

# Milestone 6 — Add Atomic Persistent AP State and Seed/Save Binding

## Human-readable summary

Archipelago progress cannot live in the current temporary handshake file. It must survive game restarts, client restarts, save/load, and loss of the server connection.

This milestone chooses one authoritative storage boundary, binds a fresh Jak 3 AP save to one room/team/slot, and stores enough information to reject incompatible or wrong-seed state safely.

It still does not deliver real items or send real locations.

## Technical objective

Implement a versioned, atomic, recoverable persistent-state layer keyed by native save identity and Archipelago slot identity.

## Required architecture decision

Create an ADR that explicitly defines:

- Where the sidecar or embedded state lives.
- Which process is the single authoritative writer.
- How game-side checks persist when the AP server is offline.
- How Python and GOAL exchange state without concurrent writes.
- How writes are made atomic.
- How backups and corrupt-state quarantine work.
- How native save-slot copy, backup/restore, deletion, and switching are handled.
- How two divergent copies of one bound save are detected or explicitly declared unsupported.
- Whether first release requires a fresh native save.

**Recommended first-release policy:** require a fresh/unprogressed native save for initial AP binding. Importing a progressed vanilla save is out of scope.

A client-session temporary file is not sufficient as the persistent storage boundary.

## Persisted schema

At minimum:

```text
state_schema_version
protocol_version
game_integration_version
slot_data_version
item_table_hash
location_table_hash
mission_table_hash
resolved_options_hash
design_version

seed_identifier
team
slot
slot_name
native_save_slot
native_save_identity

next_received_item_index
received_item_journal
received_item_counts
pending_item_application_indices
game_application_journal_version
last_observed_game_command_receipt

checked_location_bits
server_confirmed_location_bits
pending_location_outbox

local_earned_precursor_orbs
local_earned_skull_gems

active_bootstrap_overlay
active_shadow_story_state
pending_traps

goal_completed
goal_status_sent
last_clean_shutdown
```

`received_item_journal` must retain enough per-index identity and application state to distinguish “received,” “pending,” and “applied” across an index-zero replay. Counts alone are insufficient for crash-safe consumables.

Fields for not-yet-implemented systems may be empty but should be schema-defined to avoid ad hoc persistence later.

## Required behavior

- A valid unbound AP save can bind once.
- Binding occurs only after both a native save identity and authenticated AP `seed_identifier`/team/slot/slot data are known. The seed identifier should be exported in slot data rather than inferred solely from a user-editable room name.
- A bound save rejects another seed, team, or slot.
- A table/hash mismatch stops item/check processing.
- Missing state creates a new unbound state only when the native save is eligible.
- Corrupt state is never silently overwritten.
- Writes use a temp file plus durable replacement or an equivalent atomic mechanism.
- At least one prior valid backup is retained.
- A save-slot switch changes the selected sidecar.
- The documented save-copy/restore policy is enforced; a backup restore is supported, while two divergent live copies cannot silently write the same binding.
- State inspection is read-only until compatibility checks pass.

## Required tests

- New state creation.
- Bind and reload.
- Game restart.
- Client restart.
- Wrong seed.
- Wrong team or slot.
- Wrong native save slot.
- Save-slot switching.
- Missing file.
- Empty file.
- Truncated/corrupt file.
- Invalid checksum.
- Old schema.
- Newer unsupported schema.
- Table-hash mismatch.
- Interrupted write.
- Backup recovery.
- Duplicate load.
- Read-only failure behavior.
- No writes to immutable reference trees.

## Non-goals

- Do not apply game items.
- Do not submit locations.
- Do not intercept rewards.
- Do not add mission checks.

## Completion gate

A test state can be bound, atomically persisted, reloaded, backed up, and safely rejected for the wrong seed/save/table contract without modifying game inventory or server state.

## Suggested Codex prompt

```text
/plan

Implement only Milestone 6.

First write an ADR selecting the authoritative persistence owner and atomic
sidecar boundary. The design must support game-side progress while the AP server
is offline and must avoid concurrent writers.

Implement the versioned state schema, fresh-save binding, seed/team/slot/save
validation, atomic writes, backup recovery, and corrupt-state quarantine. Do
not deliver items, submit locations, or hook missions yet.
```

---

# Milestone 7 — Add a Runtime State Model and Idempotent Command Transport

## Human-readable summary

A ping proves that the client and game can see each other, but permanent item delivery needs more information. The client must know whether a save is loaded, whether the game is transitioning, and whether a command was already applied.

This milestone expands the handshake into a small, versioned control protocol with safe-state observation and deduplicated commands. It is the foundation for reliable item application, overlay cleanup, and mission changes.

## Technical objective

Upgrade the protocol bridge from heartbeat-only communication to a structured state snapshot and idempotent command/result channel.

## Required game snapshot fields

At minimum:

```text
protocol_version
game_integration_version
session_nonce
game_heartbeat
client_heartbeat

game_running
source_loaded
save_loaded
native_save_slot
native_save_identity
ap_state_loaded
ap_state_bound

current_level
current_act
current_task
current_task_node

at_title_menu
loading
in_cutscene
dying_or_dead
mission_restarting
level_transition
in_vehicle
safe_to_apply_permanent_item
safe_to_apply_consumable
safe_to_mutate_mission_state

last_command_id
last_command_kind
last_command_result
last_error_code
last_error_message
```

Use stable enums/codes for machine decisions and separate human-readable text for diagnostics.

## Required command behavior

- Each mutating command has:
  - Session nonce.
  - Monotonic or unique command ID.
  - Command kind.
  - Payload.
  - Expected state/schema versions.
- Repeating the same command ID in the same game session returns the prior result without applying the effect again.
- Permanent-unlock commands are expressed as idempotent target-state/reconciliation operations, not blind increments.
- Additive consumable commands remain forbidden until Milestone 14 supplies a durable game-application receipt boundary that survives the crash-after-effect window.
- Commands from an old game session are rejected.
- A command result distinguishes:
  - Applied.
  - Already applied.
  - Queued.
  - Unsafe now.
  - Incompatible.
  - Invalid payload.
  - Failed.
- The client can reconnect and discover recent completed command IDs/results for the current game session.
- A game restart forces reconciliation from the AP ledger; it must not depend on replaying a non-idempotent old-session command.
- Harmless read/query commands remain available at the title menu.
- Mutating commands are rejected until save binding and compatibility checks pass.

## Required tests

- Client before game.
- Game before client.
- Client restart.
- Game restart.
- Stale session command.
- Duplicate command.
- Out-of-order command.
- Invalid payload.
- Protocol mismatch.
- Table mismatch.
- Title menu.
- Save loading.
- Cutscene.
- Death/restart.
- Level transition.
- Communication loss does not crash either process.
- Snapshot parsing is forward-safe for unknown optional fields.

## Non-goals

- No real AP item application.
- No real location submission.
- No reward interception.
- No mission-board mutation.

## Completion gate

The client can reliably determine when a compatible bound save is loaded and can send a harmless target-state command whose duplicate cannot apply twice. The protocol explicitly rejects non-idempotent additive effects until their durable application journal exists.

## Suggested Codex prompt

```text
/plan

Implement only Milestone 7.

Upgrade the protocol-2 heartbeat bridge into the next versioned runtime snapshot
and idempotent command/result transport. Add save identity, task/level state,
unsafe-state flags, session nonces, command IDs, duplicate detection, and clear
result/error codes.

Use only harmless test commands. Do not deliver AP items or submit locations.
```

---

# Milestone 8 — Implement Indexed ReceivedItems and the AP Item Ledger

## Human-readable summary

When the Archipelago server sends an item, the mod must record it in order, survive a crash between receipt and application, and rebuild the native game state after a restart.

This milestone enables the incoming half of Archipelago for a deliberately small item slice. The persistent AP ledger, not native reward history, becomes authoritative for those items.

## Technical objective

Implement indexed `ReceivedItems` processing, a crash-safe ledger, and safe native reconciliation for a small test set.

## Initial item slice

Use permanent or ledger-only effects only:

- Jetboard.
- Blaster.
- Progressive Armor stage 1.
- An internal ledger-only test item only if needed.

Do not use an Orb Pack or another additive consumable in this milestone; those require the durable exactly-once application boundary in Milestone 14.

## Required behavior

- Set the client `items_handling` flags to receive remote, local, and starting inventory items.
- Validate item IDs against the connected slot's game/data contract.
- Process items in server index order.
- Persist the receipt before, or atomically with, native application.
- Store pending application by item index and item ID.
- Ignore a duplicate packet safely.
- On an index gap:
  - Send `Sync`.
  - Resend locally checked locations as required by the protocol.
  - Do not silently advance the persistent expected index.
- On index zero:
  - Treat the packet as the canonical complete received-item sequence.
  - Rebuild the AP ledger deterministically.
  - Preserve an “applied” marker only when the replayed index and item identity match the persisted journal.
  - Quarantine or report an impossible index/item-history mismatch rather than reapplying blindly.
  - Reconcile permanent native state to the rebuilt ledger.
- Queue unsafe application until the Milestone 7 snapshot says it is safe.
- Distinguish received count from native cap.
- Native inventory is reconstructed from the AP ledger after load.

## Crash-consistency tests

- Crash/restart after receipt persisted but before native application.
- Crash/restart after native application but before command result observation.
- Duplicate native application command.
- Full replay after a partially applied queue.
- Full replay that removes an incorrect local cache entry.
- Repeated permanent receipt beyond a native cap.
- Item received during cutscene, death, vehicle use, load, and transition.

## Other required tests

- First receipt.
- Duplicate packet.
- Packet gap.
- Index zero.
- Duplicate index-zero replay.
- Client disconnect.
- Server reconnect.
- Client restart.
- Game restart.
- Wrong table hash.
- Unknown item ID.
- Starting inventory.
- Same item from another player.
- Server/cheat-console item attribution does not affect identity.

## Non-goals

- No full first-release item table application.
- No mission reward interception.
- No temporary mission grants.
- No traps.

## Completion gate

The permanent-item slice can be received, journaled, queued, applied, replayed from index zero, and reconstructed after restart without loss or duplicate effects. No additive consumable is enabled prematurely.

## Suggested Codex prompt

```text
/plan

Implement only Milestone 8.

Enable ReceivedItems for the small approved item slice. Use the persistent state
and idempotent command transport. Follow Archipelago index semantics, including
Sync on gaps and full replacement/reconciliation at index zero.

Persist before application, test both crash windows, and keep AP-delivered
currency separate from locally earned collectible totals.
```

---

# Milestone 9 — Implement a Persistent Location Outbox and Server Reconciliation

## Human-readable summary

A location check must remain complete forever, even when the server is offline or the same activity is replayed.

Archipelago location packets are safe to resend; there is not a simple one-packet acknowledgment to trust. This milestone therefore keeps the local durable bit as authoritative and reconciles it with the server's checked-location state after connection and room updates.

## Technical objective

Implement durable game-to-server location reporting for one debug check and one controlled native check.

## Initial location slice

- One debug-only check.
- One early mission completion with a verified durable close-task moment.

## Required behavior

1. The game event fires.
2. The game validates the location ID against the active table.
3. The durable local AP bit is set before the event is exposed as complete.
4. The location ID is added to the persistent outbox.
5. The client sends `LocationChecks` when authenticated.
6. Duplicate sends remain harmless.
7. On `Connected`:
   - Send locally checked IDs that the server still reports as missing.
   - Merge server-confirmed AP check bits as appropriate, without changing native task completion or granting native rewards.
8. On `RoomUpdate.checked_locations`:
   - Mark matching pending IDs as server-confirmed.
   - Compact the pending outbox without clearing the permanent local bit.
9. Unknown or disabled IDs produce a compatibility error.
10. Mission replay cannot create a second AP check.

Do not rely on volatile actor addresses or transient task-node state as the AP identity.

## Required tests

- First completion.
- Repeat completion.
- Completion while AP server is offline.
- Completion while Python client is closed, if the chosen persistence architecture supports playing in that state.
- Game restart before upload.
- Client restart before upload.
- Duplicate upload.
- Reconnect.
- `Connected.checked_locations` reconciliation.
- `RoomUpdate.checked_locations` reconciliation.
- Same-slot/co-op-style server check update.
- Save/load.
- Mission replay.
- Unknown ID.
- Table mismatch.
- Outbox compaction never clears the durable bit.

## Non-goals

- Do not add all story checks.
- Do not suppress native rewards.
- Do not add side challenges or orb thresholds.

## Completion gate

A controlled native event creates one permanent AP location, survives all restart/offline cases, and can be resent until the server confirms it without ever becoming a second distinct check.

## Suggested Codex prompt

```text
/plan

Implement only Milestone 9.

Add one debug check and one controlled native completion check. Persist the
local bit and outbox before sending. Reconcile against Connected and RoomUpdate
checked_locations; do not invent a per-packet acknowledgment and never clear
the durable local completion bit.

Test offline completion, replay, both process restarts, duplicate sends, and
server-state reconciliation.
```

---

# Milestone 10 — Complete the First Real End-to-End Vertical Slice

## Human-readable summary

The previous milestones prove incoming and outgoing reliability separately. This milestone proves a genuine Jak 3 Archipelago loop:

- Complete real Jak 3 content.
- Send a mission or reward location.
- Receive a shuffled item.
- Apply it in the running game.
- Preserve everything through save, restart, reconnect, and replay.

It also moves one native reward-interception proof earlier so the project does not spend months expanding data before validating its most important substitution mechanism.

## Technical objective

Create a small connected gameplay slice with one real permanent native reward interception.

## Suggested scope

- Five to ten early story completion checks.
- Jetboard, Blaster, and Armor stage 1 support.
- One early mission chain.
- One internal temporary goal.
- One real reward interception.

**Preferred reward proof:** the Armor 1 reward at task 16, unless source/runtime inspection identifies a safer single permanent grant.

## Reward-interception requirements

### AP mode disabled

- Native reward behavior is unchanged.

### AP mode enabled

- The reward moment sends its AP location exactly once.
- Only the shuffled permanent grant is suppressed.
- Dialogue, animation, cutscene, task closure, and unrelated state continue.
- Replaying the reward cannot send a new check.

### Applying the AP item

- The native grant path may be reused.
- An `ap-applying-item` recursion guard prevents the grant from sending the reward location.
- A duplicate command cannot grant twice.

## End-to-end required tests

- Connected check followed by item receipt.
- Offline completion followed by reconnect.
- Full inventory replay.
- Duplicate check resend.
- Game restart.
- Client restart.
- Save immediately before and after reward.
- Death before reward.
- Death after reward.
- Mission replay.
- Seed mismatch.
- Table mismatch.
- Temporary goal status resend.
- Start at title menu, load the save, then connect.
- Connect first, then load the save.
- AP mode off.

## Non-goals

- No tiered mission board.
- No complete 147-location runtime.
- No lesson overlays.
- No shadow story state.
- No Haven snapshot.

## Completion gate

A tester can complete the small real Jak 3 slice on a generated server and recover correctly from a deliberate client restart, game restart, disconnect, item replay, and mission replay.

## Suggested Codex prompt

```text
/plan

Implement only Milestone 10.

Build a real end-to-end vertical slice using the existing persistent ledger and
outbox. Include five to ten early checks, the approved small item slice, a
temporary test goal, and exactly one permanent native reward interception.

Prefer the task-16 Armor 1 reward unless runtime/source review finds a safer
single grant. Preserve all non-shuffled native behavior and test AP mode off.
```

---

# Milestone 11 — Resolve High-Risk Runtime Feasibility Assumptions

## Human-readable summary

Several parts of the intended design are more than ordinary item randomization: they alter story order, temporarily synthesize native story props, and rely on the full post-game collectible set remaining available.

These assumptions should be tested before the project expands every reward and mission hook. This milestone is a focused engineering spike that either validates the design or activates a documented safe fallback.

## Technical objective

Produce runtime evidence and explicit go/no-go decisions for the highest-risk first-release assumptions.

## Required spikes

### 1. Haven early-branch snapshot

Prove that `Haven City Access` can initialize task 35 without completing tasks 14–34.

Verify:

- Correct act and level state.
- Geometry and passages.
- Required actors.
- Mission masks.
- Task 35 start.
- Hub return.
- Save/load.
- No false AP or native task completions.
- No shuffled reward leakage.

### 2. Jetboard Launch semantics

Verify that the separate native Launch flag actually controls the documented charged launch used by task 30.

### 3. Task 30 shadow story requirements

Identify and test the exact Seal/amulet/portal state needed by the mission without incrementing AP relic ownership.

### 4. Task 63 Astro-Viewer requirements

Identify and test the exact five native artifact flags/props required by the script without incrementing AP relic ownership.

### 5. Native save reconstruction

Prove which reward commands or inventory fields are reconstructed on save load and how the AP guard/reconciliation must override them.

### 6. Orb completeness

Prove the maximum number of locally earnable Precursor Orbs on one normal post-game AP save, without Hero Mode or glitches.

### 7. Side-challenge cost and course access

Verify the safe zero-cost entry path and hidden Ratchet & Clank course-access behavior used by the default.

## Required deliverable

Create `docs/development/feasibility_decisions.md` with, for each spike:

- Source evidence.
- Runtime procedure.
- Runtime result.
- Screens/logs or reproducible assertions.
- PASS, SAFE FALLBACK, or BLOCKED.
- Any required specification correction.
- Any new risk.
- Exact production milestone affected.

## Predefined fallbacks

- **Haven snapshot fails:** recommended fallback is `Haven City Access + DONE(34)` rather than falsifying Act I completion. If even that is unstable, ship vanilla mission order as the supported beta profile.
- **600 orbs fail:** reserve all IDs but generate thresholds only through the highest proven multiple of 25; recalculate network/filler counts.
- **Launch is demonstrably inseparable from base Jetboard:** make an explicit design/registry revision, reserve the retired Launch ID, merge the capability into Jetboard, and recalculate pool counts before Milestone 12.
- **Launch remains uncertain:** mark the assumption BLOCKED. Do not ship either a ghost Launch item or an unverified gate.
- **Shadow story state cannot be isolated:** block the affected simplified-mode mission path; do not let native shadow props count as AP relics.
- **Save reconstruction leaks:** release is blocked until reconciliation is deterministic.

## Non-goals

- Do not broadly implement all route authorizations.
- Do not broadly implement all shadow profiles.
- Do not broaden the supported option set.
- Do not silently redesign the normative specification.

## Completion gate

Every listed assumption has a reproducible PASS or a documented safe fallback. No unresolved high-risk assumption is allowed to remain implicit.

## Suggested Codex prompt

```text
/plan

Implement only Milestone 11 as a set of focused source/runtime feasibility
spikes. Do not expand production features.

Test the Haven task-35 snapshot, Jetboard Launch flag, task-30 native portal
state, task-63 viewer props, native save reconstruction, 600-orb availability,
and default side-challenge cost/course access.

Write feasibility_decisions.md with evidence and apply only the predefined safe
fallbacks. Record all discrepancies in JAK3_AP_RISKS.md.
```

---

# Milestone 12 — Implement Complete Pure APWorld Reachability Logic

## Human-readable summary

Archipelago needs a logical model of which missions and checks are reachable with the current items, independent of whether the runtime mission board has been implemented yet.

This milestone replaces permissive scaffolding with the documented Standard region graph, hidden completion events, route convergence, challenge exclusions, and five-of-seven finale logic. It prevents self-locks before more native hooks are added.

## Technical objective

Implement the complete generator-side default region graph and Standard access rules.

## Shared predicates

Implement and test:

```text
RANGED
BOARD_BOOST
TEMPLE_ORACLE
VEHICLE(n)
RELICS(n)
DONE(task_id)
```

## Required rule coverage

- Prologue/Spargus initiation.
- Spargus Field branch.
- Temple/Mines branch.
- Haven branch using the Milestone 11 decision.
- Freedom League branch.
- Wasteland Artifact branch.
- War Factory convergence.
- Precursor Network branch.
- Dark Maker branch.
- Five-of-seven finale.
- Story completion events.
- 38 reward-location rules.
- 24 selected side-challenge rules.
- 24 orb-threshold rules, or the proven reduced set.
- Orb progression exclusion above 300.
- Safe challenge exclusions.
- Early local Spargus Field Orders.
- Early local Blaster or Vulcan Fury.
- Option-dependent classifications resolved before item creation.

## Critical self-lock tests

- Task 11 does not require Dark Bomb.
- Task 27 does not require permanent Invisibility Statues.
- Task 29 does not require Jetboard.
- Task 42 does not require Dark Strike.
- Task 61 does not require Light Flight.
- Task 28 requires Invisibility Statues and Dark Bomb.
- Task 30 requires Jetboard and the resolved `BOARD_BOOST` capability; a separate Launch item is required only if the Milestone 11 decision keeps it independent.
- Blaster and Vulcan Fury satisfy RANGED.
- Scatter Gun and Peace Maker do not.
- Route items are not available only inside their own routes.
- Shadow native state cannot satisfy AP predicates.
- Five relics are sufficient; four are not.
- Every rule-referenced item is progression-classified.
- Every enabled `EXCLUDED` location is still reachable in all-state.

## Generation and compatibility tests

- `get_all_state()` reaches every enabled location.
- Victory is reachable.
- `fulfills_accessibility()` succeeds.
- Fixed-seed determinism.
- Multi-player generation.
- Local/non-local item constraints.
- `start_inventory_from_pool`.
- User exclusions and priorities.
- Item links/plando fail clearly if they violate the supported contract.
- Early guarantees remain valid after common option processing.
- No stale legacy mission-unlock logic remains.

## Non-goals

- Do not alter the native mission board.
- Do not add mission overlays.
- Do not add runtime shadow state.

## Completion gate

The exact supported default generates with correct Standard reachability, all-state accessibility, early guarantees, exclusions, and no documented self-lock.

## Suggested Codex prompt

```text
/plan

Implement only Milestone 12.

Replace permissive APWorld rules with the complete documented Standard graph,
using the Milestone 11 feasibility decisions. Add hidden DONE events, shared
predicates, early local guarantees, challenge/orb exclusions, and five-of-seven
finale logic.

Add targeted self-lock tests and full all-state/accessibility assertions.
Do not change native mission-board behavior.
```

---

# Milestone 13 — Implement Every Permanent Default Item

## Human-readable summary

The first vertical slice proves that a few permanent items can arrive safely, but a complete seed contains dozens of weapons, powers, upgrades, vehicles, route items, and relics.

This milestone implements the full permanent default inventory table. It keeps logical Archipelago ownership separate from native story props, reconstructs native unlocks from the AP ledger, and gives every supported permanent item a tested behavior before the project expands all mission rewards.

## Technical objective

Implement table-driven application and reconciliation for all 26 progression instances and all 28 useful instances in the supported default profile.

## Required item families

### Logical-only AP ownership

- Eight route authorizations.
  - Record ownership in the AP ledger.
  - Do not mutate mission state until Milestone 17.
- Seven Finale Relics.
  - Count only AP receipts.
  - Do not grant native Seal/Cipher/Astro-Viewer props.
  - Shadow native props remain Milestone 19 behavior.

### Permanent native capability/inventory

- Jetboard.
- Jetboard Launch, subject to the Milestone 11 decision.
- Invisibility Statues.
- Dark Bomb.
- Dark Strike.
- Light Flight.
- Blaster.
- Vulcan Fury.
- Three Progressive Wasteland Vehicle License stages.

### Useful permanent items

- Ten non-`RANGED` Morph Gun mods.
- Eight ammo-capacity upgrades.
- Four Progressive Armor stages.
- Jetboard Zap.
- Light Regeneration.
- Flash Freeze.
- Light Shield.
- Dark Blast.
- Ram 'Rod / Slam Dozer ownership.

## Required behavior

- Use one reviewed item-application table keyed by stable AP item ID.
- Record:
  - AP item family.
  - Maximum AP pool count.
  - Native grant/reconcile function.
  - Native cap.
  - Dependency closure.
  - Whether the item is ledger-only.
  - Whether it may apply while the game is unsafe.
- Reconciliation sets native permanent state from the AP ledger; it does not replay story rewards.
- Applying a Light power also establishes required base Light state.
- Applying a Dark power establishes required base Dark state.
- Progressive stages are monotonic and deterministic.
- Counts beyond native caps remain represented in the AP ledger without corrupting native state.
- A full item replay produces the same permanent inventory as a clean run.
- Native save reconstruction cannot leak shuffled rewards back into permanent ownership.
- AP mode off remains native.
- Unknown/default-unsupported IDs fail safely.
- Route authorization and relic receipt cannot accidentally trigger mission checks, native story state, or reward hooks.

## Required tests

Parameterize every permanent item definition for:

- First receipt.
- Duplicate packet.
- Duplicate item instance when legitimate.
- Count beyond native cap.
- Title menu/unsafe queue.
- Save/load.
- Game restart.
- Client restart.
- Index-zero replay.
- Native save reconstruction.
- AP recursion guard.
- AP mode off.
- Dependency closure.
- Logical-only items leave native story state unchanged.
- Item table and runtime grant table cover exactly the supported permanent pool.

Add focused tests for:

- Blaster/Vulcan ownership.
- All four armor stages.
- All three vehicle-license stages.
- Jetboard/Launch/Zap separation.
- Light/Dark base-state closure.
- Seven relics counted only from AP receipts.

## Non-goals

- Do not apply filler or consumable effects.
- Do not open route missions yet.
- Do not create shadow story props.
- Do not expand reward interception.
- Do not add traps.

## Completion gate

Every non-consumable item in the 54-instance progression/useful default pool has a deterministic ledger mapping, safe application path or intentional ledger-only behavior, full-replay reconstruction, and automated runtime coverage.

## Suggested Codex prompt

```text
/plan

Implement only Milestone 13.

Expand the proven permanent-item ledger/reconciliation path to every supported
progression and useful item. Keep route authorizations and finale relics
logical-only; do not mutate mission state or native story props for them.

Use a table-driven mapping, test every item family and native cap, and prove
that save reconstruction and index-zero replay rebuild the same permanent state.
Do not implement filler, traps, route opening, or reward expansion.
```

---

# Milestone 14 — Implement Exactly-Once Filler and Consumable Delivery

## Human-readable summary

The default pool contains many resource packs and refills. Unlike a permanent unlock, these are additive effects: accidentally applying the same Orb Pack twice changes the player's resources and cannot be fixed by simply rebuilding inventory.

This milestone creates the durable application receipt needed for consumables, then implements every supported filler family. Archipelago-delivered currency becomes spendable without advancing local collectible checks.

## Technical objective

Implement crash-safe, exactly-once application for all default filler effects.

## Required architecture

Before enabling any additive filler, prove one of these equivalent boundaries:

1. The game persistently records the received-item index/command receipt in the same durable operation as applying the effect; or
2. The effect is represented as an idempotent target derived from persistent AP credit/debit accounting.

A Python-side “sent” flag plus a transient game response is not sufficient because a crash may occur after the native effect but before the response is persisted.

Document the selected method in an ADR and update the state schema/version if required.

## Supported filler families

- Precursor Orb Packs: 5, 10, and 25.
- Skull Gem Packs: 1, 3, and 5.
- Red, yellow, blue, and dark ammo refills.
- Health refill.
- Light Eco refill.
- Dark Eco refill.
- Vehicle repair.
- Vehicle turbo/fuel refill.

## Required behavior

- Each filler receipt is keyed by its Archipelago received-item index.
- A receipt can transition only through explicit states such as:
  - Received.
  - Waiting for safe state.
  - Applying.
  - Applied.
- Repeating an applied index cannot apply the effect again, including after:
  - Client restart.
  - Game restart.
  - Full index-zero replay.
  - Lost command response.
- An unmatched index/item history is quarantined rather than guessed.
- Unsafe effects remain queued through cutscene, death, load, transition, and incompatible vehicle state.
- Capped refills never overflow native limits.
- AP Orb Packs:
  - Increase spendable orb balance.
  - Never increase `local_earned_precursor_orbs`.
- AP Skull Gem Packs:
  - Increase spendable gem balance.
  - Never increase `local_earned_skull_gems`.
- Native locally earned currency follows a separate hook/path.
- Spending currency does not modify received-item history.
- AP mode off remains native.
- The status output reports queued/applied filler without exposing internal IDs to normal users.

## Required tests

For every filler family or table-driven representative:

- First receipt.
- Duplicate packet.
- Duplicate command.
- Crash after receipt persistence and before application.
- Crash after native effect and before client result persistence.
- Client restart.
- Game restart.
- Index-zero replay.
- Item received while unsafe.
- Transition from unsafe to safe.
- Native cap.
- Invalid payload.
- AP mode off.

Currency-specific tests:

- AP Orb Pack does not trigger local orb thresholds.
- AP Gem Pack does not trigger local gem thresholds.
- Spending and save/load preserve the correct spendable amount.
- Full replay does not refund already spent currency or duplicate already applied packs.
- Native earned currency remains distinguishable from AP-delivered currency.

## Non-goals

- No traps.
- No DeathLink.
- No local orb-threshold locations yet.
- No secret purchases.

## Completion gate

Every default filler item applies once and only once across both crash windows, restarts, and full replay, while AP-delivered currency remains completely separate from locally earned collectible progress.

## Suggested Codex prompt

```text
/plan

Implement only Milestone 14.

First prove and document a durable exactly-once boundary for additive game
effects. Then implement all supported filler families keyed by ReceivedItems
index. Test the crash-after-effect window explicitly.

AP Orb/Gem Packs must be spendable but must never advance local-earned counters.
Do not implement traps, DeathLink, orb-threshold locations, or secret purchases.
```

---

# Milestone 15 — Build the Generic Mission-Equipment Overlay System

## Human-readable summary

Lesson missions and scripted sequences must temporarily provide exact equipment without permanently granting an Archipelago item.

This milestone creates one persistent, reversible overlay mechanism and proves it with Dark Bomb/Dark Blast in task 11 and Invisibility Statues in task 27. A received permanent copy must survive cleanup.

## Technical objective

Implement table-driven temporary mission overlays with idempotent cleanup and AP-ledger reconciliation.

## Overlay lifecycle

1. Validate a compatible bound AP save.
2. Persist the overlay descriptor and activation point.
3. Apply only the exact temporary native state.
4. Keep it through the documented mission segment.
5. Clean it on:
   - Success.
   - Failure.
   - Retry.
   - Abort.
   - Death.
   - Save/load.
   - Level transition.
   - Disconnect.
   - Game restart.
6. Reconcile permanent inventory from the AP ledger.
7. Retain a permanent copy received during the overlay.
8. Never emit a reward/location merely because the overlay granted something.
9. Make repeated cleanup harmless.

## Proof cases

### Task 11

- Dark Bomb.
- Dark Blast.
- Activate only at the lesson node.
- Remove after cleanup unless permanently owned.

### Task 27

- Invisibility Statues.
- Activate at the reward node.
- Retain through return teleport/mission exit.
- Remove after cleanup unless permanently owned.

## Required tests

- Every lifecycle exit.
- Permanent copy arrives before activation.
- Permanent copy arrives while active.
- Permanent copy arrives during cleanup.
- Duplicate activation.
- Duplicate cleanup.
- Game restart with active overlay.
- Corrupt/stale overlay descriptor.
- No AP receipt.
- No AP location.
- Later task 28 still requires permanent ownership.

## Non-goals

- Do not add all mission profiles.
- Do not implement shadow story state.
- Do not bootstrap permanent cross-world gates before their intended acquisition.

## Completion gate

Tasks 11 and 27 are completable with temporary lesson state, cleanup is reliable across every exit, and later content still sees only permanent AP ownership.

## Suggested Codex prompt

```text
/plan

Implement only Milestone 15.

Create the generic persistent overlay subsystem and prove it with task 11
Dark Bomb/Dark Blast and task 27 Invisibility Statues. Use the existing command
IDs and AP ledger. Test every cleanup path and permanent receipt during an
active overlay.

Do not add other mission profiles or shadow story state.
```

---

# Milestone 16 — Expand Permanent Reward Interception to All 38 Major Rewards

## Human-readable summary

The vertical slice proved one native reward can become an Archipelago location without breaking the mission.

This milestone turns that proof into a table-driven system covering all 38 default major reward moments. Native permanent grants are suppressed in AP mode, while story presentation and task closure remain native.

## Technical objective

Expand the proven interception architecture to the complete default reward table.

## Required implementation shape

Use a reviewed table that records:

- Native task/node identity.
- Native reward command(s).
- AP location ID.
- Permanent commands to suppress.
- Temporary/story commands to allow.
- Lesson-overlay handoff through the Milestone 15 overlay subsystem, when applicable.
- Recursion-guard behavior.
- Save-reconstruction behavior.
- AP-off behavior.

Avoid scattered node-specific conditionals when a common dispatcher can represent the rule safely.

## Required subdivisions

Complete and review as separate Codex tasks:

1. Spargus initiation.
2. Spargus field.
3. Temple, Volcano, and Mines.
4. Early Haven.
5. Midgame and Wasteland artifacts.
6. Late game.

Each subdivision must leave tests green and must not begin the next group automatically.

## Required behavior for every reward

- Stable AP location.
- Durable AP completion bit.
- Persistent outbox entry.
- Suppression of only the shuffled permanent grant.
- Dialogue/cutscene/task closure preserved.
- AP recursion guard.
- Duplicate-safe replay.
- Save reconstruction compatibility.
- Offline completion.
- AP mode off unchanged.
- Applying the AP item never sends the reward location.

## Explicit exclusions

Do not treat as default reward checks:

- Opening setup.
- Temporary Board Trail add/remove.
- Final-boss Jetboard remove/restore.
- Crystal-only nodes.
- Other setup-only commands.

## Required tests

For every reward or representative table-driven parameterization:

- First completion.
- Replay.
- Death before and after reward.
- Save/load.
- Game restart.
- Client restart.
- Offline/reconnect.
- AP item application.
- AP mode off.
- Native save reconstruction.
- Mixed reward nodes preserve unrelated state.

## Completion gate

All 38 major reward moments use one consistent, audited interception path and permanent inventory always reconciles from the AP ledger.

## Suggested Codex prompt

```text
/plan

Implement the next approved Milestone 16 reward subgroup only.

Use the table-driven interceptor proven in Milestone 10. For every included
node, suppress only shuffled permanent grants, preserve all story/task behavior,
set one durable AP location, and protect AP-delivered grants with the recursion
guard.

Do not proceed to the next subgroup in the same change.
```

---

# Milestone 17 — Implement Route Authorizations and the Tiered Mission Board

## Human-readable summary

Broad route authorizations are the main feature that makes this more than a vanilla-order item shuffle.

This milestone makes the native mission board reflect Archipelago reachability and safely initializes authorized story state without marking unrelated missions complete. The Haven implementation follows the explicit Milestone 11 decision.

## Technical objective

Implement all eight route authorizations and the default tiered mission-board flow.

## Implementation order

1. Spargus Field Orders.
2. Temple Expedition Orders.
3. Freedom League Orders.
4. Wasteland Artifact Intel.
5. War Factory Coordinates.
6. Precursor Network Access.
7. Dark Maker Targeting Data.
8. Haven City Access last.

## Required behavior

An authorization may initialize only the audited minimum:

- Mission masks.
- Act state.
- Level-open state.
- Native pass state.
- Hub actors.
- Mission-board entry.
- Return-to-hub support.

It must not:

- Complete the mission.
- Complete unrelated missions.
- Send an AP location.
- Grant a shuffled permanent reward.
- Increment AP relics.
- Satisfy AP item logic through native shadow flags.

Mission-board availability must derive from:

- AP route ownership.
- Durable mission-completion state.
- Required permanent capability ownership.
- Safe native runtime state.

If an authorization item arrives in an unsafe state, queue its native initialization until safe.

## Haven requirements

Use the Milestone 11 PASS or fallback decision. Keep dedicated tests for:

- Geometry.
- Passages.
- Actors.
- Mission masks.
- Task 35.
- Hub return.
- Save/load.
- No false Act I checks.
- No reward leakage.

## Required tests

- Each authorization opens only its intended group.
- Parent/convergence rules.
- Item received at title/load/cutscene/death.
- Duplicate authorization.
- Full replay.
- Save reconstruction.
- Mission completion does not disappear.
- Native mission board and APWorld logic agree.
- AP mode off remains native.
- Vanilla/fallback developer path remains available until default runtime acceptance passes.

## Completion gate

Every default authorization safely opens the same mission content modeled by the APWorld, and no route initialization falsifies an AP check or native mission completion.

## Suggested Codex prompt

```text
/plan

Implement the next approved Milestone 17 authorization only, in the documented
order. Use the Milestone 11 feasibility decision for Haven.

Initialize only the minimum audited native state. Prove that no unrelated task,
AP check, shuffled reward, or relic count changes. Do not automatically proceed
to the next authorization.
```

---

# Milestone 18 — Expand Mission Bootstrap Profiles

## Human-readable summary

Many Jak 3 missions require a specific vehicle, actor, gun course loadout, rail vehicle, fighter, mech, or other scripted equipment. Randomizing all of those would create brittle self-locks.

This milestone expands the generic overlay/profile system so every default mission receives its mission-only tools without leaking permanent ownership.

## Technical objective

Create reviewed, table-driven bootstrap profiles for all documented default mission equipment.

## Required subdivisions

### 16A — Spargus and early Wasteland

- Training/race vehicles.
- Leaper sections.
- Turrets.
- Arena and gun-training loadouts.

### 16B — Temple, Volcano, and Mines

- Flut-Flut/glider.
- Daxter sections.
- Mine equipment.
- Bomb train.
- Remaining lesson powers used in these missions.

### 16C — Haven and Sewers

- Haven vehicles.
- Missile and Blast Bot sequences.
- Gun courses.
- Board Trail.
- Mission-only shooters.

### 16D — War Factory and late game

- Fighter.
- Mech.
- Factory vehicle.
- Dark Maker suit.
- Ram 'Rod introduction.
- Subrail/walker/finale state.

Each subdivision is a separate Codex task.

## Required profile properties

- Stable profile ID.
- Activation conditions.
- Exact temporary grants.
- Exact cleanup conditions.
- Unsafe-state handling.
- Save/load behavior.
- Permanent-ownership reconciliation.
- AP-off behavior.
- Test fixture/procedure.

## Permanent gates that must not be bootstrapped

- Jetboard for later progression missions.
- Jetboard Launch.
- Permanent Invisibility Statues in tasks 28/30.
- Dark Bomb for task 28.
- Vehicle-license capability outside an introduction mission.
- Dark Strike after task 42.
- Light Flight after task 61.
- Blaster/Vulcan where Standard logic explicitly requires RANGED.

## Required tests

For each profile or table-driven representative:

- Start without permanent ownership.
- Complete.
- Fail.
- Retry.
- Abort.
- Die.
- Save/load.
- Game restart.
- Receive permanent copy while active.
- Duplicate activation/cleanup.
- No AP receipt/check from the temporary state.

## Completion gate

Every default mission can acquire its mission-only actors/equipment while every cross-world progression gate remains permanent and AP-controlled.

## Suggested Codex prompt

```text
/plan

Implement the next approved Milestone 18 profile subgroup only.

Use table-driven bootstrap descriptors and the generic overlay lifecycle. Add
all lifecycle tests, verify permanent AP ownership after cleanup, and explicitly
test that no documented cross-world progression gate is bootstrapped.

Do not proceed to another subgroup in the same change.
```

---

# Milestone 19 — Implement Shadow Native Story State

## Human-readable summary

Some mission scripts require native passes, amulets, relic props, or story flags even though simplified Archipelago logic uses broad authorizations and logical relics.

This milestone creates a subsystem separate from both permanent AP inventory and temporary equipment. It supplies only the native props a script needs and can never count toward Archipelago progression.

## Technical objective

Implement isolated shadow-story profiles, first for task 30 and task 63.

## Proof cases

### Task 30

Supply only the native Seal/amulet/portal presentation state identified by Milestone 11.

### Task 63

Supply only the five native Astro-Viewer artifact flags/props identified by Milestone 11.

## Required lifecycle

1. Derive the exact profile from the mission.
2. Record pre-existing native values.
3. Persist the active shadow descriptor.
4. Set only missing required native state.
5. Never call the AP received-item grant path.
6. Never change AP item counts.
7. Never change the AP relic count.
8. Never send a reward location.
9. Restore transient values on exit/load/restart.
10. Preserve legitimate native world changes caused by mission completion.
11. Reconcile permanent AP inventory afterward.
12. Make cleanup idempotent.

## Required tests

- Mission works with zero corresponding AP relics.
- AP relic count remains zero.
- Existing native state is preserved.
- Partial pre-existing state.
- Save/load during profile.
- Death/abort/disconnect.
- Game restart.
- Duplicate activation/cleanup.
- Task completion preserves only legitimate state.
- Full item replay does not absorb shadow props.
- Shadow state never satisfies `RELICS(n)` or another AP predicate.

## Non-goals

- No canonical story-item mode.
- No new AP items.
- No use of shadow state as generation logic.

## Completion gate

Tasks 30 and 63 execute with their required native props while the AP ledger and five-of-seven relic logic remain completely unchanged.

## Suggested Codex prompt

```text
/plan

Implement only Milestone 19.

Create a shadow-story subsystem separate from permanent inventory and mission
equipment. Implement the task-30 and task-63 profiles using the exact Milestone
11 findings. Persist/restore native state and prove AP item/relic counts never
change.

Canonical story-item mode remains unsupported.
```

---

# Milestone 20 — Add All 61 Story Mission Completion Checks

## Human-readable summary

The default world treats each supported major story mission completion as one Archipelago location.

This milestone expands the proven durable completion hook to tasks 10–35 and 37–71. Each mission sends once, remains complete through replay and restart, and stays separate from its native reward check.

## Technical objective

Implement all default story-completion locations through the persistent outbox.

## Required coverage

Include:

- Tasks 10–35.
- Tasks 37–71.

Exclude:

- Tasks 6–9 from the default.
- Task 36.
- Task 72 as a normal network location.

## Required behavior

- Stable AP location ID.
- Verified native close-task or custom durable hook.
- Permanent AP bit.
- Persistent outbox entry.
- Replay-safe.
- Offline-safe.
- Save/load-safe.
- No reward granting.
- No volatile actor identity.
- Mission completion and reward moment remain distinct locations.
- Existing completed native state is not auto-imported from a progressed vanilla save; first release requires a fresh AP-bound save.
- AP mode off does not send checks.

## Required subdivisions

Implement and review by chapter:

1. Spargus initiation.
2. Spargus field.
3. Temple/Mines.
4. Haven recon.
5. Freedom League.
6. Wasteland artifacts.
7. War Factory and late game.

## Required tests

For each group:

- First completion.
- Replay.
- Death at closure.
- Save/load.
- Game restart.
- Client restart.
- Offline/reconnect.
- Duplicate outbox send.
- Reward location remains separate.
- Mission-board state agrees with AP completion state.
- Task 36 never appears.
- Task 71 sends its own location once.

## Completion gate

All 61 story-completion locations send exactly once and remain correct through replay, restart, reconnect, and native save reconstruction.

## Suggested Codex prompt

```text
/plan

Implement the next approved Milestone 20 chapter group only.

Use verified close-task hooks, durable AP bits, and the existing persistent
outbox. Keep mission-completion and reward locations distinct. Test replay,
death at closure, save/load, both process restarts, offline completion, and AP
mode off.

Do not add task 36 or task 72 as network locations.
```

---

# Milestone 21 — Add the 24 Selected Side-Challenge Checks

## Human-readable summary

The default includes a finite set of optional races and challenges, but not the unaudited orb hunts, medal sets, or repeatable enemy drops.

This milestone adds source task IDs 114–137, bypasses grind-based entry costs safely, and preserves placement exclusions for the difficult challenges.

## Technical objective

Implement the selected side-challenge location family and default free-entry behavior.

## Required behavior

- Native task IDs 114–137.
- Stable AP location IDs.
- Durable completion bits.
- One send per challenge.
- Replay-safe outbox.
- Conservative Standard rules matching the APWorld.
- Default kiosk/challenge costs bypassed without auto-completing anything.
- Fixed challenge loadouts supplied where documented.
- Ratchet & Clank course access pre-opened only under the documented default behavior.
- AP-delivered gems/orbs do not count toward local-earned sanity totals.

## Default placement exclusions

Keep these enabled but `EXCLUDED`:

```text
127
129
130
131
132
136
```

## Required tests

- Every challenge sends once.
- Replay does not duplicate.
- Free entry does not send a check.
- Free entry does not spend or require farmable currency.
- Fixed challenge loadout cleanup.
- Save/load and reconnect.
- Excluded challenges reject progression/useful placement.
- APWorld and runtime native task IDs agree.
- Task 88 remains reserved/normalized for later experimental content but is not accidentally enabled here.

## Non-goals

- No orb-hunt IDs 73–113.
- No medals.
- No secret purchases.
- No repeatable enemy drops.

## Completion gate

All 24 selected side challenges are finite, persistent, replay-safe locations with logic-safe free entry.

## Suggested Codex prompt

```text
/plan

Implement only Milestone 21.

Add side tasks 114–137, their durable AP bits/outbox hooks, default free-entry
behavior, fixed challenge profiles, and the six documented placement
exclusions. Do not enable orb hunts, medals, secret purchases, or repeatable
drops.
```

---

# Milestone 22 — Add Local-Earned Precursor Orb Thresholds

## Human-readable summary

The default does not need 600 individual pickup identities. It sends checks at total locally earned orb thresholds instead.

This milestone implements a monotonic local-earned counter, keeps AP Orb Packs spendable but logically separate, and enables thresholds only through the amount proven obtainable in Milestone 11.

## Technical objective

Implement the default orb-threshold location family and its separate accounting model.

## Required threshold set

Preferred, when Milestone 11 proves all 600:

```text
25, 50, 75, ... 600
```

If not proven, stop at the highest proven multiple of 25 and update:

- Enabled location count.
- Filler count.
- Slot data.
- Tests.
- Documentation.

Reserved IDs above the proven maximum remain reserved.

## Required accounting behavior

### Native locally earned orb

- Increases native spendable balance.
- Increases monotonic AP local-earned total exactly once.
- May trigger multiple thresholds.
- Persists independently of spending.

### AP-delivered Orb Pack

- Increases native spendable balance.
- Does not increase local-earned total.
- Cannot trigger thresholds.

### Spending

- Does not reduce local-earned total.
- Does not unset threshold bits.

### Reconstruction/replay

- Native save reconstruction cannot count the same grant twice.
- Replayed mission/challenge rewards cannot count twice unless they are genuinely repeatable and explicitly excluded from local-earned accounting.
- Threshold bits remain authoritative.

## Placement behavior

- Thresholds above 300 are enabled but `EXCLUDED`.
- They may hold filler or traps only.
- `accessibility: full` still requires them to be reachable in all-state and in the proven runtime collectible model.

## Required tests

- Cross one threshold.
- Cross several thresholds in one award.
- Exact boundary.
- Spend after earning.
- AP Orb Pack.
- Save/load.
- Game restart.
- Client restart.
- Offline completion.
- Duplicate native reward reconstruction.
- Full item replay.
- Threshold replay.
- Exclusion above 300.
- Maximum obtainable threshold matches the Milestone 11 decision.

## Completion gate

Every enabled orb threshold is monotonic, persistent, replay-safe, and completely unaffected by AP-delivered currency.

## Suggested Codex prompt

```text
/plan

Implement only Milestone 22 using the proven maximum from Milestone 11.

Create a separate monotonic locally-earned orb counter and threshold bits.
Native earning may trigger thresholds; AP Orb Packs must never do so. Handle
multi-threshold jumps, spending, save reconstruction, replay, offline upload,
and exclusions above 300.
```

---

# Milestone 23 — Implement the Complete Default Finale and Goal

## Human-readable summary

The final mission requires both story progression and any five of the seven shuffled finale relics. Completing the final city-win state then reports Archipelago goal status.

This milestone joins the relic ledger, final mission access, final mission location, non-networked Victory event, and duplicate-safe goal reporting.

## Technical objective

Implement the complete default finale contract.

## Required behavior

- Define the seven-item `Finale Relics` group.
- Count each named relic at most once for runtime goal purposes.
- Require any five.
- Shadow native props never count.
- Task 71 requires:
  - DONE(70).
  - Five relics.
  - RANGED.
- Task 71 completion sends its normal network location once.
- Task 72/city-win creates the runtime goal.
- Generator Victory remains a locked event with no network ID.
- Persist `goal_completed`.
- Send `StatusUpdate(CLIENT_GOAL)`.
- Resend goal status safely after reconnect.
- Do not consume an item-pool slot for Victory.

## Required tests

- Every four-relic combination fails.
- Every valid five-relic combination succeeds.
- Duplicate replay/packet of one relic does not count as another unique relic.
- Full inventory replay.
- Shadow state does not count.
- Task 71 access.
- Task 71 location sends once.
- Task 72 goal triggers once.
- Client disconnect at goal.
- Game restart after goal.
- Client restart after goal.
- Goal resend.
- AP mode off.
- Server collect/release behavior remains server-controlled.

## Completion gate

The default game can be completed only after the mission chain and five unique relics are satisfied, and goal status survives every reconnect/restart path.

## Suggested Codex prompt

```text
/plan

Implement only Milestone 23.

Add the seven-relic group, unique five-of-seven runtime count, task-71 access,
task-71 location, task-72/city-win goal, persistent goal state, and duplicate-
safe StatusUpdate resend. Prove shadow props and duplicate receipts cannot
inflate the relic count.
```

---

# Milestone 24 — Full Default Integration, Accessibility, and Reliability Testing

## Human-readable summary

All major systems now exist. This milestone proves they work together as one complete default game rather than as isolated tests.

A release candidate must generate correctly, remain fully accessible, survive ordinary failure/restart cases, and complete at least one real multiworld seed from start to finish.

## Technical objective

Validate the complete supported default in the generator, client, OpenGOAL runtime, and manual play.

## Generator verification

At minimum:

```python
state = multiworld.get_all_state()
assert multiworld.has_beaten_game(state, player)

for location in multiworld.get_locations(player):
    assert location.can_reach(state), location.name

assert multiworld.fulfills_accessibility(state)
```

Verify final counts based on the Milestone 11 orb decision. Preferred target:

```text
147 network locations
26 progression instances
28 useful instances
93 filler instances
```

Also verify:

- Every rule item is progression-classified.
- Excluded locations cannot receive progression/useful.
- Early route and ranged guarantees.
- No self-locks.
- Deterministic tables, slot data, and hashes.
- No retired ID reuse.
- Multi-player generation.
- Standard placement controls.
- No unsupported option can generate.

## Fuzzing tiers

### Pull request / local fast suite

- At least 50 default seeds.
- Targeted option-validation tests.

### Scheduled or manually triggered development suite

- At least 1,000 default seeds.

### Release-candidate suite

- At least 10,000 default seeds.

Record:

- Sphere-zero location count.
- Early branch count.
- Progression drought length.
- Route-item impact.
- Relic sphere distribution.
- Difficult-check progression frequency.
- Fill failures and seed reproduction data.

## Runtime verification matrix

- Fresh save binding.
- Wrong save/seed rejection.
- Existing bound save.
- Title-menu-first and server-first startup.
- Full disconnect/reconnect.
- Client restart.
- Game restart.
- Full item replay.
- Packet gap.
- Offline checks.
- Native save reconstruction.
- Every overlay cleanup class.
- Shadow cleanup.
- Mission replay.
- Side challenge replay.
- Orb accounting.
- Goal resend.
- Table/protocol mismatch.
- Corrupt sidecar recovery.

## Manual playthrough target

Complete at least one full default seed with:

- `accessibility: full`.
- Default YAML.
- At least one other game/slot in the multiworld.
- Normal save/load.
- One deliberate server disconnect.
- One game restart.
- One client restart.
- One forced full item replay.
- Several remote items.
- Several local items.
- At least one completion performed while the AP server is unavailable.

## Acceptance requirements

- No progression loss.
- No duplicate checks.
- No permanent native reward leakage.
- No temporary overlay leakage.
- No shadow relic leakage.
- No unreachable enabled locations.
- No false mission completion.
- No unexplained protocol errors.
- Reproducible logs for every failure.

## Completion gate

A full default seed can be generated, played, saved, restarted, reconnected, replay-synchronized, and finished without violating any architectural invariant.

## Suggested Codex prompt

```text
/plan

Implement only Milestone 24 verification and fixes required by failures found
within that verification. Do not add new options or content.

Run the complete generator assertions, tiered fuzzing, runtime failure matrix,
and one documented full default multiworld playthrough. Record reproduction
data for every failure and do not mark the milestone complete with an
unresolved invariant violation.
```

---

# Milestone 25 — Polish Player-Facing Status and Diagnostics

## Human-readable summary

Basic diagnostics must exist throughout development, but a normal player should not need source code or a debugger to understand a wrong save, queued item, disconnected game, incompatible version, or pending check.

This milestone turns the existing technical observability into concise player-facing status and recovery guidance.

## Technical objective

Provide usable status in the Python client and, where low-risk, a small OpenGOAL debug/status view.

## Required information

- AP server connected/disconnected.
- OpenGOAL attached/detached.
- Compatible/incompatible protocol.
- Game integration version.
- Table/slot-data versions and hashes.
- Seed, team, slot, and native save identity.
- Bound/unbound/wrong-save status.
- Current task/level and safe-state summary.
- Last received item.
- Pending item count.
- Pending outgoing check count.
- Last server-confirmed check.
- Active mission overlay.
- Active shadow profile.
- Item queued until safe.
- Goal state.
- Last error with actionable wording.

## Recommended commands

- `/status`
- `/diagnostics`
- `/resync`
- `/pending`
- `/binding`
- `/version`

Recovery commands must not bypass seed binding or mutate permanent progress without an explicit, audited operation.

## Support bundle

Create a safe diagnostic bundle containing:

- Client log.
- OpenGOAL/compiler log.
- Protocol snapshot.
- Version/hash summary.
- Sanitized state metadata.
- Recent command/results.

Do not include server passwords or unnecessary personal paths/secrets.

## Required tests

- Every common error has clear text.
- Wrong seed/save.
- Table mismatch.
- Item queued.
- Outbox pending.
- Server reconnect.
- Game reconnect.
- Corrupt sidecar.
- Goal completed.
- Support bundle redaction.
- UI/status code cannot change gameplay state accidentally.

## Non-goals

- No large custom UI framework.
- No experimental gameplay options.
- No silent error suppression.

## Completion gate

A tester can diagnose the common connection, binding, delivery, persistence, and version problems using only the client/status output and support bundle.

## Suggested Codex prompt

```text
/plan

Implement only Milestone 25.

Polish the existing diagnostics into player-facing status commands and a
sanitized support bundle. Reuse the authoritative protocol/persistence state;
do not create a second state model. Keep UI scope small and make every error
actionable without hiding serious failures.
```

---

# Milestone 26 — Release Documentation, Packaging, and Clean-Room Validation

## Human-readable summary

The repository already has an APWorld build and OpenGOAL installation/launch pipeline, but a development pipeline is not yet a public release.

This milestone pins compatibility, packages the exact tested artifacts, documents fresh installation and recovery, and proves that someone outside the development environment can complete a connected seed.

## Technical objective

Produce the first default-only beta release package and its complete installation/support documentation.

## Required packaging

- Versioned `.apworld`.
- Versioned OpenGOAL bridge/mod files.
- Installer/repair tooling.
- Uninstaller or precise removal instructions.
- Default YAML.
- Checksums.
- Release notes.
- License/attribution.
- Compatibility manifest.

## Compatibility manifest

Pin:

- Jak3-AP version.
- APWorld version.
- Protocol version.
- Game integration version.
- Slot-data/state schema versions.
- Item/location/mission table hashes.
- Required Archipelago version range.
- Required OpenGOAL commit/build.
- Supported operating systems.
- Known unsupported combinations.

## Required documentation

- Install Archipelago/APWorld.
- Install OpenGOAL and required Jak 3 data.
- Install/repair the game bridge.
- Generate the supported YAML.
- Generate/host a seed.
- Launch client and game.
- Bind a fresh save.
- Save backup.
- Reconnect/resync.
- Move between save slots safely.
- Update the mod.
- Handle an incompatible state.
- Gather logs/support bundle.
- Report a bug.
- Known limitations.
- Unsupported options.
- Recovery from partial installation.
- Complete removal.

## Clean-room validation

Use a machine or disposable environment that did not develop the project.

Test:

- Clean APWorld installation.
- Clean generation.
- Clean OpenGOAL install/build.
- Clean bridge install.
- Launch from documented commands/UI.
- Bind a new save.
- Complete a connected test seed.
- Restart/reconnect.
- Upgrade/repair.
- Uninstall.
- No writes to source-reference trees.
- Documentation paths and screenshots match the release.

At least one tester who did not implement the project should follow the guide without undocumented steps.

## Release labeling

Recommended first public label:

```text
Jak3-AP default-only beta
```

Experimental options remain rejected even if partial code exists.

## Completion gate

A non-developer can install the released artifacts in a clean environment, generate the supported default, bind a fresh save, complete a connected test seed, collect a support bundle, and remove or repair the installation using only the published documentation.

## Suggested Codex prompt

```text
/plan

Implement only Milestone 26 release hardening.

Package the already-tested default-only beta, pin all compatibility versions and
hashes, complete installation/recovery/uninstall documentation, and perform a
clean-room test. Do not enable experimental options or add new gameplay
features during release packaging.
```

---

# Later Milestones — After the Default-Only Beta

Do not mix these into Milestones 4–26. Each feature needs its own design delta, registry/version impact, generation rules, runtime behavior, migration behavior, tests, and manual acceptance.

## Recommended expanded-safe order

1. Improved in-game AP status UI.
2. DeathLink.
3. Safe traps.
4. Medal checks.
5. Secret-purchase checks.
6. Secret upgrades and vehicles.
7. Audited mission milestones.

## Recommended experimental order

1. Orb-hunt sanity after per-target audit.
2. Regional orb bundles.
3. Individual static collectibles.
4. Individual vehicle shuffle.
5. Canonical passes and amulets.
6. Chapter shuffle.
7. Full mission shuffle.
8. Expert movement alternatives.
9. Physical entrance shuffle.

An option remains rejected until all of the following are complete:

- Stable IDs.
- Option resolution.
- Item classifications.
- Full APWorld rules.
- Runtime hooks.
- Persistence/migration effects.
- All-state accessibility.
- Fuzzing.
- Manual runtime test.
- Documentation.

Partial supporting code is not enough to make an option selectable.
