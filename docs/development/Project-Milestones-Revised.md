# Jak 3 Archipelago — Revised Remaining Project Milestones

**Applies after:** Milestones 0–6 completed; Milestone 7 implementation committed as `0cdc04e`; formal live acceptance pending  
**Repository review basis:** commit `0cdc04e` plus the complete attached Milestone 7 implementation/review history  
**Design target:** OpenGOAL Jak 3 + Archipelago, design version 0.3  
**First-release scope:** one supported default profile only

This revision preserves the established Milestones 4–26 numbering. Milestones 4–6 remain completed contracts, and **Milestone 7 is preserved exactly as previously written**. Commit `0cdc04e` is treated as its implementation result, not as proof of its remaining interactive acceptance gate. **Milestone 7.1** adds diagnostics around the committed implementation, and **Milestone 7.2** performs the real save/restart matrix, measures overhead, and freezes the control architecture before Milestone 8. No existing whole-number milestone is renumbered or displaced.

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


### Review, complexity, and stop rules

The Milestone 7 history showed that an unbounded sequence of broad review-agent passes over one large cross-layer diff is inefficient and can eventually produce false positives as well as valid defects. Future milestones use this review policy:

1. Split work before implementation when one task crosses more than two independently stateful boundaries, such as server protocol, Python persistence, native save I/O, live GOAL state, or installer/update activation.
2. Prefer reviewable sub-tasks whose production diff is small enough for one human to understand. Tests and generated evidence do not count against that goal, but a large production diff must be justified explicitly.
3. Before coding a lifecycle feature, write its state-transition table and identify the authoritative owner, durability boundary, identity, restart behavior, and unsupported transitions.
4. Use one implementation review, one focused adversarial review of the changed boundaries, and the milestone acceptance run. Additional broad re-reviews require a new failing test, a reproduced runtime failure, or direct source evidence.
5. A review finding must state a reachable transition, expected behavior, observed behavior, severity, and supporting source/test evidence. Purely hypothetical hardening is recorded rather than implemented unless the failure could corrupt AP progress, bind the wrong save, crash normal input, or violate a documented supported workflow.
6. After no credible P1/P2 findings remain and the required acceptance matrix passes, stop adding defensive branches. Later discoveries become focused regression fixes; they do not reopen the entire milestone.
7. Development-only hot reload is not automatically a supported player workflow. The release policy may require a clean game restart after bridge/APWorld updates. Do not add more hot-reload state preservation unless that workflow remains intentionally supported and is tested.
8. Future OpenGOAL gameplay systems should be added in separate modules rather than continually enlarging the Milestone 7 control bridge. The existing `archipelago.gc` remains the protocol/runtime/save-binding core.

### Cross-cutting diagnostic contract for Milestones 7.1–26

Milestone 7.1 establishes the diagnostic API, event registry, storage, retention, redaction, and support-bundle contract around the committed Milestone 7 implementation. Milestone 7 itself is not retroactively changed. Milestone 7.2 then uses those diagnostics for the remaining interactive acceptance and performance baseline. Every milestone from Milestone 8 onward that adds or changes runtime behavior must use the Milestone 7.1 API rather than creating unrelated free-form logging.

For each meaningful state transition, command, durable write, native hook, recovery path, rejection, retry, and externally visible error, the implementing milestone must:

1. Emit a stable, documented event name from the shared diagnostic-event registry.
2. Include the relevant correlation identity, such as command ID, received-item index, location ID, task ID, overlay/profile ID, state revision, or goal update ID.
3. Record the result after the authoritative durability or native-application boundary, not merely the attempted action.
4. Record rejected and duplicate/idempotent paths distinctly from successful first application.
5. Avoid passwords, authentication tokens, credential-bearing URLs, raw native-save identities, arbitrary packet dumps, full sidecar contents, or uncontrolled GOAL forms.
6. Keep diagnostic failure non-fatal: an unwritable log or malformed optional diagnostic event must not mutate gameplay state, skip persistence validation, or crash the game/client.
7. Add tests for the event's success, duplicate/idempotent, rejected/error, and restart/recovery paths where those paths exist.
8. Prefer state transitions and sampled health summaries over high-frequency polling noise. A one-second heartbeat must not generate normal INFO-level events indefinitely.
9. Preserve a concise human-readable message while keeping machine decisions in stable codes and structured fields.
10. Update the diagnostic-event catalogue and support-bundle field allowlist when new event fields are introduced.

---

## 3. Numbering decision and downstream wording changes

| Milestone | Treatment in this revision |
| --- | --- |
| Milestones 4–6 | Preserved as completed contracts. Milestone 7.1 may instrument their paths without changing their behavior. |
| Milestone 7 | Preserved exactly as previously written. Commit `0cdc04e` is implementation-complete, but its existing live save/copy/restart completion gate is still pending. |
| **Milestone 7.1** | Structured diagnostic logging and forensic support bundles around the committed Milestone 7 behavior. It must not redefine protocol or save-binding semantics. |
| **Milestone 7.2** | New validation-first milestone: execute the real runtime matrix, measure startup/runtime cost, define the supported update/reload policy, and freeze Protocol 3 before gameplay traffic. |
| Milestones 8–24 | Keep their existing numbers and functional scope. Their wording adds subsystem-specific diagnostic-event and support-evidence requirements and requires Milestone 7.2 acceptance before real gameplay transport. |
| Milestone 25 | Keeps its number, but becomes player-facing status, recovery guidance, and diagnostic-export UX. It reuses Milestone 7.1 rather than creating the logger late in development. |
| Milestone 26 | Keeps its number and adds diagnostic schema, retention, redaction, and support-bundle validation to release hardening. |

