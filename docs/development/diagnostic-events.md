# Diagnostic event registry

Diagnostic schema version 1 uses the immutable names below. Unknown names are
rejected; optional future envelope fields remain forward-safe. GOAL numeric
codes, where present, are also unique and stable. Context and detail values are
bounded and filtered by the registry allowlists in `diagnostics.py`. The
`runtime_state` and `safety_projection` objects have explicit nested-key
schemas; other nested event objects and recursive mappings are rejected both
when emitted and when an existing segment is validated for export.

## Diagnostics lifecycle, capture, and export

- `diagnostics.session.started`
- `diagnostics.session.stopped`
- `diagnostics.prior_session.clean`
- `diagnostics.prior_session.unclean`
- `diagnostics.capture_gap`
- `diagnostics.events_dropped_or_suppressed`
- `diagnostics.event.rejected`
- `diagnostics.writer.failed`
- `diagnostics.rotation.completed`
- `diagnostics.retention.completed`
- `diagnostics.exception.main`
- `diagnostics.exception.asyncio`
- `diagnostics.exception.thread`
- `diagnostics.bundle.export.started`
- `diagnostics.bundle.export.completed`
- `diagnostics.bundle.export.partial`
- `diagnostics.bundle.export.failed`
- `diagnostics.goal.drain.completed`
- `diagnostics.goal.duplicate`
- `diagnostics.goal.gap`
- `diagnostics.goal.overflow`

## Client, server, process, nREPL, and bridge lifecycle

- `client.started`
- `client.stopping`
- `client.stopped`
- `server.connecting`
- `server.authenticated`
- `server.disconnected`
- `server.rejected`
- `bridge.client.disconnected` (GOAL 420)
- `opengoal.install.discovered`
- `bridge.install.verified`
- `bridge.install.repaired`
- `bridge.install.failed`
- `process.started`
- `process.already_running`
- `process.capture_gap`
- `process.exited`
- `process.crashed`
- `nrepl.connecting`
- `nrepl.attached`
- `nrepl.closed`
- `nrepl.timeout`
- `nrepl.failed`
- `bridge.source.loaded` (GOAL 100)
- `bridge.event_channel.ready` (GOAL 101)
- `bridge.reload.required`
- `bridge.reload.started`
- `bridge.reload.activated`
- `bridge.reload.failed`
- `bridge.restart_required`

## Compatibility, save identity, binding, and runtime

- `compatibility.contract.reported`
- `slot.contract.accepted`
- `slot.contract.rejected`
- `protocol.handshake.accepted` (GOAL 400)
- `protocol.handshake.rejected` (GOAL 401)
- `save.identity.proposed` (GOAL 200)
- `save.identity.authorized`
- `save.identity.consumed`
- `save.identity.published` (GOAL 202)
- `save.identity.invalidated` (GOAL 203)
- `save.native_operation.started` (GOAL 210)
- `save.native_operation.succeeded` (GOAL 211)
- `save.native_operation.failed` (GOAL 212)
- `save.native.observed`
- `save.native.loaded`
- `save.native.unloaded`
- `save.native.switched`
- `save.native.eligible`
- `save.native.ineligible`
- `binding.deferred`
- `binding.opened`
- `binding.switched`
- `binding.rejected`
- `binding.closed`
- `runtime.state.changed` (GOAL 300)
- `runtime.safety.changed` (GOAL 301)
- `runtime.communication.lost`
- `runtime.communication.reconnected`

## Protocol 3 receipt-bearing commands

- `protocol.command.submitted`
- `protocol.command.accepted`
- `protocol.command.applied` (GOAL 411)
- `protocol.command.replayed` (GOAL 412)
- `protocol.command.queued`
- `protocol.command.unsafe` (GOAL 413)
- `protocol.command.rejected` (GOAL 414)
- `protocol.command.timed_out`
- `protocol.command.failed` (GOAL 415)
- `protocol.command.recovered` (Python reconciles a prior timeout with a later
  receipt from the same game-session nonce)

## Milestone 8 received items and permanent reconciliation

- `ap.received_items.packet_observed`
- `item.receipt.accepted`
- `item.receipt.duplicate`
- `item.receipt.index_gap`
- `item.receipt.rejected`
- `item.replay.started`
- `item.replay.completed`
- `item.application.queued`
- `item.application.command_submitted`
- `item.application.completed`
- `item.application.already_applied`
- `item.application.failed`
- `item.reconciliation.started`
- `item.reconciliation.completed`
- `item.recovery.started`
- `item.recovery.completed`
- `item.native_target.applied` (GOAL 500)
- `item.native_target.already_correct` (GOAL 501)
- `item.native_target.failed` (GOAL 502)

## Milestone 10 vertical slice

- `location.observed` (GOAL 600)
- `location.duplicate_ignored`
- `location.committed_local`
- `location.outbox.enqueued`
- `location.outbox.batch_sent`
- `location.outbox.send_failed`
- `location.server_confirmed`
- `location.reconciliation.started`
- `location.reconciliation.completed`
- `location.reconciliation.rejected`
- `reward.native_preserved` (GOAL 700)
- `reward.permanent_suppressed` (GOAL 701)
- `reward.shape_mismatch` (GOAL 702)
- `reward.item_application_guarded` (GOAL 703)
- `goal.completed`
- `goal.status.queued`
- `goal.status.sent`
- `goal.status.resent`
- `goal.status.failed`

Location events additionally allow reward-node identity. Batch IDs hash the
persistent state-instance ID together with the committed revision; raw
save/state identity is never logged. GOAL code 600 uses location correlation
kind 3, task ID in `arg0`, the bounded native task/reward source code in `arg1`,
and native node ID in `arg2`. Reward events record the bounded task/node,
AP/native decision, guard state, result, and correlated location or command.
Temporary-goal events record durable revision and authenticated connection
generation so a support bundle distinguishes the first send from a reconnect
resend.

## Persistence and recovery

- `persistence.writer_lock.acquired`
- `persistence.writer_lock.refused`
- `persistence.writer_lock.released`
- `persistence.path.selected`
- `persistence.state.created`
- `persistence.state.loaded`
- `persistence.state.bound`
- `persistence.state.switched`
- `persistence.state.closed`
- `persistence.commit.attempted`
- `persistence.commit.succeeded`
- `persistence.commit.failed`
- `persistence.backup.refreshed`
- `persistence.backup.restored`
- `persistence.corruption.detected`
- `persistence.quarantine.performed`
- `persistence.compatibility.rejected`
- `persistence.binding.rejected`
- `persistence.eligibility.rejected`
- `persistence.shutdown.clean`
- `persistence.shutdown.unclean`
- `persistence.revision.stale`
- `persistence.concurrent_writer.rejected`

`server.disconnected` describes the actual Archipelago network connection.
`bridge.client.disconnected` is the distinct Python-to-GOAL Protocol 3 shutdown.
The Python registry is authoritative for default severity, numeric-code mapping,
and field allowlists.