This ordering gives the logger access to the committed Milestone 7 runtime snapshot and idempotent command channel, uses it to capture the remaining live acceptance evidence, and still places both observability and protocol freeze before real `ReceivedItems`, real location traffic, reward interception, overlays, route mutation, and finale handling.

---

## 4. Diagnostic logging review and architectural decision

### Current foundation to preserve

At commit `0cdc04e`, the project already has a useful launch/handshake/runtime logger:

- One session ID names a paired client log and combined OpenGOAL/compiler log.
- Client metadata records versions, platform, executable, working directory, and support-file paths.
- `gk` and `goalc` output launched by the client is captured, ANSI-cleaned, and source-prefixed.
- Client lifecycle, source installation/hash, process launch, nREPL traffic, handshake failures, protocol versions, slot-contract validation, and manual diagnostic snapshots are logged.
- The GOAL bridge emits stable handshake messages, and wrapped background tasks preserve their Python exceptions.
- Basic tests protect paired filenames, source prefixes, and ANSI stripping.

This is a strong **startup and handshake diagnostic logger**. It is not yet a complete forensic logger for the item, location, persistence, mission, reward, overlay, authorization, and goal systems that follow.

### Gaps that Milestone 7.1 closes

- Most records are free-form text rather than a versioned, machine-readable event stream.
- Client, compiler, game, persistence, command, save, item, check, and mission activity do not yet share correlation IDs or one authoritative ordering contract.
- Raw process lines and GOAL events do not consistently share UTC timestamps or source-monotonic sequence data.
- A one-second heartbeat and raw nREPL form logging can overwhelm long sessions, while no bounded rotation/retention policy exists.
- The atomic persistence engine has extensive recovery and commit behavior but no subsystem-level diagnostic event sink.
- GOAL and Python output cannot be treated as one perfectly ordered transaction ledger when written independently.
- Unhandled thread/async-loop failures, log-writer failures, and previous unclean sessions do not yet have one explicit project-owned capture contract.
- Current tests do not cover schema stability, redaction, rotation, support-bundle contents, concurrent sources, disk/log failure, or high-volume sessions.
- Leaving the engineering logger until the old late diagnostics milestone would require retrofitting the most difficult gameplay systems after they were already built.

### Decision

Do not revert, rewrite, or broadly reopen commit `0cdc04e`. Treat its Protocol 3, native-save identity, descriptor-qualified binding, runtime-safety, and idempotent command semantics as frozen pending real acceptance. Implement Milestone 7.1 as a separate, reviewable instrumentation task, then perform Milestone 7.2 as the evidence-producing completion of Milestone 7's existing live gate. Production fixes during Milestone 7.2 are limited to reproduced failures or direct source-proven defects. Milestone 25 remains responsible only for concise player-facing presentation and recovery guidance.

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

# Milestone 7.1 — Establish Structured Diagnostic Logging and Forensic Support Bundles

## Human-readable summary

The project already produces useful paired client and OpenGOAL logs, but upcoming Archipelago gameplay can fail across many boundaries: the server packet, Python ledger, persistent sidecar, command transport, native game application, mission script, save reconstruction, or reconnect path.

A maintainer or agentic AI should be able to reconstruct that chain without attaching a debugger or asking the player to reproduce the problem repeatedly. This milestone upgrades the existing logger into an engineering-grade diagnostic subsystem before real items and checks are enabled.

For the player, normal logging remains automatic and bounded. When a problem occurs, one sanitized support bundle contains the relevant timeline, versions, state summaries, and errors without exposing passwords or native save data.

## Frozen Milestone 7 boundary

Milestone 7 is not revised by this milestone. Milestone 7.1 begins after commit `0cdc04e` is present, even though the existing interactive completion gate is still pending. Its purpose is to make that gate and later gameplay failures diagnosable. It may add passive observation adapters, event sinks, and diagnostic projections around Milestones 4–7, but it must not change persistence semantics, safe-state decisions, command/result semantics, protocol compatibility requirements, or Milestone 7's required tests.

Formal live acceptance is performed in Milestone 7.2. If diagnostic work exposes an actual defect, record it as a focused regression with a reproducer or direct source evidence and repair only that defect; do not silently redefine or broadly re-review Milestone 7.

## Technical objective

Preserve the two current human-readable logs, add a versioned Python-owned structured event stream, instrument the existing launcher/protocol/persistence paths, establish crash/noise/privacy policies, and create a sanitized support-bundle exporter that every later milestone can extend.

## Required architecture

### One diagnostic session, three support-facing artifacts

Each client run owns one session ID and creates:

```text
Jak3Client_<session>.txt       # human-readable Python/AP client log
Jak3OpenGOAL_<session>.txt     # human-readable gk/goalc/game output
Jak3Events_<session>.jsonl     # machine-readable correlated event timeline
```

The JSON Lines event stream is the authoritative diagnostic timeline. The human logs remain valuable raw context and must not be removed.

### Single-writer rule

- Python is the only writer to the structured event file and support bundle.
- Python should also be the only writer to each support-facing merged file where practical.
- GOAL emits bounded, sequence-numbered diagnostic records through a dedicated bridge/ring/outbox or another explicitly versioned channel; Python drains and records them.
- Do not rely on Python's thread lock to order writes made independently by the GOAL process.
- Keep `format #t` or an equivalent emergency game-side trace as a fallback, but do not use a second process to write the authoritative structured file.
- The first source-loaded/initialization event must be retrievable even when it occurs before the client finishes attaching.
- If `gk` or `goalc` was already running and its prior stdout cannot be captured, emit an explicit capture-gap event rather than implying the log is complete.

### Diagnostic event envelope

Define and version a JSON-serializable envelope. Required fields are:

```text
diagnostic_schema_version
event_sequence
observed_utc
source_component
source_sequence
source_monotonic_or_game_tick
severity
event_name
message
session_id
correlation_id
process_id
thread_or_task
protocol_version
game_integration_version
runtime_state_sequence
persistent_state_revision
context
details
```

Rules:

- `observed_utc` is timezone-aware UTC.
- `event_sequence` is assigned by the Python writer and is monotonic within the diagnostic session.
- `source_sequence` identifies ordering within the client, launcher, GOAL bridge, compiler/game collector, or persistence source.
- `correlation_id` is required for commands and is used where available for item indices, location sends, task hooks, overlay profiles, and goal updates.
- Optional fields use explicit null/absence rules; arbitrary Python objects and unserializable payloads are rejected safely.
- Event names are stable identifiers such as `protocol.command.completed`, not prose.
- Human-readable `message` supplements stable fields; code must not parse the message to make gameplay decisions.
- The diagnostic schema has its own version and migration policy. It is support-tool compatibility, not an AP item/location ID contract.

### Event catalogue and required current coverage

Create a documented event-name catalogue. Milestone 7.1 must cover the systems already present:

#### Session/process lifecycle

- Diagnostic session started and configuration summary.
- Prior session detected as clean or unclean.
- AP client start/stop.
- AP server connecting/authenticated/disconnected/rejected.
- OpenGOAL installation discovery and bridge hash verification.
- `gk`/`goalc` start, already-running capture gap, exit code, crash/abnormal exit.
- nREPL connect/attach/close/timeout.
- GOAL source loaded and log/event channel ready.

#### Compatibility and binding prerequisites

- Protocol/integration/table/slot/state versions and hashes.
- Slot-data contract accepted or rejected, with stable mismatch field/code.
- Native save observed, eligible/ineligible, loaded/unloaded/switched.
- Binding deferred, attempted, accepted, rejected, or read-only.
- Raw native-save identity is never logged; use a one-way diagnostic identity hash.

#### Milestone 7 save/binding and bridge-update lifecycle

At minimum, define stable events for:

- `save.identity.proposed`, `save.identity.authorized`, `save.identity.consumed`, `save.identity.published`, and `save.identity.invalidated`.
- `save.native_operation.started`, `save.native_operation.succeeded`, and `save.native_operation.failed`.
- `binding.opened`, `binding.switched`, `binding.rejected`, and `binding.closed`.
- `runtime.safety.changed`, carrying only the changed safe-state reasons.
- `bridge.reload.required`, `bridge.reload.started`, `bridge.reload.activated`, `bridge.reload.failed`, and `bridge.restart_required`.
- `protocol.command.submitted`, `protocol.command.applied`, `protocol.command.replayed`, and `protocol.command.rejected`.

Use a one-way diagnostic identity hash, command ID, game-session nonce hash, state revision, native slot, and activation generation as correlation data. Never log a raw save UUID.

#### Protocol/runtime state

- Handshake accepted/rejected.
- Runtime state transitions, not every unchanged poll.
- Safe-state changes.
- Command submitted, accepted, applied, already applied, queued, unsafe, rejected, timed out, failed, and recovered after reconnect.
- Duplicate and stale-session commands.
- Communication loss/reconnect.
- Heartbeat health is sampled or summarized; steady one-second pings are DEBUG/TRACE-only and rate-limited.

#### Persistence retrofit for completed Milestone 6

Instrument the existing persistence layer without changing its semantics:

- Writer lock acquired/refused/released.
- State path selected using only a redacted/hash identity.
- State created, loaded, bound, switched, and closed.
- Commit attempted/succeeded/failed with old/new revision and operation category.
- Backup refreshed/restored.
- Corruption detected.
- Quarantine performed with sanitized filename/reference.
- Compatibility/binding/eligibility rejection.
- Clean versus unclean shutdown state.
- Stale revision and concurrent-writer rejection.

Prefer dependency injection or a small event-sink protocol so `persistence.py` remains independently testable and does not depend on the global client logger.

### Noise, levels, rotation, and retention

- INFO records lifecycle, state transitions, durable operations, retries that affect behavior, and user-actionable failures.
- DEBUG records bounded command/protocol detail.
- TRACE or an explicit opt-in diagnostic mode may include sanitized raw nREPL forms and high-frequency polling.
- Normal mode must not log each one-second healthy heartbeat to human or structured INFO output.
- Add rate limiting and a `diagnostics.events_dropped_or_suppressed` summary when events are intentionally sampled or a game-side ring overflows.
- Use bounded size-based rotation or an equivalent bounded per-session design.
- Retention must be configurable and default to a finite number of sessions/files/bytes.
- Old logs may be compressed or removed only after the current session is safely initialized.
- A three-hour normal session and an accelerated high-volume test must stay within the documented storage bound.

### Crash and exception capture

Create one explicit project-owned policy for:

- Main-thread unhandled exceptions.
- `asyncio` loop exceptions and unawaited task failures.
- Background thread exceptions, including process-output collectors.
- GOAL/compiler/game abnormal exits.
- Failure while writing or rotating diagnostics.
- Previous session missing a clean-shutdown marker.

Use existing Archipelago exception logging where it is authoritative, but install missing hooks rather than assuming every task/thread is covered. Avoid duplicate traceback storms. A diagnostic failure falls back to stderr/client output and never changes AP state.

### Redaction and privacy

The normal logs and exported bundle must never include:

- AP server passwords or authentication tokens.
- Credential-bearing URLs.
- Raw native-save identity.
- Complete native save files.
- Game assets, ISO data, or memory dumps.
- Full persistent sidecar/journal contents by default.
- Unbounded raw server packets or arbitrary command payloads.

Use field allowlists, not only pattern replacement. The support bundle additionally sanitizes user/profile path segments and records which fields were redacted. Item/location/task numeric IDs and names are allowed because they are required for diagnosis.

### Support bundle

Implement a command such as:

```text
/diagnostics export
```

It creates a timestamped archive containing only allowlisted files/data:

- Current client log.
- Current OpenGOAL/compiler log.
- Structured event JSONL.
- Manifest with checksums and diagnostic schema version.
- Current sanitized protocol/runtime snapshot.
- Version/hash/installed-bridge summary.
- Sanitized persistence summary: state revision, open/recovery status, counts, pending counts, and clean-shutdown state, but not the full journal or native identity.
- Recent command-result summaries.
- A small README describing contents and known capture gaps.

Bundle creation must work after a partial startup failure and must report which optional artifacts were unavailable. It must not upload anything automatically.

## Required tests

### Schema and event tests

- Every event is valid UTF-8 JSON and matches the versioned schema.
- Event names are registered and unique.
- Python event sequence is monotonic.
- Source sequence and correlation IDs survive asynchronous ordering.
- Unknown optional fields are forward-safe for the bundle reader.
- Multiline text, Unicode, and ANSI control sequences are normalized safely.
- Unsupported/unserializable details produce a safe diagnostic error rather than recursion or a client crash.

### Coverage tests

- Session start and clean shutdown.
- Prior unclean session.
- Server connect/auth/reject/disconnect.
- OpenGOAL start/already-running/exit.
- nREPL timeout and protocol mismatch.
- Runtime state transition and unchanged-poll suppression.
- Duplicate/stale/unsafe/failed harmless commands.
- Persistence create/load/bind/commit/revision conflict/backup recovery/quarantine/writer-lock rejection.
- GOAL event-ring drain, duplicate drain, sequence gap, and overflow summary.
- The earliest source-loaded event is present after attach.

### Noise, failure, and retention tests

- Ten thousand synthetic heartbeats do not create ten thousand INFO events.
- Rotation/retention stays within its configured bound.
- Concurrent compiler/game/client events remain parseable and do not overwrite each other.
- Unwritable directory, permission error, partial line, simulated disk-full write, and rotation failure do not mutate AP state or terminate gameplay.
- Collector-thread and asyncio-loop exceptions are captured once with traceback/correlation.
- Logging an error from inside the logger does not recurse indefinitely.

### Redaction and bundle tests

- Passwords, auth tokens, credential URLs, raw save identity, user-profile paths, and prohibited file types are absent.
- Bundle manifest/checksums match included files.
- Missing optional artifacts are disclosed.
- Bundle can be created after startup failure and after clean shutdown.
- Bundle creation is read-only with respect to AP persistent state and native gameplay state.

## Documentation deliverables

Create or update:

```text
docs/development/diagnostic-architecture.md
docs/development/diagnostic-events.md
docs/troubleshooting.md
worlds/jak3/docs/setup_en.md
```

Document:

- File locations and retention.
- Log levels and temporary verbose mode.
- Event-envelope fields.
- Redaction policy.
- Support-bundle command and contents.
- Known capture gaps for pre-existing OpenGOAL processes.
- How later milestones add event names without breaking the schema.

## Non-goals

- No real `ReceivedItems` processing.
- No real location submission.
- No reward interception or mission mutation.
- No large in-game UI.
- No remote telemetry or automatic upload.
- No full native memory dump or full sidecar export.
- Do not change completed Milestone 6 persistence behavior merely to simplify logging.

## Completion gate

A synthetic cross-component failure involving startup, a persistence recovery/rejection, a harmless command timeout/duplicate, and a game/client reconnect can be diagnosed from the exported support bundle alone. The structured timeline identifies the component, stable event, correlation ID, state revision, command result, and capture gaps in order; the bundle passes redaction tests; a high-volume session remains bounded; and disabling or breaking the diagnostic sink cannot corrupt gameplay or persistent AP state.

## Suggested Codex prompt

```text
/plan

Implement only Milestone 7.1.

Preserve the existing paired human-readable logs, then add one Python-owned
versioned JSONL event timeline, a stable event registry, GOAL event draining,
persistence instrumentation, bounded rotation/retention, exception/crash
capture, field-allowlist redaction, and `/diagnostics export` support bundles.

Do not add ReceivedItems, locations, rewards, or mission behavior. Make logging
failure non-fatal and prove that a synthetic startup/persistence/command failure
can be diagnosed from the sanitized bundle alone.
```

---

# Milestone 7.2 — Perform Live Runtime Acceptance, Establish Performance Baselines, and Freeze Protocol 3

## Human-readable summary

Milestone 7 now has extensive source, compiler, fake-protocol, persistence, and harmless transport coverage. The remaining uncertainty is not another hypothetical branch: it is whether native save identity, binding, safety, and restart behavior work correctly during real player workflows.

This milestone stops broad speculative review and exercises those workflows in an actual OpenGOAL game using Milestone 7.1 diagnostics. It also measures startup, compile, heartbeat, logging, and runtime cost so future milestones do not accidentally turn the control bridge into an unbounded performance or maintenance burden.

For the player, this is the point where the project proves that the correct save remains attached to the correct Archipelago slot through ordinary saving, switching, restarting, disconnecting, and failure. No real items or locations are enabled yet.

## Technical objective

Demonstrate Milestone 7's existing completion gate on a real runtime, establish reproducible performance baselines, define the supported bridge-update lifecycle, and freeze Protocol 3/control semantics before Milestone 8 sends gameplay data.

## Validation-first change policy

- Do not perform another unbounded review-agent pass over the complete Milestone 7 diff.
- Do not add defensive branches for merely imaginable transitions.
- Production code may change only for:
  - A reproduced live failure.
  - A deterministic failing regression test derived from the live matrix.
  - A direct contradiction with audited native source that can corrupt state, bind the wrong save, or crash a supported workflow.
- Every fix must be narrow, must add a focused regression, and must rerun only the affected matrix rows plus the existing required suite.
- No real item, location, reward, mission-board, overlay, or goal behavior is added.

## Required real native-save matrix

Run and record, at minimum:

1. Authenticate, start a fresh New Game, save, and verify one stable UUID/slot/eligibility descriptor.
2. Load the same save repeatedly and verify the same descriptor and sidecar binding.
3. Cleanly restart the client while the game remains open.
4. Terminate the client uncleanly while the game remains open, then reconnect.
5. Restart the game while the client remains open; verify a new game-session nonce and safe reconciliation.
6. Restart both processes in both orders.
7. Switch save A → save B → save A and verify binding follows the exact descriptor without a false-safe window.
8. Copy a tagged native save to another native slot and verify copied-slot rejection is read-only and recoverable.
9. Attempt to use a progressed vanilla save and verify it is rejected as ineligible without altering it.
10. Enter Continue Without Save and verify no prior descriptor or binding remains active.
11. From the title menu, create another New Game after loading an AP save; verify a fresh UUID is used and the previous sidecar is not reopened.
12. Overwrite the same native slot with a new game and verify the new save cannot inherit the old AP identity.
13. Exercise a controlled save/load failure where practical; verify identity publication and binding fail closed while native behavior remains recoverable.
14. Send the harmless target-state command, repeat it, reconnect, and verify `APPLIED`/`ALREADY_APPLIED` or stored receipt behavior without a second effect.
15. Verify title-menu queries remain available while mutating commands remain unsafe/unbound.

Each row must include the diagnostic session/support bundle, expected result, observed result, pass/fail, and any known capture gap.

## Supported update and reload policy

Adopt this first-release policy unless the matrix proves a different policy is both necessary and reliable:

- Installing a changed APWorld/OpenGOAL bridge while Jak 3 is running requires a clean game restart before normal play.
- Bridge-only live reload remains a development/recovery aid, not a player-facing guarantee.
- Do not expand support for live reload during native memory-card I/O in later gameplay milestones.
- Existing reload protections in `0cdc04e` remain in place; they are not removed in this milestone unless a reproduced defect requires it.

Document the policy in setup, update, recovery, and release instructions.

## Performance and complexity baseline

Measure and record on the test system:

- Cold client startup to attached compiler.
- Full `(mi)` duration.
- Bridge-only `(ml)` duration.
- Warm reconnect with an unchanged compatible bridge.
- CPU utilization and game frame-time impact of the one-second heartbeat during at least 30 minutes of gameplay.
- Snapshot write rate and bytes per hour.
- Human-log and structured-log bytes per hour in normal mode.
- Memory use of the bridge before and after a long idle/gameplay session.
- Time to export a sanitized support bundle.

The currently observed roughly 28-second dependency rebuild is a baseline to explain, not automatic evidence that Milestone 7 code caused the cost. Compare cold, warm, unchanged-source, and changed-source paths before optimizing.

If measurement shows material overhead or the update policy cannot be simplified safely, record a proposed **Milestone 7.3**. Do not create or implement Milestone 7.3 merely because the code is large.

## Architecture freeze and modularity rules

After the matrix passes:

- Freeze Protocol 3 field meanings, command/result/error codes, native tag 900, save-authorization format, and descriptor-qualified binding semantics for the default-only beta.
- A later protocol change requires an explicit version bump and compatibility/migration decision.
- The eight-entry GOAL receipt ring remains session-level command deduplication, not the durable gameplay journal.
- Python's AP ledger remains authoritative for permanent items.
- Future GOAL systems are added in separate modules, for example:
  - `archipelago-items.gc`
  - `archipelago-locations.gc`
  - `archipelago-overlays.gc`
  - `archipelago-missions.gc`
- Do not continue placing all future gameplay behavior into the Milestone 7 control bridge.

## Required documentation updates

- Mark Milestone 7 complete only after every mandatory matrix row passes or has a documented, approved safe limitation.
- Record measured performance rather than estimates.
- Record the supported update/restart policy.
- Update R-019 and any bridge-reload risk with real evidence.
- Store a concise acceptance report under `docs/development/`.

## Non-goals

- No `ReceivedItems` processing.
- No `LocationChecks` submission.
- No reward interception.
- No mission mutation.
- No speculative cleanup/refactor of working Milestone 7 code.
- No promise that arbitrary hot reload during memory-card I/O is a supported player workflow.

## Completion gate

Milestone 7's existing live gate is demonstrated with real runtime evidence: no tested workflow binds the wrong save, transfers acknowledgement across descriptors, publishes an uncommitted identity, reports mutation-safe without a compatible bound save, or loses recoverable state across the required restart matrix. Protocol 3 is then frozen, measured overhead and the update/restart policy are documented, and Milestone 8 may begin.

## Suggested Codex prompt

```text
/plan

Implement only Milestone 7.2.

Do not broadly revise Milestone 7 or add gameplay. Use the Milestone 7.1 event
stream and support bundle to execute the real native save/load/copy/new-game,
clean/unclean restart, save-switch, and harmless-command matrix. Measure cold
compile, bridge load, warm reconnect, heartbeat, log, and runtime overhead.

Change production code only for a reproduced failure or direct source-proven
state-corruption defect, with a focused regression. Define and document the
first-release update/restart policy, then freeze Protocol 3 before Milestone 8.
```

---

# Milestone 8 — Implement Indexed ReceivedItems and the AP Item Ledger

## Human-readable summary

Milestone 7.2 has now proven and frozen the save/binding and idempotent-command foundation. When the Archipelago server sends an item, the mod must record it in order, survive a crash between receipt and application, and rebuild the native game state after a restart.

This milestone enables the incoming half of Archipelago for a deliberately small permanent-item slice. The persistent Python AP ledger, not native reward history and not the eight-entry GOAL receipt ring, becomes authoritative for those items. It reuses Protocol 3 rather than reopening Milestone 7.

## Technical objective

After Milestone 7.2 passes, implement indexed `ReceivedItems` processing, a crash-safe Python ledger, and safe native reconciliation for a small test set. Keep the Milestone 7 runtime/save-binding core stable and add native item behavior in a separate OpenGOAL module.

## Milestone 7 foundation constraints

- Milestone 7.2 is a hard prerequisite.
- Use idempotent target-state/reconciliation commands for permanent unlocks.
- Python persistence and indexed AP receipts are authoritative; the GOAL receipt ring is only current-game-session command deduplication and reconnect discovery.
- Do not use the eight-entry ring as the crash-safe journal for currency or other consumables. Additive exactly-once application remains deferred to Milestone 14.
- Add native item mapping/application in `archipelago-items.gc` or an equivalent separate module rather than continually enlarging the core `archipelago.gc`.

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

## Required diagnostic events

Use the Milestone 7.1 event API and correlate every path by received-item index and game command ID. At minimum emit:

```text
ap.received_items.packet_observed
item.receipt.accepted
item.receipt.duplicate
item.receipt.index_gap
item.replay.started
item.replay.completed
item.application.queued
item.application.command_submitted
item.application.completed
item.application.already_applied
item.application.failed
item.reconciliation.started
item.reconciliation.completed
```

Record item ID/name, source player, source location ID, packet start index, expected index, persistent state revision, command correlation ID, safe-state reason, and final outcome. Do not log the full server packet or password-bearing connection data.

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

Archipelago location packets are safe to resend; there is not a simple one-packet acknowledgment to trust. This milestone therefore keeps the local durable bit as authoritative and reconciles it with the server's checked-location state after connection and room updates. Milestone 7.2 is a hard prerequisite, and its Protocol 3/save-binding semantics remain frozen.

## Technical objective

Implement durable game-to-server location reporting for one debug check and one controlled native check. Add native check observation/outbox behavior in `archipelago-locations.gc` or an equivalent separate module rather than adding it to the Milestone 7 control core.

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

## Required diagnostic events

Correlate the native observation, durable commit, outbox send, and server reconciliation using the location ID and outbox batch ID. At minimum emit:

```text
location.observed
location.duplicate_ignored
location.committed_local
location.outbox.enqueued
location.outbox.batch_sent
location.server_confirmed
location.reconciliation.started
location.reconciliation.completed
location.reconciliation.rejected
```

The timeline must distinguish native task completion from the AP durable bit and must show that server confirmation compacts the outbox without clearing local completion.

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

It also moves one native reward-interception proof earlier so the project does not spend months expanding data before validating its most important substitution mechanism. The Milestone 7.2 control protocol remains frozen; this slice must use it rather than growing a second transport path.

## Technical objective

Create a small connected gameplay slice with one real permanent native reward interception, then repeat the relevant Milestone 7.2 save-switch/restart rows with actual item and location hooks active.

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

## Diagnostic acceptance for the vertical slice

The slice must emit one correlated timeline spanning:

```text
native reward/task observation
→ AP location durable commit
→ outbox send/reconciliation
→ ReceivedItems index receipt
→ persistent item journal commit
→ game command/result
→ native inventory reconciliation
→ clean restart/reconnect verification
```

The location ID, received-item index, command ID, persistence revision, task/reward node, and AP/native result must be recoverable from the structured event stream. The exported support bundle must be sufficient to explain a deliberately injected failure at each boundary.

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

## Diagnostic evidence requirements

Each runtime spike must have an experiment/correlation ID and must retain its structured event timeline or sanitized support bundle. A PASS or fallback decision cannot rely only on prose recollection; the deliverable must point to the source/runtime procedure and the diagnostic evidence that demonstrates the observed state transitions, native flags, item/relic counts, and save/reload result.

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

## Required diagnostic events

Every permanent item implementation must extend the shared event catalogue with target-state reconciliation events. Record item ID/name, AP count, native target state, native observed state, command ID, state revision, safe-state decision, and outcome. Do not dump arbitrary native memory. Required paths include first application, already-correct state, repeated receipt beyond native cap, queued application, save reconstruction, and reconciliation repair.

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

## Required diagnostic events

Exactly-once consumables require a complete receipt/application timeline. Correlate received-item index, application receipt ID, command ID, pre/post capped resource summary, persistent revision, game-session nonce, and final result. Emit distinct events for reserved, applied, observed-applied-after-restart, duplicate-suppressed, unsafe/queued, capped/no-op, and failed/ambiguous. Never log a raw memory dump or make the diagnostic event the durability boundary.

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

## Required diagnostic events

For each overlay emit profile selected, activation requested/applied, lesson-stage transition, permanent-item arrival while active, cleanup requested/completed, reconciliation completed, and cleanup failure/recovery. Include task/node, overlay instance ID, exact temporary capabilities, pre-existing native state summary, and final AP-ledger/native-state comparison.

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

## Required diagnostic events

For every intercepted node record native reward hook observed, AP mode decision, recursion-guard state, location ID, permanent native grants suppressed, unrelated native effects allowed, task closure observed, local AP bit/outbox result, replay/duplicate decision, and AP-mode-off native path. Correlate by task ID, reward-node ID, location ID, and reward interception instance ID.

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

## Required diagnostic events

Each authorization/profile operation must record authorization ownership, rule eligibility, mission-board entry considered, native snapshot/profile planned, fields changed, fields already satisfied, activation result, rollback/cleanup, save/load reconstruction, and any divergence from the expected native snapshot. Correlate by authorization item, mission/task, profile version, and operation ID.

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

### 18A — Spargus and early Wasteland

- Training/race vehicles.
- Leaper sections.
- Turrets.
- Arena and gun-training loadouts.

### 18B — Temple, Volcano, and Mines

- Flut-Flut/glider.
- Daxter sections.
- Mine equipment.
- Bomb train.
- Remaining lesson powers used in these missions.

### 18C — Haven and Sewers

- Haven vehicles.
- Missile and Blast Bot sequences.
- Gun courses.
- Board Trail.
- Mission-only shooters.

### 18D — War Factory and late game

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

## Required diagnostic events

Every bootstrap profile must emit profile lifecycle events using task/profile/overlay instance IDs. Record supplied actors/equipment, stage boundaries, mission result, death/abort/retry, cleanup, permanent item receipt during the profile, and final AP-ledger/native-state reconciliation.

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

## Required diagnostic events

Shadow-state events must state the profile/task, exact allowlisted native flags/props requested, which were pre-existing, which were synthesized, cleanup/preservation result, and AP relic count before/after. A nonzero relic-count delta caused by shadow state is an ERROR event and blocks completion.

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

## Required diagnostic events

For each story mission record close-task/native completion observed, durable AP bit decision, duplicate/replay decision, outbox enqueue/send/confirmation, current task/node, and any mismatch between native completion and AP completion. Use the task ID and location ID as correlation fields; do not use actor addresses as identifiers.

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

## Required diagnostic events

For each selected challenge record availability/cost bypass decision, start, native completion, durable AP bit, replay/duplicate, fixed-equipment profile, outbox result, and placement-classification metadata. Correlate by source task ID and location ID.

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

## Required diagnostic events

Record each local native orb delta, AP-delivered spendable-orb delta, monotonic local-earned total, threshold(s) crossed, durable threshold bits, duplicate reconstruction suppression, spend event, and outbox result. Every event must explicitly identify the source class (`local_native` versus `ap_delivered`) so an AP Orb Pack can never be mistaken for local threshold progress.

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

## Required diagnostic events

Record unique AP relic ownership changes, current five-of-seven count, finale gate transition, task-71 start/completion, task-72/city-win observation, durable goal commit, `StatusUpdate` send/resend/confirmation state, and duplicate suppression. Shadow/native presentation props must be identified separately and must never appear as AP relic ownership.

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

Repeat the complete Milestone 7.2 save/binding/restart matrix against the full gameplay integration; do not assume its earlier pass covers later native hooks. In addition:

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

## Diagnostic and soak verification

- Every injected or naturally discovered runtime failure produces a support bundle before the issue is considered understood.
- The structured event sequence is parseable end to end; any source-sequence gap or intentionally dropped/sampled event is represented explicitly.
- A three-hour connected runtime session, or an equivalent accelerated test plus one real extended session, respects documented file-size/retention bounds.
- Ten thousand heartbeat cycles do not bury state changes in INFO-level noise.
- Diagnostic CPU/I/O overhead is measured and shown not to materially alter game behavior or protocol timing.
- Cold compile, warm reconnect, bridge-only load, heartbeat, and log-growth measurements are compared with the Milestone 7.2 baseline; material regressions require explanation or remediation.
- Client crash, game crash, compiler exit, log-directory failure, and unclean restart retain enough evidence to identify the failing component.
- Support-bundle redaction is revalidated against realistic slot names, usernames, paths, server addresses, and passwords.
- A maintainer who did not run the test can reconstruct the item/check/mission timeline from the bundle without the native save or full sidecar.

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

# Milestone 25 — Polish Player-Facing Status, Recovery Guidance, and Diagnostic Export UX

## Human-readable summary

Engineering-grade diagnostics and the support-bundle exporter have existed since Milestone 7.1 and were used for the Milestone 7.2 runtime acceptance matrix. A normal player still should not need to read JSON events or source code to understand a wrong save, queued item, disconnected game, incompatible version, pending check, or failed recovery.

This milestone turns the already authoritative protocol, persistence, and diagnostic state into concise status and recovery guidance. It does not create another logger, another state model, or another support-bundle format.

## Technical objective

Provide small, reliable player-facing status commands and, where low-risk, a compact OpenGOAL status view that summarize Milestone 7.1's data and guide safe recovery.

## Required information

- AP server connected/disconnected/authenticated.
- OpenGOAL attached/detached and process status.
- Compatible/incompatible protocol and game integration.
- Table/slot-data/state/diagnostic schema versions and hashes.
- Seed, team, slot, and redacted native save identity.
- Bound/unbound/wrong-save/read-only status.
- Current task/level and safe-state summary.
- Last received item and item index.
- Pending item/application count.
- Pending outgoing check count and last server-confirmed check.
- Active mission overlay and active shadow profile.
- Item/check/mission operation queued until safe.
- Goal state and pending/resend status.
- Last actionable error code/message and correlation ID.
- Current diagnostic session ID, files, retention status, and known capture gaps.

## Recommended commands

- `/status`
- `/pending`
- `/binding`
- `/version`
- `/resync`
- `/diagnostics summary`
- `/diagnostics export`
- `/diagnostics verbose on|off` for a temporary, clearly disclosed session-scoped mode

Recovery commands must not bypass seed binding, compatibility checks, durable journals, or safe-state rules. Diagnostic commands are read-only except for creating an archive or changing the session-local verbosity setting.

## Support-bundle UX requirements

Reuse the Milestone 7.1 exporter and schema. Add only:

- Clear success/failure output and archive path.
- A short explanation of what is included and redacted.
- A warning when pre-existing OpenGOAL processes created a capture gap.
- A correlation/session ID the player can include in a bug report.
- Safe guidance when the log directory is unwritable or the bundle is incomplete.

Do not fork the exporter or add a second bundle format.

## Required tests

- Every common error maps to clear, actionable text.
- Wrong seed/save.
- Table or diagnostic-schema mismatch.
- Item queued/failed/already applied.
- Outbox pending/server confirmed.
- Server reconnect.
- Game reconnect/restart.
- Corrupt sidecar and backup recovery.
- Active overlay/shadow profile.
- Goal completed/status pending.
- Support bundle success, partial success, redaction, and unwritable destination.
- Verbose mode expires at shutdown and does not expose prohibited data.
- UI/status/export code cannot mutate gameplay or persistent progress accidentally.
- Human status values match the authoritative structured event/protocol/persistence state.

## Non-goals

- No new diagnostic storage architecture.
- No large custom UI framework.
- No experimental gameplay options.
- No silent error suppression.
- No “force” recovery command that bypasses an invariant.

## Completion gate

A tester can identify and safely respond to common connection, binding, delivery, persistence, mission-state, and version problems using the status commands. The same session's Milestone 7.1 support bundle can be exported with one command, and every displayed status is traceable to the authoritative protocol/persistence/diagnostic state.

## Suggested Codex prompt

```text
/plan

Implement only Milestone 25.

Polish the existing Milestone 7.1 diagnostic infrastructure into concise status,
pending, binding, version, resync-guidance, and diagnostic-export commands.
Reuse the authoritative event stream, protocol snapshot, persistence state, and
support-bundle exporter. Do not create a second logger/state model or add any
force command that bypasses invariants.
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

## Additional diagnostic release requirements

The compatibility manifest also pins:

- Diagnostic event schema version.
- Support-bundle manifest version.
- Default log levels, rotation limits, and retention policy.
- Known process-output capture gaps.
- Supported bridge/APWorld update policy, including whether a clean game restart is mandatory after changed source.
- Recorded cold compile, bridge-only load, and warm reconnect baseline ranges.

The packaged APWorld must include the event catalogue/bundle exporter and must verify their files/checksums during package validation.

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
- Update the mod, including the required clean-restart boundary after changed bridge/APWorld source.
- Handle an incompatible state.
- Locate logs, temporarily enable verbose diagnostics, export a sanitized support bundle, and explain its retention/redaction policy.
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
- Upgrade/repair, including a changed-source update followed by the documented restart path.
- Uninstall.
- No writes to source-reference trees.
- Documentation paths and screenshots match the release.
- A startup failure and one injected runtime failure both produce a redacted, parseable support bundle in the clean environment.
- Log rotation/retention behaves as documented during an extended or accelerated session.

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

---
