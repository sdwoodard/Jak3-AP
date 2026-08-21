"""Restricted, development-only recorder for Milestone 11 feasibility spikes.

The recorder never accepts a free-form GOAL expression.  Live mutations are
limited to the presets below and require the run's disposable-save acknowledgement
plus a second acknowledgement at the mutation boundary.
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
import hashlib
import importlib
import json
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
from types import ModuleType
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = REPOSITORY_ROOT.parent
DEFAULT_JAK_PROJECT = WORKSPACE_ROOT / "jak-project"
DEFAULT_ARCHIPELAGO = WORKSPACE_ROOT / "Archipelago"
DEFAULT_DECOMPILE = WORKSPACE_ROOT / "openGOAL-decompile"
REFERENCE_ROOTS = (DEFAULT_JAK_PROJECT, DEFAULT_ARCHIPELAGO, DEFAULT_DECOMPILE)
EXPECTED_REVISIONS = {
    "jak-project": "425f143fccada9e38b35633bd298b5b64c6ca6e8",
    "Archipelago": "feab54daec712ffb333b8c73f38eb69e1ed9c508",
}
PINNED_OPENGOAL_VERSION = "0.3.5"
STATE_SCHEMA_VERSION = 1
FINALIZED_PENDING_BUNDLE = "finalized_pending_bundle"
BUNDLE_INCOMPLETE = "bundle_incomplete"
EXPERIMENT_RE = re.compile(r"^m11-[a-z0-9-]+-[0-9a-f]{8}$")
TOKEN_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")

OBSERVATION_FIELDS = frozenset(
    {
        "ap_checked_mask",
        "ap_inventory_mask",
        "ap_ledger_revision",
        "ap_orb_pack_count",
        "ap_relic_count",
        "local_orb_earned_count",
        "native_act",
        "native_actor_mask",
        "native_course_access",
        "native_course_purchase",
        "native_features",
        "native_gems",
        "native_hero_mode",
        "native_jetboard_mask",
        "side_previous_cost",
        "side_displayed_cost",
        "side_activation_flag",
        "side_event_resolved",
        "side_parent_command_suppressed",
        "native_items",
        "native_loaded_level_mask",
        "native_mission_mask",
        "native_non_ap_feature_mask",
        "native_passage_mask",
        "native_permanent_target_mask",
        "native_portal_open",
        "native_portal_present",
        "native_postgame_complete",
        "native_purchase_secrets",
        "native_reward_mask",
        "native_secrets",
        "native_skill",
        "native_skill_high_watermark",
        "native_skill_total",
        "native_task_mask",
        "native_task30_item_mask",
        "native_task30_node_closed",
        "side_marker_available",
        "side_parent_shadow_closed",
        "side_intro_node_closed",
        "side_intro_node_open",
        "side_resolution_node_closed",
        "native_viewer_scene_available",
        "native_viewer_scene_active",
        "native_viewer_item_mask",
        "orb_challenge_reward_count",
        "orb_container_count",
        "orb_mission_reward_count",
        "orb_standalone_count",
    }
)

# Every runtime PASS needs every named checkpoint and assertion.  Qualitative
# observations (geometry, actors, controls) remain explicit operator assertions;
# masks and counters are independently captured in the same checkpoint.
SPIKES: Mapping[str, Mapping[str, tuple[str, ...]]] = {
    "haven_task_35": {
        "before_entry": (
            "tasks_14_34_incomplete",
            "task_35_incomplete",
            "no_ap_or_reward_leak",
        ),
        "mission_start": ("geometry_playable", "required_actors_present"),
        "sewer_entry": ("geometry_playable", "required_actors_present"),
        "hub_return": ("normal_return_flow", "no_ap_or_reward_leak"),
        "after_save_load": (
            "tasks_14_34_incomplete",
            "task_35_incomplete",
            "state_persisted",
        ),
    },
    "jetboard_launch": {
        "00": ("base_absent", "launch_absent", "charged_launch_absent"),
        "base_only": ("base_present", "launch_absent", "charged_launch_absent"),
        "base_launch": ("base_present", "launch_present", "charged_launch_works"),
        "launch_only": ("base_absent", "launch_present", "bits_independent"),
        "task30_base_only": ("charged_jump_unavailable",),
        "task30_base_launch": ("charged_jump_available",),
        "after_save_load": ("launch_reconstructed", "base_ownership_unchanged"),
        "after_restart": ("launch_reconstructed", "base_ownership_unchanged"),
    },
    "task_30_shadow": {
        "none": ("portal_observed", "mission_entry_observed", "ap_relic_unchanged"),
        "seal_only": (
            "portal_observed",
            "mission_entry_observed",
            "ap_relic_unchanged",
        ),
        "amulets_only": (
            "portal_observed",
            "mission_entry_observed",
            "ap_relic_unchanged",
        ),
        "all_four": ("portal_observed", "mission_entry_observed", "ap_relic_unchanged"),
    },
    "task_63_viewer": {
        "artifacts_clear": (
            "telescope_actor_observed",
            "time_map_actor_observed",
            "ap_relic_unchanged",
        ),
        "artifacts_set": (
            "telescope_actor_observed",
            "time_map_actor_observed",
            "ap_relic_unchanged",
        ),
    },
    "native_reconstruction": {
        "before_save": ("targets_recorded",),
        "after_native_reload": ("direct_fields_recorded", "reward_replay_recorded"),
        "after_game_restart": ("restart_reconstruction_recorded",),
        "after_ap_reconcile": ("three_item_clear_preserve_recorded", "leak_assessed"),
        "after_item_replay": ("item_replay_recorded", "leak_assessed"),
    },
    "orb_600": {
        "postgame_before": ("normal_non_hero_save", "ap_pack_baseline_recorded"),
        "at_600": (
            "locally_earned_600",
            "ap_pack_contribution_zero",
            "source_families_observed",
        ),
        "after_save_load": ("600_persisted", "ap_pack_contribution_zero"),
        "after_restart": ("600_persisted", "ap_pack_contribution_zero"),
    },
    "side_challenges": {
        "zero_cost_before": ("zero_skull_gems", "selected_cost_zero"),
        "zero_cost_after": (
            "currency_delta_zero",
            "kiosk_activation_durable",
            "challenge_entered",
        ),
        "zero_cost_reload": ("kiosk_activation_persisted",),
        "courses_hidden": ("both_courses_hidden", "purchase_bit_clear"),
        "courses_shadow_open": (
            "both_courses_visible",
            "purchase_bit_clear",
            "no_purchase_check",
        ),
        "courses_shadow_reload": (
            "course_access_persisted",
            "purchase_bit_clear",
            "no_purchase_check",
        ),
        "courses_cleared": ("both_courses_hidden", "purchase_bit_clear"),
    },
}

DECISIONS = frozenset({"pass", "safe_fallback", "blocked"})
SAFE_FALLBACK_SPIKES = frozenset({"haven_task_35", "jetboard_launch", "orb_600"})
REVIEW_REASONS: Mapping[str, tuple[str, str]] = {
    "predefined_haven_fallback": ("haven_task_35", "safe_fallback"),
    "jetboard_semantics_proven": ("jetboard_launch", "pass"),
    "missing_persistence_checkpoint": ("jetboard_launch", "blocked"),
    "invalid_task30_numeric_control": ("task_30_shadow", "blocked"),
    "invalid_task63_numeric_control": ("task_63_viewer", "blocked"),
    "release_blocking_reconstruction_leak": ("native_reconstruction", "blocked"),
    "incomplete_side_challenge_matrix": ("side_challenges", "blocked"),
    "missing_qualifying_orb_save": ("orb_600", "blocked"),
}

JETBOARD_SEMANTIC_CHECKPOINTS = (
    "00",
    "base_only",
    "base_launch",
    "launch_only",
    "task30_base_only",
    "task30_base_launch",
)
JETBOARD_PERSISTENCE_CHECKPOINTS = ("after_save_load", "after_restart")

NATIVE_RECONSTRUCTION_OBSERVATION_FIELDS = frozenset(
    {
        "native_items",
        "native_features",
        "native_non_ap_feature_mask",
        "native_permanent_target_mask",
        "native_reward_mask",
        "native_task_mask",
        "native_mission_mask",
        "ap_inventory_mask",
        "ap_ledger_revision",
        "ap_checked_mask",
    }
)
AP_STATE_OBSERVATION_FIELDS = frozenset(
    {
        "ap_inventory_mask",
        "ap_ledger_revision",
        "ap_checked_mask",
        "ap_relic_count",
    }
)
AP_STATE_LIVE_SPIKES = frozenset(
    {
        "haven_task_35",
        "native_reconstruction",
        "orb_600",
        "side_challenges",
        "task_30_shadow",
        "task_63_viewer",
    }
)
AP_STATE_ITEM_BITS = {
    743_000_108: 1 << 0,  # Jetboard
    743_010_014: 1 << 1,  # Blaster
    743_000_116: 1 << 2,  # Progressive Armor stage 1
}
AP_ORB_PACK_IDS = (
    743_012_000,  # Precursor Orb Pack (5)
    743_012_001,  # Precursor Orb Pack (10)
    743_012_002,  # Precursor Orb Pack (25)
)
AP_RELIC_IDS = tuple(range(743_010_016, 743_010_023))
AP_STATE_CHECK_IDS = (
    743_001_010,
    743_001_011,
    743_001_012,
    743_001_013,
    743_001_014,
    743_001_015,
    743_001_016,
    743_020_036,
)

# Numeric controls are machine-checked independently of operator assertions.
# A checkpoint cannot become PASS merely because an operator supplied a
# contradictory ``--assert name=pass`` value.
SHADOW_NATIVE_ISOLATION_OBSERVATIONS = {
    "native_task_mask": 0,
    "native_mission_mask": 0,
    "native_reward_mask": 0,
}
EXPECTED_OBSERVATIONS: Mapping[tuple[str, str], Mapping[str, int | float]] = {
    ("haven_task_35", "before_entry"): {"native_task_mask": 0},
    ("haven_task_35", "mission_start"): {"native_actor_mask": 3},
    ("haven_task_35", "sewer_entry"): {"native_actor_mask": 3},
    ("haven_task_35", "after_save_load"): {"native_task_mask": 0},
    ("jetboard_launch", "00"): {"native_jetboard_mask": 0},
    ("jetboard_launch", "base_only"): {"native_jetboard_mask": 1},
    ("jetboard_launch", "base_launch"): {"native_jetboard_mask": 3},
    ("jetboard_launch", "launch_only"): {"native_jetboard_mask": 2},
    ("jetboard_launch", "task30_base_only"): {"native_jetboard_mask": 1},
    ("jetboard_launch", "task30_base_launch"): {"native_jetboard_mask": 3},
    ("jetboard_launch", "after_save_load"): {"native_jetboard_mask": 3},
    ("jetboard_launch", "after_restart"): {"native_jetboard_mask": 3},
    ("task_30_shadow", "none"): {
        **SHADOW_NATIVE_ISOLATION_OBSERVATIONS,
        "native_task30_item_mask": 0,
        "native_portal_present": 1,
        "native_portal_open": 1,
        "native_task30_node_closed": 1,
    },
    ("task_30_shadow", "seal_only"): {
        **SHADOW_NATIVE_ISOLATION_OBSERVATIONS,
        "native_task30_item_mask": 16,
        "native_portal_present": 1,
        "native_portal_open": 1,
        "native_task30_node_closed": 1,
    },
    ("task_30_shadow", "amulets_only"): {
        **SHADOW_NATIVE_ISOLATION_OBSERVATIONS,
        "native_task30_item_mask": 7,
        "native_portal_present": 1,
        "native_portal_open": 1,
        "native_task30_node_closed": 1,
    },
    ("task_30_shadow", "all_four"): {
        **SHADOW_NATIVE_ISOLATION_OBSERVATIONS,
        "native_task30_item_mask": 23,
        "native_portal_present": 1,
        "native_portal_open": 1,
        "native_task30_node_closed": 1,
    },
    ("task_63_viewer", "artifacts_clear"): {
        **SHADOW_NATIVE_ISOLATION_OBSERVATIONS,
        "native_viewer_item_mask": 0,
        "native_viewer_scene_available": 1,
        "native_viewer_scene_active": 1,
        "native_actor_mask": 12,
    },
    ("task_63_viewer", "artifacts_set"): {
        **SHADOW_NATIVE_ISOLATION_OBSERVATIONS,
        "native_viewer_item_mask": 1984,
        "native_viewer_scene_available": 1,
        "native_viewer_scene_active": 1,
        "native_actor_mask": 12,
    },
    ("orb_600", "postgame_before"): {
        "native_hero_mode": 0,
        "native_postgame_complete": 1,
        "ap_orb_pack_count": 0,
    },
    ("orb_600", "at_600"): {
        "native_skill_total": 600.0,
        "local_orb_earned_count": 600,
        "ap_orb_pack_count": 0,
    },
    ("orb_600", "after_save_load"): {
        "native_skill_total": 600.0,
        "local_orb_earned_count": 600,
        "ap_orb_pack_count": 0,
        "native_hero_mode": 0,
    },
    ("orb_600", "after_restart"): {
        "native_skill_total": 600.0,
        "local_orb_earned_count": 600,
        "ap_orb_pack_count": 0,
        "native_hero_mode": 0,
    },
    ("side_challenges", "zero_cost_before"): {
        "native_gems": 0.0,
        "native_items": 0,
        # The bounded reward mask includes the deliberately closed
        # desert-beast-battle-resolution node at bit 32.
        "native_reward_mask": 32,
        "side_marker_available": 1,
        "side_event_resolved": 1,
        "side_parent_command_suppressed": 1,
        "side_displayed_cost": 0,
        "side_activation_flag": 0,
    },
    ("side_challenges", "zero_cost_after"): {
        "native_gems": 0.0,
        "native_items": 0,
        "native_reward_mask": 32,
        "side_marker_available": 1,
        "side_event_resolved": 1,
        "side_parent_command_suppressed": 1,
        # event.tex becomes the native play icon once the challenge is active.
        "side_displayed_cost": 4,
        "side_activation_flag": 1,
    },
    ("side_challenges", "zero_cost_reload"): {
        "native_gems": 0.0,
        "native_items": 0,
        "native_reward_mask": 32,
        "side_marker_available": 1,
        "side_event_resolved": 1,
        "side_parent_command_suppressed": 1,
        "side_displayed_cost": 0,
        "side_activation_flag": 1,
    },
    ("side_challenges", "courses_hidden"): {
        "native_course_access": 0,
        "native_course_purchase": 0,
        "native_gems": 0.0,
    },
    ("side_challenges", "courses_shadow_open"): {
        "native_course_access": 1,
        "native_course_purchase": 0,
        "native_gems": 0.0,
    },
    ("side_challenges", "courses_shadow_reload"): {
        "native_course_access": 1,
        "native_course_purchase": 0,
        "native_gems": 0.0,
    },
    ("side_challenges", "courses_cleared"): {
        "native_course_access": 0,
        "native_course_purchase": 0,
        "native_gems": 0.0,
    },
}

REQUIRED_CHECKPOINT_OBSERVATIONS: Mapping[tuple[str, str], tuple[str, ...]] = {
    ("orb_600", "at_600"): (
        "orb_standalone_count",
        "orb_container_count",
        "orb_mission_reward_count",
        "orb_challenge_reward_count",
    ),
}
ORB_SOURCE_FAMILY_FIELDS = REQUIRED_CHECKPOINT_OBSERVATIONS[("orb_600", "at_600")]

REQUIRED_OBSERVATIONS: Mapping[str, tuple[str, ...]] = {
    "haven_task_35": (
        "ap_checked_mask",
        "ap_inventory_mask",
        "native_act",
        "native_actor_mask",
        "native_items",
        "native_loaded_level_mask",
        "native_mission_mask",
        "native_reward_mask",
        "native_task_mask",
    ),
    "task_30_shadow": ("ap_relic_count", "ap_checked_mask"),
    "task_63_viewer": (
        "ap_relic_count",
        "ap_checked_mask",
        "native_actor_mask",
        "native_viewer_scene_available",
        "native_viewer_scene_active",
    ),
    "native_reconstruction": (
        "ap_checked_mask",
        "ap_inventory_mask",
        "ap_ledger_revision",
        "native_features",
        "native_items",
        "native_non_ap_feature_mask",
        "native_permanent_target_mask",
        "native_reward_mask",
        "native_task_mask",
        "native_mission_mask",
    ),
    "side_challenges": (
        "ap_checked_mask",
        "ap_relic_count",
        "native_purchase_secrets",
    ),
}

SOURCE_FILES: Mapping[str, tuple[str, ...]] = {
    "engine/game/game-info-h.gc": (
        "(amulet0 0)",
        "(seal-of-mar 4)",
        "(artifact-holocube 6)",
        "(artifact-av-map 10)",
        "(task-perm-list          entity-perm-array)",
        "(sub-task-list           (array game-task-node-info))",
        "(mission-list            (array game-task-node-info))",
    ),
    "engine/game/game-info.gc": (
        "(defmethod task-complete?",
        "(-> this task-perm-list data task status)",
        "(game-task-node-flag close-task)",
    ),
    "engine/game/settings-h.gc": (
        "(hero-mode 0)",
        "(gungame-ratchet 22)",
        "(board 18)",
        "(board-launch 37)",
    ),
    "engine/game/task/game-task.gc": (
        'name "sewer-met-hum-introduction"',
        "(game-task-node mine-boss-resolution)",
        ':play-continue "sewl-elevator"',
        ':pre-play-continue "ctygenb-samos"',
        'name "temple-tests-introduction"',
        "(game-task-node-command add-board-launch)",
        'name "arena-fight-1-throne"',
        'name "desert-artifact-race-1-resolution"',
        'name "arena-fight-2-resolution"',
        'name "desert-oasis-defense-resolution"',
        'name "desert-artifact-race-2-race"',
        'name "desert-beast-battle-resolution"',
        'name "desert-jump-mission-resolution"',
        'name "desert-chase-marauders-resolution"',
        'name "temple-defend-resolution"',
        'name "wascity-defend-resolution"',
    ),
    "engine/game/task/task-control.gc": (
        "(game-task-node-command add-board-launch)",
        "(game-items seal-of-mar)",
        "(game-items artifact-av-map)",
        "(eval-game-task-cmd! s1-0)",
        "(defun task-node-close!",
        "(defmethod game-task-node-info-method-11",
    ),
    "engine/util/script.gc": (
        "(set-continue! *game-info* (the-as basic (-> arg0 param 1)) #f)",
        "(send-event *target* 'want-continue (-> arg0 param 1))",
    ),
    "engine/target/board/target-board.gc": (
        "(game-feature board-launch)",
        "(cpad-pressed?",
        "(cpad-hold?",
    ),
    "engine/target/target-handler.gc": (
        "(go target-continue (the-as continue-point (-> arg3 param 0)))",
    ),
    "engine/game/game-save.gc": (
        "skill-high-watermark",
        "purchase-secrets",
        "(game-save-elt items)",
        "(game-save-elt features)",
        "(game-save-elt task-node-list)",
    ),
    "levels/temple/temple-scenes.gc": (
        '"group-fma-medallion-charge"',
        '"tpl-mardoor-4"',
        '(task-close! "temple-tests-introduction")',
        ':load-point "templea-mardoor"',
    ),
    "levels/forest/forest-tasks.gc": (
        'name "forest-turn-on-machine-res"',
        ':name "for-telescope-fma"',
        ':name "time-map"',
    ),
    "levels/desert/des-burning-bush.gc": (
        "(get-current-task-event",
        "(-> gp-0 tex)",
        "(-> *target* game gem)",
    ),
    "levels/gungame/gungame-manager.gc": (
        "(game-secrets gungame-ratchet)",
        "(set! gp-0 (logior gp-0 4))",
        "(set! gp-0 (logior gp-0 8))",
    ),
}

NATIVE_QUERY_FORMS = (
    """(format #t
  "M11_STATE native_features=~D native_items=~D native_secrets=~D native_purchase_secrets=~D~%"
  (the-as int (-> *game-info* features))
  (the-as int (-> *game-info* items))
  (the-as int (-> *game-info* secrets))
  (the-as int (-> *game-info* purchase-secrets)))""",
    """(format #t
  "M11_STATE native_non_ap_feature_mask=~D native_permanent_target_mask=~D~%"
  (the-as int
    (logclear (-> *game-info* features)
              (game-feature board gun gun-yellow-1 armor0)))
  (ap-items-native-target-mask))""",
    """(format #t
  "M11_STATE native_skill=~F native_skill_total=~F native_skill_high_watermark=~F native_gems=~F~%"
  (-> *game-info* skill)
  (-> *game-info* skill-total)
  (-> *game-info* skill-high-watermark)
  (-> *game-info* gem))""",
    """(let ((task-mask 0)
      (mission-mask 0)
      (nodes (-> *game-info* sub-task-list)))
  (dotimes (i 59)
    (when (task-complete? *game-info* (the-as game-task (+ i 14)))
      (logior! task-mask (ash 1 i))))
  (dotimes (i (-> nodes length))
    (when (nonzero? i)
      (let* ((node (-> nodes i))
             (task-index (the-as int (-> node task))))
        (when (and (>= task-index 14)
                   (<= task-index 72)
                   (logtest? (-> node flags) (game-task-node-flag close-task))
                   (logtest? (-> node flags) (game-task-node-flag closed)))
          (logior! mission-mask (ash 1 (- task-index 14)))))))
  (format #t
    "M11_STATE native_task_mask=~D native_mission_mask=~D~%"
    task-mask
    mission-mask))""",
    """(let ((mask (+
  (if (= (level-status? *level* 'ctygenb #f) 'active) 1 0)
  (if (= (level-status? *level* 'ctywide-ff #f) 'active) 2 0)
  (if (= (level-status? *level* 'slumbset #f) 'active) 4 0)
  (if (= (level-status? *level* 'sewl #f) 'active) 8 0)
  (if (= (level-status? *level* 'sewa #f) 'active) 16 0))))
  (format #t "M11_STATE native_loaded_level_mask=~D native_passage_mask=~D native_act=~D~%"
    mask
    (+ (if (= (level-status? *level* 'ctygenb #f) 'active) 1 0)
       (if (= (level-status? *level* 'sewl #f) 'active) 2 0))
    (-> *ap-runtime* current-act)))""",
    """(let ((actor-mask (+ (if (process-by-name "samos-genb" *active-pool*) 1 0)
                       (if (process-by-name "keira-genb" *active-pool*) 2 0)))
      (viewer-active 0)
      (viewer-available (if (scene-lookup "forest-turn-on-machine-res") 1 0)))
  (when (and (= (-> *ap-runtime* in-cutscene) 1)
             *scene-player*
             (-> *scene-player* 0 scene)
             (string= (-> *scene-player* 0 scene name)
                      "forest-turn-on-machine-res"))
    (set! viewer-active 1)
    (dotimes (i (-> *scene-player* 0 scene actor length))
      (let ((actor (-> *scene-player* 0 scene actor i)))
        (when (handle->process (-> actor process))
          (cond
            ((string= (-> actor name) "for-telescope-fma")
             (logior! actor-mask 4))
            ((string= (-> actor name) "time-map")
             (logior! actor-mask 8)))))))
  (format #t
    "M11_STATE native_actor_mask=~D native_viewer_scene_available=~D native_viewer_scene_active=~D~%"
    actor-mask
    viewer-available
    viewer-active))""",
    """(let ((mask 0))
  (when (task-node-closed? (game-task-node arena-fight-1-throne))
    (logior! mask 1))
  (when (task-node-closed? (game-task-node desert-artifact-race-1-resolution))
    (logior! mask 2))
  (when (task-node-closed? (game-task-node arena-fight-2-resolution))
    (logior! mask 4))
  (when (task-node-closed? (game-task-node desert-oasis-defense-resolution))
    (logior! mask 8))
  (when (task-node-closed? (game-task-node desert-artifact-race-2-race))
    (logior! mask 16))
  (when (task-node-closed? (game-task-node desert-beast-battle-resolution))
    (logior! mask 32))
  (when (task-node-closed? (game-task-node desert-jump-mission-resolution))
    (logior! mask 64))
  (when (task-node-closed? (game-task-node desert-chase-marauders-resolution))
    (logior! mask 128))
  (when (task-node-closed? (game-task-node temple-defend-resolution))
    (logior! mask 256))
  (when (task-node-closed? (game-task-node wascity-defend-resolution))
    (logior! mask 512))
  (format #t "M11_STATE native_reward_mask=~D~%" mask))""",
    """(format #t
  "M11_STATE native_jetboard_mask=~D native_viewer_item_mask=~D native_hero_mode=~D native_postgame_complete=~D native_course_access=~D native_course_purchase=~D~%"
  (+ (if (logtest? (game-feature board) (-> *game-info* features)) 1 0)
     (if (logtest? (game-feature board-launch) (-> *game-info* features)) 2 0))
  (the-as int
    (logand (-> *game-info* items)
            (game-items artifact-holocube artifact-av-reflector artifact-av-prism artifact-av-generator artifact-av-map)))
  (if (logtest? (game-secrets hero-mode) (-> *game-info* secrets)) 1 0)
  (if (task-complete? *game-info* (game-task desert-final-boss)) 1 0)
  (if (logtest? (game-secrets gungame-ratchet) (-> *game-info* secrets)) 1 0)
  (if (logtest? (game-secrets gungame-ratchet) (-> *game-info* purchase-secrets)) 1 0))""",
    """(let ((door (process-by-name "tpl-mardoor-4" *active-pool*))
      (node (task-node-by-name "temple-tests-introduction")))
  (format #t
    "M11_STATE native_portal_present=~D native_portal_open=~D native_task30_node_closed=~D native_task30_item_mask=~D~%"
    (if door 1 0)
    (if (and door (send-event door 'open?)) 1 0)
    (if (logtest? (-> node flags) (game-task-node-flag closed)) 1 0)
    (the-as int
      (logand (-> *game-info* items)
              (game-items seal-of-mar amulet0 amulet1 amulet2)))))""",
)
NATIVE_QUERY_FIELDS = frozenset(
    {
        "native_features",
        "native_items",
        "native_secrets",
        "native_purchase_secrets",
        "native_skill",
        "native_skill_total",
        "native_skill_high_watermark",
        "native_gems",
        "native_task_mask",
        "native_mission_mask",
        "native_non_ap_feature_mask",
        "native_loaded_level_mask",
        "native_passage_mask",
        "native_permanent_target_mask",
        "native_act",
        "native_actor_mask",
        "native_reward_mask",
        "native_jetboard_mask",
        "native_viewer_item_mask",
        "native_hero_mode",
        "native_postgame_complete",
        "native_course_access",
        "native_course_purchase",
        "native_portal_present",
        "native_portal_open",
        "native_task30_node_closed",
        "native_task30_item_mask",
        "native_viewer_scene_available",
        "native_viewer_scene_active",
    }
)
LIVE_LOG_LIMIT = 2 * 1024 * 1024
LIVE_LOG_TIMEOUT_SECONDS = 5.0
LIVE_SNAPSHOT_MAX_AGE_SECONDS = 5.0
REPL_FAILURE_MARKERS = (
    "-- Compilation Error! --",
    "REPL Error:",
    "Typecheck failed.",
    "call_method_of_type failed!",
    "has invalid type ptr",
)
LIVE_STAGE_SETTLE_SECONDS = 0.75
CLEAN_START_STAGE_PRESETS = frozenset(
    {
        "haven_task35_hub_candidate",
        "jetboard_task30_scene_stage",
        "side_zero_cost_desb4_intro_stage",
        "task30_scene_stage",
        "task63_clear_intro_stage",
        "task63_set_intro_stage",
    }
)
JETBOARD_FEATURE_STAGE_PRESETS = frozenset(
    {
        "jetboard_00",
        "jetboard_base_only",
        "jetboard_base_launch",
        "jetboard_launch_only",
    }
)
JETBOARD_RECONCILIATION_RESTORE_PRESETS = frozenset({"jetboard_restore_reconciliation"})
SIDE_MARKER_CAPTURE_PRESETS = frozenset({"side_zero_cost_desb4"})
SIDE_CHALLENGE_ACTIVE_CAPTURE_PRESETS = frozenset({"side_observe_desb4_after"})
SIDE_CHALLENGE_RELOAD_CAPTURE_PRESETS = frozenset({"side_observe_desb4_reload"})
COURSE_CAPTURE_PRESETS = frozenset(
    {
        "courses_cleared",
        "courses_hidden",
        "courses_observe_reload",
        "courses_shadow_open",
    }
)
SIDE_MARKER_STAGE_PRESETS = frozenset(
    {
        "side_zero_cost_desb4_activate_stage",
        "side_zero_cost_desb4_refresh_stage",
        "side_zero_cost_desb4_suppress_parent_reward_stage",
        "side_zero_cost_desb4_stage",
    }
)
SIDE_CHALLENGE_INITIALIZATION_ORDER = (
    "side_zero_cost_desb4_intro_stage",
    "side_zero_cost_desb4_suppress_parent_reward_stage",
    "side_zero_cost_desb4_activate_stage",
    "side_zero_cost_desb4_stage",
    "side_zero_cost_desb4_refresh_stage",
)
CAPTURE_ONLY_PRESETS = frozenset(
    {"courses_observe_reload", "task63_set_active_capture"}
) | (SIDE_MARKER_CAPTURE_PRESETS)
STAGE_ONLY_PRESETS = JETBOARD_RECONCILIATION_RESTORE_PRESETS
READ_ONLY_PROBE_FORMS: Mapping[str, str] = {
    "side_marker_desb4": """(let ((raw
        (search-process-tree
          *active-pool*
          (lambda ((candidate process))
            (and (type? candidate des-burning-bush)
                 (= (-> (the-as des-burning-bush candidate) task actor)
                    (game-task-actor burning-bush-desb-4))))))
      (parent (task-node-by-name "desert-beast-battle-resolution"))
      (intro (task-node-by-name "desert-bbush-destroy-interceptors-introduction"))
      (resolution (task-node-by-name "desert-bbush-destroy-interceptors-resolution")))
  (format #t
    "M11_STATE side_parent_shadow_closed=~D side_parent_command_suppressed=~D side_intro_node_closed=~D side_intro_node_open=~D side_resolution_node_closed=~D~%"
    (if (logtest? (-> parent flags) (game-task-node-flag closed)) 1 0)
    (if (and (= (-> parent command-index) #x3a)
             (= (-> parent command-count) 0)) 1 0)
    (if (logtest? (-> intro flags) (game-task-node-flag closed)) 1 0)
    (if (game-task-node-info-method-12 intro) 1 0)
    (if (logtest? (-> resolution flags) (game-task-node-flag closed)) 1 0))
  (if raw
    (let* ((bush (the-as des-burning-bush raw))
           (control (-> bush task))
           (event (get-current-task-event control)))
      (format #t
        "M11_STATE side_marker_available=1 side_event_resolved=~D side_displayed_cost=~D side_activation_flag=~D~%"
        (if (!= (-> control current-node) (game-task-node none)) 1 0)
        (the-as int (-> event tex))
        (the-as int (-> bush bb-perm user-object 0))))
    (format #t
      "M11_STATE side_marker_available=0 side_event_resolved=0 side_displayed_cost=-1 side_activation_flag=-1~%")))"""
}
PROJECT_AGENT_MODULES = frozenset({"diagnostics", "repl_client"})


def _load_project_agent_module(name: str) -> ModuleType:
    """Load one project agent without initializing Archipelago's world registry."""

    if name not in PROJECT_AGENT_MODULES:
        raise SpikeError(f"Project agent module is not allowlisted: {name}")
    archipelago_root = str(DEFAULT_ARCHIPELAGO)
    if not DEFAULT_ARCHIPELAGO.is_dir():
        raise SpikeError(
            f"Archipelago dependency root not found: {DEFAULT_ARCHIPELAGO}"
        )
    if archipelago_root not in sys.path:
        sys.path.append(archipelago_root)
    package_paths = (
        ("_m11_project_worlds", REPOSITORY_ROOT / "worlds"),
        ("_m11_project_worlds.jak3", REPOSITORY_ROOT / "worlds" / "jak3"),
        (
            "_m11_project_worlds.jak3.agents",
            REPOSITORY_ROOT / "worlds" / "jak3" / "agents",
        ),
    )
    for package_name, package_path in package_paths:
        if package_name in sys.modules:
            continue
        package = ModuleType(package_name)
        package.__package__ = package_name
        package.__path__ = [str(package_path)]  # type: ignore[attr-defined]
        sys.modules[package_name] = package
    return importlib.import_module(f"_m11_project_worlds.jak3.agents.{name}")


PRESET_FORMS: Mapping[str, tuple[str, str, str]] = {
    "haven_task35_hub_candidate": (
        "haven_task_35",
        "before_entry",
        """(let ((point (get-continue-by-name *game-info* "ctygenb-samos")))
  (set-continue! *game-info* point #f)
  (send-event *target* 'continue point))""",
    ),
    "haven_task35_enter_sewer": (
        "haven_task_35",
        "sewer_entry",
        """(let ((point (get-continue-by-name *game-info* "sewl-elevator")))
  (set-continue! *game-info* point #f)
  (send-event *target* 'continue point))""",
    ),
    "haven_task35_return_hub": (
        "haven_task_35",
        "hub_return",
        """(let ((point (get-continue-by-name *game-info* "ctygenb-samos")))
  (set-continue! *game-info* point #f)
  (send-event *target* 'continue point))""",
    ),
    "jetboard_00": (
        "jetboard_launch",
        "00",
        """(begin
  (set! *ap3-permanent-items-reconciliation-suspended-hook*
        ap3-permanent-items-noop-reconciliation-suspended?)
  (logclear! (-> *game-info* features) (game-feature board board-launch)))""",
    ),
    "jetboard_base_only": (
        "jetboard_launch",
        "base_only",
        """(begin
  (set! *ap3-permanent-items-reconciliation-suspended-hook*
        ap3-permanent-items-noop-reconciliation-suspended?)
  (logclear! (-> *game-info* features) (game-feature board-launch))
  (logior! (-> *game-info* features) (game-feature board)))""",
    ),
    "jetboard_base_launch": (
        "jetboard_launch",
        "base_launch",
        """(begin
  (set! *ap3-permanent-items-reconciliation-suspended-hook*
        ap3-permanent-items-noop-reconciliation-suspended?)
  (logior! (-> *game-info* features) (game-feature board board-launch)))""",
    ),
    "jetboard_task30_base_only": (
        "jetboard_launch",
        "task30_base_only",
        """(let ((training (task-node-by-name "temple-tests-hover-training"))
      (door (task-node-by-name "temple-tests-oracle-door-crossed"))
      (point (get-continue-by-name *game-info* "templec-start")))
  (game-task-node-info-method-11 training 'event)
  (game-task-node-info-method-11 door 'event)
  (set! *ap3-permanent-items-reconciliation-suspended-hook*
        ap3-permanent-items-noop-reconciliation-suspended?)
  (logclear! (-> *game-info* features) (game-feature board-launch))
  (logior! (-> *game-info* features) (game-feature board))
  (set-continue! *game-info* point #f)
  (send-event *target* 'continue point))""",
    ),
    "jetboard_task30_base_launch": (
        "jetboard_launch",
        "task30_base_launch",
        """(let ((training (task-node-by-name "temple-tests-hover-training"))
      (door (task-node-by-name "temple-tests-oracle-door-crossed"))
      (point (get-continue-by-name *game-info* "templec-start")))
  (game-task-node-info-method-11 training 'event)
  (game-task-node-info-method-11 door 'event)
  (set! *ap3-permanent-items-reconciliation-suspended-hook*
        ap3-permanent-items-noop-reconciliation-suspended?)
  (logior! (-> *game-info* features) (game-feature board board-launch))
  (set-continue! *game-info* point #f)
  (send-event *target* 'continue point))""",
    ),
    "jetboard_launch_only": (
        "jetboard_launch",
        "launch_only",
        """(begin
  (set! *ap3-permanent-items-reconciliation-suspended-hook*
        ap3-permanent-items-noop-reconciliation-suspended?)
  (logclear! (-> *game-info* features) (game-feature board))
  (logior! (-> *game-info* features) (game-feature board-launch)))""",
    ),
    "jetboard_restore_reconciliation": (
        "jetboard_launch",
        "after_save_load",
        """(set! *ap3-permanent-items-reconciliation-suspended-hook*
  ap-rewards-permanent-item-reconciliation-suspended?)""",
    ),
    "jetboard_task30_scene_stage": (
        "jetboard_launch",
        "task30_base_only",
        """(begin
  (play-clean #f)
  (start 'play (get-continue-by-name *game-info* "templec-start"))
  (set-master-mode 'game))""",
    ),
    "task30_none": (
        "task_30_shadow",
        "none",
        "(logclear! (-> *game-info* items) (game-items seal-of-mar amulet0 amulet1 amulet2))",
    ),
    "task30_seal_only": (
        "task_30_shadow",
        "seal_only",
        """(begin
  (logclear! (-> *game-info* items) (game-items seal-of-mar amulet0 amulet1 amulet2))
  (logior! (-> *game-info* items) (game-items seal-of-mar)))""",
    ),
    "task30_amulets_only": (
        "task_30_shadow",
        "amulets_only",
        """(begin
  (logclear! (-> *game-info* items) (game-items seal-of-mar amulet0 amulet1 amulet2))
  (logior! (-> *game-info* items) (game-items amulet0 amulet1 amulet2)))""",
    ),
    "task30_all_four": (
        "task_30_shadow",
        "all_four",
        """(begin
  (logclear! (-> *game-info* items) (game-items seal-of-mar amulet0 amulet1 amulet2))
  (logior! (-> *game-info* items) (game-items seal-of-mar amulet0 amulet1 amulet2)))""",
    ),
    "task30_scene_stage": (
        "task_30_shadow",
        "none",
        """(let ((point (get-continue-by-name *game-info* "templea-mardoor")))
  (set-continue! *game-info* point #f)
  (send-event *target* 'continue point))""",
    ),
    "task30_scene_activate": (
        "task_30_shadow",
        "none",
        """(let ((node (task-node-by-name "temple-tests-introduction"))
      (door (process-by-name "tpl-mardoor-4" *active-pool*)))
  (logior! (-> node flags) (game-task-node-flag closed))
  (when door (send-event door 'open)))""",
    ),
    "task63_clear_scene_stage": (
        "task_63_viewer",
        "artifacts_clear",
        """(let ((point (get-continue-by-name *game-info* "forest-pillar-start")))
  (set-continue! *game-info* point #f)
  (send-event *target* 'continue point))""",
    ),
    "task63_set_scene_stage": (
        "task_63_viewer",
        "artifacts_set",
        """(let ((point (get-continue-by-name *game-info* "forest-pillar-start")))
  (set-continue! *game-info* point #f)
  (send-event *target* 'continue point))""",
    ),
    "task63_clear_intro_stage": (
        "task_63_viewer",
        "artifacts_clear",
        """(begin
  (play-clean #f)
  (start 'play (get-continue-by-name *game-info* "forest-pillar-start"))
  (set-master-mode 'game))""",
    ),
    "task63_set_intro_stage": (
        "task_63_viewer",
        "artifacts_set",
        """(begin
  (play-clean #f)
  (start 'play (get-continue-by-name *game-info* "forest-pillar-start"))
  (set-master-mode 'game))""",
    ),
    "task63_clear": (
        "task_63_viewer",
        "artifacts_clear",
        """(begin
  (logclear! (-> *game-info* items)
             (game-items artifact-holocube artifact-av-reflector artifact-av-prism artifact-av-generator artifact-av-map))
  (when (not *scene-player*)
    (process-spawn scene-player :init scene-player-init "forest-turn-on-machine-res" #t "forest-pillar-start" :name "scene-player"))
  (none))""",
    ),
    "task63_set": (
        "task_63_viewer",
        "artifacts_set",
        """(begin
  (logior! (-> *game-info* items)
           (game-items artifact-holocube artifact-av-reflector artifact-av-prism artifact-av-generator artifact-av-map))
  (when (not *scene-player*)
    (process-spawn scene-player :init scene-player-init "forest-turn-on-machine-res" #t "forest-pillar-start" :name "scene-player"))
  (none))""",
    ),
    "task63_set_active_capture": (
        "task_63_viewer",
        "artifacts_set",
        """(begin
  (logior! (-> *game-info* items)
           (game-items artifact-holocube artifact-av-reflector artifact-av-prism artifact-av-generator artifact-av-map))
  (none))""",
    ),
    "native_reconstruction_targets": (
        "native_reconstruction",
        "before_save",
        "(begin (logior! (-> *game-info* features) (game-feature board board-launch gun gun-yellow-1 armor0)) (logior! (-> *game-info* items) (game-items seal-of-mar amulet0 amulet1 amulet2 artifact-holocube artifact-av-reflector artifact-av-prism artifact-av-generator artifact-av-map)))",
    ),
    "native_reconstruction_rewards": (
        "native_reconstruction",
        "before_save",
        """(begin
  (logior! (-> (task-node-by-name "arena-fight-1-throne") flags) (game-task-node-flag closed))
  (logior! (-> (task-node-by-name "desert-artifact-race-1-resolution") flags) (game-task-node-flag closed))
  (logior! (-> (task-node-by-name "arena-fight-2-resolution") flags) (game-task-node-flag closed))
  (logior! (-> (task-node-by-name "desert-oasis-defense-resolution") flags) (game-task-node-flag closed))
  (logior! (-> (task-node-by-name "desert-artifact-race-2-race") flags) (game-task-node-flag closed))
  (logior! (-> (task-node-by-name "desert-beast-battle-resolution") flags) (game-task-node-flag closed))
  (logior! (-> (task-node-by-name "desert-jump-mission-resolution") flags) (game-task-node-flag closed))
  (logior! (-> (task-node-by-name "desert-chase-marauders-resolution") flags) (game-task-node-flag closed))
  (logior! (-> (task-node-by-name "temple-defend-resolution") flags) (game-task-node-flag closed))
  (logior! (-> (task-node-by-name "wascity-defend-resolution") flags) (game-task-node-flag closed))
  (update-task-masks 'event)
  (eval-game-task-cmd! (task-node-by-name "desert-artifact-race-2-race"))
  (eval-game-task-cmd! (task-node-by-name "desert-beast-battle-resolution")))""",
    ),
    "courses_shadow_open": (
        "side_challenges",
        "courses_shadow_open",
        "(begin (logclear! (-> *game-info* purchase-secrets) (game-secrets gungame-ratchet)) (logior! (-> *game-info* secrets) (game-secrets gungame-ratchet)))",
    ),
    "courses_observe_reload": (
        "side_challenges",
        "courses_shadow_reload",
        "(none)",
    ),
    "side_zero_cost_desb4": (
        "side_challenges",
        "zero_cost_before",
        """(let ((parent (task-node-by-name "desert-beast-battle-resolution"))
      (raw
        (search-process-tree
          *active-pool*
          (lambda ((candidate process))
            (and (type? candidate des-burning-bush)
                 (= (-> (the-as des-burning-bush candidate) task actor)
                    (game-task-actor burning-bush-desb-4)))))))
  (if raw
    (let* ((bush (the-as des-burning-bush raw))
           (control (-> bush task))
           (event (get-current-task-event control))
           (before (the-as int (-> event tex))))
      (set! (-> event tex) (game-task-icon gaticon-00))
      (format #t
        "M11_STATE side_marker_available=1 side_event_resolved=~D side_parent_command_suppressed=~D side_previous_cost=~D side_displayed_cost=~D side_activation_flag=~D~%"
        (if (!= (-> control current-node) (game-task-node none)) 1 0)
        (if (and (= (-> parent command-index) #x3a)
                 (= (-> parent command-count) 0)) 1 0)
        before
        (the-as int (-> (get-current-task-event control) tex))
        (the-as int (-> bush bb-perm user-object 0))))
    (format #t
      "M11_STATE side_marker_available=0 side_event_resolved=0 side_parent_command_suppressed=0 side_previous_cost=-1 side_displayed_cost=-1 side_activation_flag=-1~%")))""",
    ),
    "side_zero_cost_desb4_activate_stage": (
        "side_challenges",
        "zero_cost_before",
        """(let ((parent (task-node-by-name "desert-beast-battle-resolution"))
      (intro (task-node-by-name "desert-bbush-destroy-interceptors-introduction")))
  (logior! (-> parent flags) (game-task-node-flag closed))
  (game-task-node-info-method-11 intro 'event))""",
    ),
    "side_zero_cost_desb4_refresh_stage": (
        "side_challenges",
        "zero_cost_before",
        "(+! (-> *game-info* task-counter) 1)",
    ),
    "side_zero_cost_desb4_suppress_parent_reward_stage": (
        "side_challenges",
        "zero_cost_before",
        """(let ((parent (task-node-by-name "desert-beast-battle-resolution")))
  (if (and (= (-> parent command-index) #x3a)
           (= (-> parent command-count) 1)
           (not (logtest? (-> *game-info* items)
                          (game-items artifact-av-reflector))))
    (begin
      (set! (-> parent command-count) 0)
      (format #t "M11_STATE side_parent_command_suppressed=1~%"))
    (format #t
      "REPL Error: side parent reward suppression refused index=~D count=~D items=~D~%"
      (the-as int (-> parent command-index))
      (the-as int (-> parent command-count))
      (the-as int (-> *game-info* items)))))""",
    ),
    "side_observe_desb4_after": (
        "side_challenges",
        "zero_cost_after",
        """(let ((parent (task-node-by-name "desert-beast-battle-resolution"))
      (raw
        (search-process-tree
          *active-pool*
          (lambda ((candidate process))
            (and (type? candidate des-burning-bush)
                 (= (-> (the-as des-burning-bush candidate) task actor)
                    (game-task-actor burning-bush-desb-4)))))))
  (if raw
    (let* ((bush (the-as des-burning-bush raw))
           (control (-> bush task))
           (event (get-current-task-event control)))
      (format #t
        "M11_STATE side_marker_available=1 side_event_resolved=~D side_parent_command_suppressed=~D side_displayed_cost=~D side_activation_flag=~D~%"
        (if (!= (-> control current-node) (game-task-node none)) 1 0)
        (if (and (= (-> parent command-index) #x3a)
                 (= (-> parent command-count) 0)) 1 0)
        (the-as int (-> event tex))
        (the-as int (-> bush bb-perm user-object 0))))
    (format #t
      "M11_STATE side_marker_available=0 side_event_resolved=0 side_parent_command_suppressed=0 side_displayed_cost=-1 side_activation_flag=-1~%")))""",
    ),
    "side_observe_desb4_reload": (
        "side_challenges",
        "zero_cost_reload",
        """(let ((parent (task-node-by-name "desert-beast-battle-resolution"))
      (raw
        (search-process-tree
          *active-pool*
          (lambda ((candidate process))
            (and (type? candidate des-burning-bush)
                 (= (-> (the-as des-burning-bush candidate) task actor)
                    (game-task-actor burning-bush-desb-4)))))))
  (if raw
    (let* ((bush (the-as des-burning-bush raw))
           (control (-> bush task))
           (event (get-current-task-event control)))
      (format #t
        "M11_STATE side_marker_available=1 side_event_resolved=~D side_parent_command_suppressed=~D side_displayed_cost=~D side_activation_flag=~D~%"
        (if (!= (-> control current-node) (game-task-node none)) 1 0)
        (if (and (= (-> parent command-index) #x3a)
                 (= (-> parent command-count) 0)) 1 0)
        (the-as int (-> event tex))
        (the-as int (-> bush bb-perm user-object 0))))
    (format #t
      "M11_STATE side_marker_available=0 side_event_resolved=0 side_parent_command_suppressed=0 side_displayed_cost=-1 side_activation_flag=-1~%")))""",
    ),
    "side_zero_cost_desb4_stage": (
        "side_challenges",
        "zero_cost_before",
        """(let ((point (get-continue-by-name *game-info* "desert-bbush-desb-4")))
  (set-continue! *game-info* point #f)
  (send-event *target* 'continue point))""",
    ),
    "side_zero_cost_desb4_intro_stage": (
        "side_challenges",
        "zero_cost_before",
        """(begin
  (play-clean #f)
  (start 'play (get-continue-by-name *game-info* "desert-bbush-desb-4"))
  (set-master-mode 'game))""",
    ),
    "courses_cleared": (
        "side_challenges",
        "courses_cleared",
        "(begin (logclear! (-> *game-info* purchase-secrets) (game-secrets gungame-ratchet)) (logclear! (-> *game-info* secrets) (game-secrets gungame-ratchet)))",
    ),
    "courses_hidden": (
        "side_challenges",
        "courses_hidden",
        "(begin (logclear! (-> *game-info* purchase-secrets) (game-secrets gungame-ratchet)) (logclear! (-> *game-info* secrets) (game-secrets gungame-ratchet)))",
    ),
}


class SpikeError(RuntimeError):
    """Expected refusal or invalid recorder state."""


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def require_safe_artifact_path(path: Path) -> Path:
    resolved = path.resolve(strict=False)
    for reference in REFERENCE_ROOTS:
        if is_relative_to(resolved, reference.resolve(strict=False)):
            raise SpikeError(
                f"Refusing artifact path inside reference tree: {resolved}"
            )
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_revision(root: Path) -> str:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={root.resolve()}", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def audit_sources(
    jak_project: Path, archipelago: Path, decompile: Path
) -> dict[str, Any]:
    revisions = {
        "jak-project": _git_revision(jak_project),
        "Archipelago": _git_revision(archipelago),
    }
    for name, expected in EXPECTED_REVISIONS.items():
        if revisions[name] != expected:
            raise SpikeError(
                f"{name} revision mismatch: expected {expected}, got {revisions[name]}"
            )
    primary_root = jak_project / "goal_src" / "jak3"
    snapshot_root = decompile / "jak3" / "data" / "goal_src" / "jak3"
    files: dict[str, dict[str, str]] = {}
    for relative, anchors in SOURCE_FILES.items():
        primary = primary_root / relative
        snapshot = snapshot_root / relative
        if not primary.is_file() or not snapshot.is_file():
            raise SpikeError(f"Missing audited source pair: {relative}")
        content = primary.read_text("utf-8")
        missing = [anchor for anchor in anchors if anchor not in content]
        if missing:
            raise SpikeError(f"Source anchors missing from {relative}: {missing}")
        primary_hash = sha256_file(primary)
        snapshot_hash = sha256_file(snapshot)
        if primary_hash != snapshot_hash:
            raise SpikeError(f"Primary/decompile source mismatch: {relative}")
        files[relative] = {"sha256": primary_hash, "snapshot_sha256": snapshot_hash}
    return {
        "status": "pass",
        "opengoal_version": PINNED_OPENGOAL_VERSION,
        "revisions": revisions,
        "files": files,
    }


def fallback_counts(proven_orb_maximum: int, *, launch_retired: bool) -> dict[str, int]:
    if proven_orb_maximum < 0 or proven_orb_maximum > 600:
        raise SpikeError("Proven orb maximum must be between 0 and 600.")
    thresholds = proven_orb_maximum // 25
    launch_delta = int(launch_retired)
    locations = 123 + thresholds
    progression = 26 - launch_delta
    useful = 28
    filler = 69 + thresholds + launch_delta
    if progression + useful + filler != locations:
        raise AssertionError("Fallback pool arithmetic no longer conserves the pool.")
    return {
        "orb_thresholds": thresholds,
        "locations": locations,
        "progression": progression,
        "useful": useful,
        "filler": filler,
    }


def fallback_versioning(
    proven_orb_maximum: int, *, launch_retired: bool
) -> dict[str, int | bool]:
    """Describe mandatory compatibility bumps without mutating the registry."""

    counts = fallback_counts(proven_orb_maximum, launch_retired=launch_retired)
    location_changed = counts["orb_thresholds"] != 24
    item_changed = launch_retired
    contract_changed = location_changed or item_changed
    return {
        **counts,
        "item_table_version_bump": int(item_changed),
        "location_table_version_bump": int(location_changed),
        "slot_data_version_bump": int(contract_changed),
        "item_table_hash_required": item_changed,
        "location_table_hash_required": location_changed,
        "resolved_options_hash_required": item_changed,
        "reject_older_development_state": contract_changed,
    }


def _state_path(run: Path) -> Path:
    candidate = require_safe_artifact_path(run)
    return candidate / "run.json" if candidate.is_dir() else candidate


def load_state(run: Path) -> tuple[Path, dict[str, Any]]:
    path = _state_path(run)
    if not path.is_file():
        raise SpikeError(f"Spike run state not found: {path}")
    state = json.loads(path.read_text("utf-8"))
    if state.get("schema_version") != STATE_SCHEMA_VERSION:
        raise SpikeError("Unsupported spike run schema.")
    experiment_id = state.get("experiment_id")
    if not isinstance(experiment_id, str) or not EXPERIMENT_RE.fullmatch(experiment_id):
        raise SpikeError("Malformed spike experiment ID.")
    return path, state


def save_state(path: Path, state: Mapping[str, Any]) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _record_event(
    state: dict[str, Any], name: str, context: Mapping[str, object]
) -> None:
    state.setdefault("events", []).append(
        {"event_name": name, "observed_utc": utc_now(), "context": dict(context)}
    )


def start_run(
    artifact_root: Path, spike: str, save_slot: int, *, acknowledged: bool
) -> Path:
    if not acknowledged:
        raise SpikeError("Explicit disposable save-slot acknowledgement is required.")
    if spike not in SPIKES:
        raise SpikeError(f"Unknown spike: {spike}")
    if save_slot < 0 or save_slot > 3:
        raise SpikeError("Disposable native save slot must be 0 through 3.")
    root = require_safe_artifact_path(artifact_root)
    experiment_id = f"m11-{spike.replace('_', '-')}-{secrets.token_hex(4)}"
    run = root / experiment_id
    run.mkdir(parents=True, exist_ok=False)
    state: dict[str, Any] = {
        "schema_version": STATE_SCHEMA_VERSION,
        "experiment_id": experiment_id,
        "spike": spike,
        "disposable_save_slot": save_slot,
        "disposable_slot_acknowledged": True,
        "started_utc": utc_now(),
        "status": "started",
        "checkpoints": {},
        "bridge_snapshot_uses": [],
        "events": [],
    }
    _record_event(
        state,
        "feasibility.spike.started",
        {"spike": spike, "status": "started", "save_generation": 0},
    )
    save_state(run / "run.json", state)
    return run


def parse_assertions(values: Sequence[str]) -> dict[str, str]:
    assertions: dict[str, str] = {}
    for value in values:
        name, separator, status = value.partition("=")
        if not separator or not TOKEN_RE.fullmatch(name):
            raise SpikeError(f"Malformed assertion: {value}")
        normalized = status.lower()
        if normalized not in {"pass", "fail", "blocked"}:
            raise SpikeError(
                f"Assertion status must be pass, fail, or blocked: {value}"
            )
        assertions[name] = normalized
    return assertions


def parse_observations(values: Sequence[str]) -> dict[str, int | float]:
    observations: dict[str, int | float] = {}
    for value in values:
        name, separator, raw = value.partition("=")
        if not separator or name not in OBSERVATION_FIELDS:
            raise SpikeError(f"Observation field is not allowlisted: {value}")
        try:
            observations[name] = (
                float(raw) if any(char in raw for char in ".eE") else int(raw, 0)
            )
        except ValueError as exc:
            raise SpikeError(f"Observation must be numeric: {value}") from exc
    return observations


def parse_native_response(response: str) -> dict[str, int | float]:
    markers = re.findall(r"M11_STATE\s+([^\r\n]+)", response)
    if not markers:
        raise SpikeError(
            "OpenGOAL diagnostic output did not contain the restricted "
            "M11_STATE marker."
        )
    observations: dict[str, int | float] = {}
    for marker in markers:
        keys = re.findall(r"(?:^|\s)([a-z][a-z0-9_]*)=", marker)
        for key in keys:
            if key not in OBSERVATION_FIELDS:
                raise SpikeError(f"Observation field is not allowlisted: {key}")
        numeric_values = re.findall(
            r"(?:^|\s)([a-z][a-z0-9_]*)=\s*([-+]?\d+(?:\.\d+)?)", marker
        )
        if len(numeric_values) != len(keys):
            raise SpikeError("OpenGOAL M11_STATE observation was not numeric.")
        observations.update(
            parse_observations([f"{key}={value}" for key, value in numeric_values])
        )
    return observations


def _canonical_json_bytes(value: object) -> bytes:
    rendered = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return (rendered + "\n").encode("utf-8")


def _bridge_snapshot_token(snapshot: str, field: str) -> str:
    match = re.search(rf"(?m)^{re.escape(field)} ([^\r\n]+)$", snapshot)
    if match is None:
        raise SpikeError(f"Protocol bridge snapshot omitted {field}.")
    return match.group(1)


def _ap_state_observations(
    state_path: Path,
    bridge_snapshot: Path,
    *,
    expected_native_save_slot: int,
) -> dict[str, int]:
    """Derive bounded AP controls from one checksummed, live-bound state file."""

    path = require_safe_artifact_path(state_path)
    if not path.is_file():
        raise SpikeError(f"Persistent AP state file not found: {path}")
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SpikeError("Persistent AP state is not valid UTF-8 JSON.") from exc
    if not isinstance(envelope, Mapping) or set(envelope) != {
        "format",
        "checksum_algorithm",
        "payload_sha256",
        "payload",
    }:
        raise SpikeError("Persistent AP state envelope has an incompatible shape.")
    if envelope["format"] != "jak3-ap-state":
        raise SpikeError("Persistent AP state format is not jak3-ap-state.")
    if envelope["checksum_algorithm"] != "sha256":
        raise SpikeError("Persistent AP state checksum algorithm is not sha256.")
    payload = envelope["payload"]
    checksum = envelope["payload_sha256"]
    if not isinstance(payload, Mapping) or not isinstance(checksum, str):
        raise SpikeError("Persistent AP state payload/checksum has an invalid shape.")
    actual_checksum = hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
    if not secrets.compare_digest(checksum, actual_checksum):
        raise SpikeError("Persistent AP state checksum does not match its payload.")

    snapshot_path = require_safe_artifact_path(bridge_snapshot)
    if not snapshot_path.is_file():
        raise SpikeError(f"Protocol bridge snapshot not found: {snapshot_path}")
    snapshot = snapshot_path.read_text(encoding="utf-8", errors="replace")
    begin = _bridge_snapshot_value(snapshot, "snapshot_begin")
    if _bridge_snapshot_value(snapshot, "snapshot_end") != begin:
        raise SpikeError(
            "Protocol bridge snapshot revision is internally inconsistent."
        )
    live_identity = _bridge_snapshot_token(snapshot, "native_save_identity")
    state_slot = payload.get("native_save_slot")
    state_identity = payload.get("native_save_identity")
    if state_slot != expected_native_save_slot:
        raise SpikeError(
            "Persistent AP state belongs to native save slot "
            f"{state_slot}, but this run requires {expected_native_save_slot}."
        )
    if state_identity != live_identity:
        raise SpikeError(
            "Persistent AP state native-save identity does not match the live bridge."
        )

    revision = payload.get("state_revision")
    counts = payload.get("received_item_counts")
    checked = payload.get("checked_location_bits")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
        raise SpikeError("Persistent AP state revision is not a non-negative integer.")
    if not isinstance(counts, Mapping):
        raise SpikeError("Persistent AP received-item counts are not a mapping.")
    inventory_mask = 0
    for item_id, bit in AP_STATE_ITEM_BITS.items():
        count = counts.get(str(item_id), 0)
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise SpikeError("Persistent AP received-item count is invalid.")
        if count:
            inventory_mask |= bit
    orb_pack_count = 0
    for item_id in AP_ORB_PACK_IDS:
        count = counts.get(str(item_id), 0)
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise SpikeError("Persistent AP Orb Pack receipt count is invalid.")
        orb_pack_count += count
    relic_count = 0
    for item_id in AP_RELIC_IDS:
        count = counts.get(str(item_id), 0)
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise SpikeError("Persistent AP relic receipt count is invalid.")
        relic_count += count

    if not isinstance(checked, list) or any(
        isinstance(location_id, bool) or not isinstance(location_id, int)
        for location_id in checked
    ):
        raise SpikeError("Persistent AP checked-location bits are not integer IDs.")
    if len(set(checked)) != len(checked):
        raise SpikeError("Persistent AP checked-location bits contain duplicates.")
    unknown_checks = set(checked) - set(AP_STATE_CHECK_IDS)
    if unknown_checks:
        raise SpikeError(
            "Persistent AP state contains checks outside the bounded Milestone 10 "
            f"slice: {sorted(unknown_checks)}"
        )
    checked_set = set(checked)
    checked_mask = sum(
        1 << index
        for index, location_id in enumerate(AP_STATE_CHECK_IDS)
        if location_id in checked_set
    )
    return {
        "ap_inventory_mask": inventory_mask,
        "ap_ledger_revision": revision,
        "ap_checked_mask": checked_mask,
        "ap_orb_pack_count": orb_pack_count,
        "ap_relic_count": relic_count,
    }


def _read_live_log(log_path: Path, offset: int) -> str:
    with log_path.open("rb") as stream:
        stream.seek(offset)
        payload = stream.read(LIVE_LOG_LIMIT + 1)
    if len(payload) > LIVE_LOG_LIMIT:
        raise SpikeError("OpenGOAL diagnostic output exceeded the bounded read limit.")
    return payload.decode("utf-8", errors="replace")


def _repl_failure_marker(output: str) -> str | None:
    return next(
        (marker for marker in REPL_FAILURE_MARKERS if marker in output),
        None,
    )


async def _live_capture(
    preset: str | None,
    opengoal_log: Path | None,
    bridge_snapshot: Path | None = None,
    *,
    reuse_attached_target: bool = False,
    expected_native_save_slot: int | None = None,
    allow_pre_staged_permanent_item: bool = False,
    require_task63_scene_active: bool = False,
    require_side_marker_capture: bool = False,
    require_side_challenge_active_capture: bool = False,
    require_side_challenge_reload_capture: bool = False,
    require_course_capture: bool = False,
    used_snapshot_keys: frozenset[str] = frozenset(),
    snapshot_provenance: dict[str, object] | None = None,
) -> dict[str, int | float]:
    repl_module = _load_project_agent_module("repl_client")
    OpenGoalRepl = repl_module.OpenGoalRepl

    if bridge_snapshot is None:
        raise SpikeError(
            "Every live capture requires a fresh, run-owned protocol bridge snapshot."
        )
    if expected_native_save_slot is None:
        raise SpikeError("Every live capture requires the run-owned native save slot.")
    if opengoal_log is None and (
        preset is None or PRESET_FORMS[preset][0] != "jetboard_launch"
    ):
        raise SpikeError("Live capture requires the paired OpenGOAL diagnostic log.")
    log_path = (
        require_safe_artifact_path(opengoal_log) if opengoal_log is not None else None
    )
    if log_path is not None and not log_path.is_file():
        raise SpikeError(f"OpenGOAL diagnostic log not found: {log_path}")
    snapshot_path = require_safe_artifact_path(bridge_snapshot)
    if not snapshot_path.is_file():
        raise SpikeError(f"Protocol bridge snapshot not found: {snapshot_path}")
    snapshot_readback = log_path is None
    if snapshot_readback and (
        preset is None or PRESET_FORMS[preset][0] != "jetboard_launch"
    ):
        raise SpikeError(
            "Protocol snapshot readback is restricted to Jetboard presets."
        )
    clean_start_capture = preset in CLEAN_START_STAGE_PRESETS
    permanent_item_capture = preset in JETBOARD_FEATURE_STAGE_PRESETS
    provenance = _validate_live_bridge_snapshot(
        snapshot_path,
        expected_native_save_slot=expected_native_save_slot,
        require_mutation_safe=(
            preset is not None
            and not clean_start_capture
            and not permanent_item_capture
            and not require_task63_scene_active
            and not require_side_marker_capture
            and not require_side_challenge_active_capture
            and not require_side_challenge_reload_capture
            and not require_course_capture
        ),
        require_permanent_item_safe=permanent_item_capture,
        allow_suspended_permanent_item=allow_pre_staged_permanent_item,
        require_clean_start_stage=clean_start_capture,
        require_task63_scene_capture=require_task63_scene_active,
        require_side_marker_capture=require_side_marker_capture,
        require_side_challenge_active_capture=require_side_challenge_active_capture,
        require_side_challenge_reload_capture=require_side_challenge_reload_capture,
        require_course_capture=require_course_capture,
    )
    if _snapshot_provenance_key(provenance) in used_snapshot_keys:
        raise SpikeError(
            "Protocol bridge snapshot revision was already consumed by this run; "
            "wait for a fresh bridge export before the next live boundary."
        )
    if snapshot_provenance is not None:
        snapshot_provenance.update(provenance)
    offset = log_path.stat().st_size if log_path is not None else 0
    repl = OpenGoalRepl()
    try:
        await repl.connect()
        if not reuse_attached_target:
            await repl.attach()
        if preset is not None:
            await repl.send_form(PRESET_FORMS[preset][2])
        if snapshot_readback:
            before = snapshot_path.read_text(encoding="utf-8", errors="replace")
            before_revision = _bridge_snapshot_value(before, "snapshot_begin")
            await repl.send_form(
                "(set! (-> *ap-runtime* test-target) "
                "(+ (if (logtest? (game-feature board) "
                "(-> *game-info* features)) 1 0) "
                "(if (logtest? (game-feature board-launch) "
                "(-> *game-info* features)) 2 0)))"
            )
            await repl.send_form("(ap-export-state!)")
            deadline = time.monotonic() + LIVE_LOG_TIMEOUT_SECONDS
            while time.monotonic() < deadline:
                snapshot = snapshot_path.read_text(encoding="utf-8", errors="replace")
                revision = _bridge_snapshot_value(snapshot, "snapshot_begin")
                if (
                    revision > before_revision
                    and _bridge_snapshot_value(snapshot, "snapshot_end") == revision
                ):
                    mask = _bridge_snapshot_value(snapshot, "test_target")
                    if mask not in {0, 1, 2, 3}:
                        raise SpikeError(
                            "Protocol snapshot Jetboard mask was outside 0..3."
                        )
                    return {"native_jetboard_mask": mask}
                await asyncio.sleep(0.05)
            raise SpikeError("Protocol bridge snapshot did not advance after export.")
        assert log_path is not None
        for query in NATIVE_QUERY_FORMS:
            await repl.send_form(query)
    finally:
        if repl.connected:
            if snapshot_readback:
                await repl.send_form("(set! (-> *ap-runtime* test-target) 0)")
            if preset is not None and PRESET_FORMS[preset][0] == "jetboard_launch":
                await repl.send_form(
                    "(set! *ap3-permanent-items-reconciliation-suspended-hook* "
                    "ap-rewards-permanent-item-reconciliation-suspended?)"
                )
            if snapshot_readback:
                await repl.send_form("(ap-export-state!)")
        await repl.close()

    assert log_path is not None
    deadline = time.monotonic() + LIVE_LOG_TIMEOUT_SECONDS
    settle_deadline: float | None = None
    output = ""
    while time.monotonic() < deadline:
        output = _read_live_log(log_path, offset)
        marker = _repl_failure_marker(output)
        if marker is not None:
            raise SpikeError(f"OpenGOAL rejected restricted capture: {marker}")
        try:
            observations = parse_native_response(output)
        except SpikeError:
            await asyncio.sleep(0.05)
            continue
        missing = NATIVE_QUERY_FIELDS - observations.keys()
        if not missing:
            if settle_deadline is None:
                settle_deadline = time.monotonic() + LIVE_STAGE_SETTLE_SECONDS
                deadline = max(deadline, settle_deadline + 0.1)
            elif time.monotonic() >= settle_deadline:
                return observations
        await asyncio.sleep(0.05)
    observations = parse_native_response(output)
    raise SpikeError(
        "OpenGOAL diagnostic output did not publish every restricted native field: "
        + ", ".join(sorted(NATIVE_QUERY_FIELDS - observations.keys()))
    )


async def _live_probe(
    probe: str,
    bridge_snapshot: Path,
    opengoal_log: Path,
    *,
    reuse_attached_target: bool = False,
    expected_native_save_slot: int,
) -> dict[str, int | float]:
    """Run one allowlisted, read-only live-state probe without recording a checkpoint."""

    if probe not in READ_ONLY_PROBE_FORMS:
        raise SpikeError(f"Unknown restricted read-only probe: {probe}")
    snapshot_path = require_safe_artifact_path(bridge_snapshot)
    log_path = require_safe_artifact_path(opengoal_log)
    if not snapshot_path.is_file():
        raise SpikeError(f"Protocol bridge snapshot not found: {snapshot_path}")
    if not log_path.is_file():
        raise SpikeError(f"OpenGOAL diagnostic log not found: {log_path}")
    _validate_live_bridge_snapshot(
        snapshot_path,
        expected_native_save_slot=expected_native_save_slot,
        require_side_marker_capture=probe == "side_marker_desb4",
    )

    repl_module = _load_project_agent_module("repl_client")
    OpenGoalRepl = repl_module.OpenGoalRepl
    offset = log_path.stat().st_size
    repl = OpenGoalRepl()
    try:
        await repl.connect()
        if not reuse_attached_target:
            await repl.attach()
        await repl.send_form(READ_ONLY_PROBE_FORMS[probe])
    finally:
        await repl.close()

    required = {
        "side_marker_available",
        "side_event_resolved",
        "side_displayed_cost",
        "side_activation_flag",
        "side_parent_shadow_closed",
        "side_parent_command_suppressed",
        "side_intro_node_closed",
        "side_intro_node_open",
        "side_resolution_node_closed",
    }
    deadline = time.monotonic() + LIVE_LOG_TIMEOUT_SECONDS
    settle_deadline: float | None = None
    output = ""
    while time.monotonic() < deadline:
        output = _read_live_log(log_path, offset)
        marker = _repl_failure_marker(output)
        if marker is not None:
            raise SpikeError(f"OpenGOAL rejected restricted probe: {marker}")
        try:
            observations = parse_native_response(output)
        except SpikeError:
            await asyncio.sleep(0.05)
            continue
        if not (required - observations.keys()):
            if settle_deadline is None:
                settle_deadline = time.monotonic() + LIVE_STAGE_SETTLE_SECONDS
                deadline = max(deadline, settle_deadline + 0.1)
            elif time.monotonic() >= settle_deadline:
                return {field: observations[field] for field in sorted(required)}
        await asyncio.sleep(0.05)
    raise SpikeError(
        "OpenGOAL diagnostic output did not publish every restricted probe field: "
        + ", ".join(sorted(required - parse_native_response(output).keys()))
    )


async def _live_stage(
    preset: str,
    bridge_snapshot: Path | None = None,
    opengoal_log: Path | None = None,
    *,
    reuse_attached_target: bool = False,
    expected_native_save_slot: int | None = None,
    used_snapshot_keys: frozenset[str] = frozenset(),
) -> dict[str, object]:
    repl_module = _load_project_agent_module("repl_client")
    OpenGoalRepl = repl_module.OpenGoalRepl

    if bridge_snapshot is None:
        raise SpikeError(
            "Every live stage requires a fresh, run-owned protocol bridge snapshot."
        )
    if expected_native_save_slot is None:
        raise SpikeError("Every live stage requires the run-owned native save slot.")
    snapshot_path = require_safe_artifact_path(bridge_snapshot)
    if not snapshot_path.is_file():
        raise SpikeError(f"Protocol bridge snapshot not found: {snapshot_path}")
    clean_start_stage = preset in CLEAN_START_STAGE_PRESETS
    restore_reconciliation = preset in JETBOARD_RECONCILIATION_RESTORE_PRESETS
    permanent_item_stage = (
        preset in JETBOARD_FEATURE_STAGE_PRESETS or restore_reconciliation
    )
    side_marker_stage = preset in SIDE_MARKER_STAGE_PRESETS
    provenance = _validate_live_bridge_snapshot(
        snapshot_path,
        expected_native_save_slot=expected_native_save_slot,
        require_mutation_safe=(
            not clean_start_stage and not permanent_item_stage and not side_marker_stage
        ),
        require_permanent_item_safe=permanent_item_stage,
        allow_suspended_permanent_item=restore_reconciliation,
        require_clean_start_stage=clean_start_stage,
        require_side_marker_capture=side_marker_stage,
    )
    if _snapshot_provenance_key(provenance) in used_snapshot_keys:
        raise SpikeError(
            "Protocol bridge snapshot revision was already consumed by this run; "
            "wait for a fresh bridge export before the next live boundary."
        )

    log_path = (
        require_safe_artifact_path(opengoal_log) if opengoal_log is not None else None
    )
    if log_path is not None and not log_path.is_file():
        raise SpikeError(f"OpenGOAL diagnostic log not found: {log_path}")
    log_offset = log_path.stat().st_size if log_path is not None else 0

    repl = OpenGoalRepl()
    try:
        await repl.connect()
        if not reuse_attached_target:
            await repl.attach()
        response = await repl.send_form(PRESET_FORMS[preset][2])
        response_output = response if isinstance(response, str) else ""
        failure_output = response_output
        marker = _repl_failure_marker(failure_output)
        if marker is not None:
            raise SpikeError(f"OpenGOAL rejected restricted preset {preset}: {marker}")
        if log_path is not None:
            deadline = time.monotonic() + LIVE_STAGE_SETTLE_SECONDS
            while time.monotonic() < deadline:
                failure_output = _read_live_log(log_path, log_offset)
                marker = _repl_failure_marker(failure_output)
                if marker is not None:
                    raise SpikeError(
                        f"OpenGOAL rejected restricted preset {preset}: {marker}"
                    )
                await asyncio.sleep(0.05)
    finally:
        await repl.close()
    return provenance


def stage_run(
    run: Path,
    preset: str,
    *,
    mutation_acknowledged: bool,
    bridge_snapshot: Path | None = None,
    opengoal_log: Path | None = None,
    reuse_attached_target: bool = False,
) -> None:
    path, state = load_state(run)
    if state["status"] != "started":
        raise SpikeError("Only a started run can apply a staging preset.")
    if not mutation_acknowledged:
        raise SpikeError("A staging preset requires mutation acknowledgement.")
    if preset not in PRESET_FORMS:
        raise SpikeError(f"Unknown restricted preset: {preset}")
    if preset in CAPTURE_ONLY_PRESETS:
        raise SpikeError(
            f"Restricted preset {preset} is capture-only and cannot be staged."
        )
    spike, checkpoint, _ = PRESET_FORMS[preset]
    if state["spike"] != spike:
        raise SpikeError("Restricted preset does not match this spike.")
    if preset in SIDE_CHALLENGE_INITIALIZATION_ORDER:
        preparations = state.get("preparations", [])
        completed = [
            preparation.get("preset")
            for preparation in preparations
            if isinstance(preparation, Mapping)
            and preparation.get("preset") in SIDE_CHALLENGE_INITIALIZATION_ORDER
        ]
        expected = list(SIDE_CHALLENGE_INITIALIZATION_ORDER[: len(completed)])
        if completed != expected or len(completed) >= len(
            SIDE_CHALLENGE_INITIALIZATION_ORDER
        ):
            raise SpikeError(
                "Side-challenge initialization history is not an exact unfinished "
                "prefix; start a fresh correlation."
            )
        required = SIDE_CHALLENGE_INITIALIZATION_ORDER[len(completed)]
        if preset != required:
            raise SpikeError(
                f"Side-challenge initialization requires {required} next; got {preset}."
            )
    if bridge_snapshot is None:
        raise SpikeError("Live staging requires --bridge-snapshot.")
    provenance = asyncio.run(
        _live_stage(
            preset,
            bridge_snapshot,
            opengoal_log,
            reuse_attached_target=reuse_attached_target,
            expected_native_save_slot=int(state["disposable_save_slot"]),
            used_snapshot_keys=_used_snapshot_keys(state),
        )
    )
    _record_snapshot_use(state, provenance, boundary=f"stage:{preset}")
    state.setdefault("preparations", []).append(
        {
            "staged_utc": utc_now(),
            "preset": preset,
            "checkpoint": checkpoint,
            "bridge_snapshot": provenance,
        }
    )
    _record_event(
        state,
        "feasibility.spike.checkpoint",
        {
            "spike": spike,
            "checkpoint": checkpoint,
            "status": "staged",
            **provenance,
        },
    )
    save_state(path, state)


def _bridge_snapshot_value(snapshot: str, field: str) -> int:
    match = re.search(rf"(?m)^{re.escape(field)} (-?\d+)$", snapshot)
    if match is None:
        raise SpikeError(f"Protocol bridge snapshot omitted {field}.")
    return int(match.group(1))


def _bridge_snapshot_text(snapshot: str, field: str) -> str:
    match = re.search(rf"(?m)^{re.escape(field)} ([^\r\n]+)$", snapshot)
    if match is None:
        raise SpikeError(f"Protocol bridge snapshot omitted {field}.")
    return match.group(1)


def _snapshot_provenance_key(provenance: Mapping[str, object]) -> str:
    revision = provenance.get("bridge_snapshot_revision")
    digest = provenance.get("bridge_snapshot_sha256")
    if isinstance(revision, bool) or not isinstance(revision, int):
        raise SpikeError("Bridge snapshot provenance omitted an integer revision.")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise SpikeError("Bridge snapshot provenance omitted a SHA-256 digest.")
    return f"{revision}:{digest}"


def _used_snapshot_keys(state: Mapping[str, Any]) -> frozenset[str]:
    uses = state.get("bridge_snapshot_uses", [])
    if not isinstance(uses, list):
        raise SpikeError("Bridge snapshot provenance list is malformed.")
    keys: set[str] = set()
    for use in uses:
        if not isinstance(use, Mapping):
            raise SpikeError("Bridge snapshot provenance entry is malformed.")
        keys.add(_snapshot_provenance_key(use))
    return frozenset(keys)


def _record_snapshot_use(
    state: dict[str, Any], provenance: Mapping[str, object], *, boundary: str
) -> None:
    key = _snapshot_provenance_key(provenance)
    if key in _used_snapshot_keys(state):
        raise SpikeError(
            "Protocol bridge snapshot revision was already consumed by this run."
        )
    state.setdefault("bridge_snapshot_uses", []).append(
        {**provenance, "boundary": boundary, "consumed_utc": utc_now()}
    )


def _validate_live_bridge_snapshot(
    snapshot_path: Path,
    *,
    expected_native_save_slot: int | None = None,
    require_mutation_safe: bool = False,
    require_permanent_item_safe: bool = False,
    allow_suspended_permanent_item: bool = False,
    require_clean_start_stage: bool = False,
    require_task63_scene_capture: bool = False,
    require_side_marker_capture: bool = False,
    require_side_challenge_active_capture: bool = False,
    require_side_challenge_reload_capture: bool = False,
    require_course_capture: bool = False,
) -> dict[str, object]:
    if allow_suspended_permanent_item and not require_permanent_item_safe:
        raise SpikeError(
            "A suspended permanent-item boundary is valid only for a "
            "permanent-item capture."
        )
    if (
        sum(
            (
                require_mutation_safe,
                require_permanent_item_safe,
                require_clean_start_stage,
                require_task63_scene_capture,
                require_side_marker_capture,
                require_side_challenge_active_capture,
                require_side_challenge_reload_capture,
                require_course_capture,
            )
        )
        > 1
    ):
        raise SpikeError("Live bridge validation modes are mutually exclusive.")
    specialized_boundary = any(
        (
            require_clean_start_stage,
            require_permanent_item_safe,
            require_task63_scene_capture,
            require_side_marker_capture,
            require_side_challenge_active_capture,
            require_side_challenge_reload_capture,
            require_course_capture,
        )
    )
    if specialized_boundary and expected_native_save_slot is None:
        raise SpikeError(
            "Specialized live bridge validation requires the run-owned native "
            "save slot."
        )
    age = time.time() - snapshot_path.stat().st_mtime
    if age < -1.0 or age > LIVE_SNAPSHOT_MAX_AGE_SECONDS:
        raise SpikeError(
            "Protocol bridge snapshot is not live "
            f"(age {age:.1f}s; maximum {LIVE_SNAPSHOT_MAX_AGE_SECONDS:.1f}s)."
        )
    snapshot_bytes = snapshot_path.read_bytes()
    snapshot = (
        snapshot_bytes.decode("utf-8", errors="replace")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )
    begin = _bridge_snapshot_value(snapshot, "snapshot_begin")
    if _bridge_snapshot_value(snapshot, "snapshot_end") != begin:
        raise SpikeError(
            "Protocol bridge snapshot revision is internally inconsistent."
        )
    for field in ("connection_ready", "game_running", "source_loaded"):
        if _bridge_snapshot_value(snapshot, field) != 1:
            raise SpikeError(f"Protocol bridge snapshot requires {field}=1.")
    if expected_native_save_slot is not None:
        actual_slot = _bridge_snapshot_value(snapshot, "native_save_slot")
        if actual_slot != expected_native_save_slot:
            raise SpikeError(
                "Protocol bridge snapshot belongs to native save slot "
                f"{actual_slot}, but this run requires {expected_native_save_slot}."
            )
    if require_mutation_safe:
        for field in (
            "at_title_menu",
            "loading",
            "in_cutscene",
            "dying_or_dead",
            "mission_restarting",
            "level_transition",
            "in_vehicle",
        ):
            if _bridge_snapshot_value(snapshot, field) != 0:
                raise SpikeError(
                    f"Protocol bridge snapshot is unsafe for staging: {field}=1."
                )
        if _bridge_snapshot_value(snapshot, "safe_to_mutate_mission_state") != 1:
            raise SpikeError(
                "Protocol bridge snapshot requires "
                "safe_to_mutate_mission_state=1 for staging."
            )
    if require_permanent_item_safe:
        for field in (
            "at_title_menu",
            "loading",
            "in_cutscene",
            "dying_or_dead",
            "mission_restarting",
            "level_transition",
            "in_vehicle",
        ):
            if _bridge_snapshot_value(snapshot, field) != 0:
                raise SpikeError(
                    "Protocol bridge snapshot is unsafe for permanent-item "
                    f"staging: {field}=1."
                )
        for field in ("save_loaded", "ap_state_loaded", "ap_state_bound"):
            if _bridge_snapshot_value(snapshot, field) != 1:
                raise SpikeError(f"Permanent-item staging requires exact {field}=1.")
        permanent_safe = _bridge_snapshot_value(
            snapshot, "safe_to_apply_permanent_item"
        )
        runner_suspended = (
            allow_suspended_permanent_item
            and permanent_safe == 0
            and _bridge_snapshot_value(snapshot, "permanent_item_native_target_mask")
            == -1
        )
        if permanent_safe != 1 and not runner_suspended:
            raise SpikeError(
                "Protocol bridge snapshot requires "
                "safe_to_apply_permanent_item=1, or an exact runner-owned "
                "suspended boundary, for permanent-item staging."
            )
    if require_clean_start_stage:
        for field in (
            "at_title_menu",
            "loading",
            "in_cutscene",
            "dying_or_dead",
            "mission_restarting",
            "level_transition",
            "in_vehicle",
        ):
            if _bridge_snapshot_value(snapshot, field) != 0:
                raise SpikeError(
                    "Protocol bridge snapshot is unsafe for clean-start "
                    f"relocation: {field}=1."
                )
        exact_values = {
            "save_loaded": 1,
            "ap_state_loaded": 1,
            "ap_state_bound": 1,
            "current_act": 1,
            "current_task": 10,
            "current_task_node": 8,
            "permanent_item_native_target_mask": 0,
            "safe_to_mutate_mission_state": 0,
        }
        for field, expected in exact_values.items():
            actual = _bridge_snapshot_value(snapshot, field)
            if actual != expected:
                raise SpikeError(
                    "Clean-start relocation requires exact "
                    f"{field}={expected}, got {actual}."
                )
        if _bridge_snapshot_text(snapshot, "current_level") != "wasstada":
            raise SpikeError("Clean-start relocation requires current_level=wasstada.")
    if require_task63_scene_capture:
        for field in (
            "at_title_menu",
            "loading",
            "dying_or_dead",
            "mission_restarting",
            "level_transition",
            "in_vehicle",
        ):
            if _bridge_snapshot_value(snapshot, field) != 0:
                raise SpikeError(
                    "Protocol bridge snapshot is unsafe for task-63 capture: "
                    f"{field}=1."
                )
        exact_values = {
            "save_loaded": 1,
            "ap_state_loaded": 1,
            "ap_state_bound": 1,
            "in_cutscene": 1,
            "current_task": -1,
            "current_task_node": -1,
            "permanent_item_native_target_mask": 0,
            "safe_to_mutate_mission_state": 0,
        }
        for field, expected in exact_values.items():
            actual = _bridge_snapshot_value(snapshot, field)
            if actual != expected:
                raise SpikeError(
                    "Task-63 capture requires exact active-scene "
                    f"{field}={expected}, got {actual}."
                )
        if _bridge_snapshot_text(snapshot, "current_level") != "foresta":
            raise SpikeError("Task-63 capture requires current_level=foresta.")
    if require_side_marker_capture:
        for field in (
            "at_title_menu",
            "loading",
            "in_cutscene",
            "dying_or_dead",
            "mission_restarting",
            "level_transition",
            "in_vehicle",
        ):
            if _bridge_snapshot_value(snapshot, field) != 0:
                raise SpikeError(
                    "Protocol bridge snapshot is unsafe for side-marker capture: "
                    f"{field}=1."
                )
        exact_values = {
            "save_loaded": 1,
            "ap_state_loaded": 1,
            "ap_state_bound": 1,
            "current_task": -1,
            "current_task_node": -1,
            "permanent_item_native_target_mask": 0,
            "safe_to_mutate_mission_state": 0,
        }
        for field, expected in exact_values.items():
            actual = _bridge_snapshot_value(snapshot, field)
            if actual != expected:
                raise SpikeError(
                    "Side-marker capture requires exact "
                    f"{field}={expected}, got {actual}."
                )
        if _bridge_snapshot_text(snapshot, "current_level") != "desert":
            raise SpikeError("Side-marker capture requires current_level=desert.")
    if require_side_challenge_active_capture:
        for field in (
            "at_title_menu",
            "loading",
            "in_cutscene",
            "dying_or_dead",
            "mission_restarting",
            "level_transition",
            "in_vehicle",
        ):
            if _bridge_snapshot_value(snapshot, field) != 0:
                raise SpikeError(
                    "Protocol bridge snapshot is unsafe for active "
                    f"side-challenge capture: {field}=1."
                )
        exact_values = {
            "save_loaded": 1,
            "ap_state_loaded": 1,
            "ap_state_bound": 1,
            "current_task": 137,
            "current_task_node": 409,
            "permanent_item_native_target_mask": 0,
            "safe_to_mutate_mission_state": 0,
        }
        for field, expected in exact_values.items():
            actual = _bridge_snapshot_value(snapshot, field)
            if actual != expected:
                raise SpikeError(
                    "Active side-challenge capture requires exact "
                    f"{field}={expected}, got {actual}."
                )
        if _bridge_snapshot_text(snapshot, "current_level") != "desert":
            raise SpikeError(
                "Active side-challenge capture requires current_level=desert."
            )
    if require_side_challenge_reload_capture:
        for field in (
            "at_title_menu",
            "loading",
            "in_cutscene",
            "dying_or_dead",
            "mission_restarting",
            "level_transition",
        ):
            if _bridge_snapshot_value(snapshot, field) != 0:
                raise SpikeError(
                    f"Reloaded side-challenge capture is unsafe: {field}=1."
                )
        exact_values = {
            "save_loaded": 1,
            "ap_state_loaded": 1,
            "ap_state_bound": 1,
            "safe_to_mutate_mission_state": 0,
        }
        for field, expected in exact_values.items():
            actual = _bridge_snapshot_value(snapshot, field)
            if actual != expected:
                raise SpikeError(
                    "Reloaded side-challenge capture requires exact "
                    f"{field}={expected}, got {actual}."
                )
        if _bridge_snapshot_text(snapshot, "current_level") != "desert":
            raise SpikeError(
                "Reloaded side-challenge capture requires current_level=desert."
            )
    if require_course_capture:
        for field in (
            "at_title_menu",
            "loading",
            "in_cutscene",
            "dying_or_dead",
            "mission_restarting",
            "level_transition",
        ):
            if _bridge_snapshot_value(snapshot, field) != 0:
                raise SpikeError(f"Course-access capture is unsafe: {field}=1.")
        exact_values = {
            "save_loaded": 1,
            "ap_state_loaded": 1,
            "ap_state_bound": 1,
        }
        for field, expected in exact_values.items():
            actual = _bridge_snapshot_value(snapshot, field)
            if actual != expected:
                raise SpikeError(
                    "Course-access capture requires exact "
                    f"{field}={expected}, got {actual}."
                )
    return {
        "bridge_snapshot_sha256": hashlib.sha256(snapshot_bytes).hexdigest(),
        "bridge_snapshot_revision": begin,
        "bridge_snapshot_native_slot": _bridge_snapshot_value(
            snapshot, "native_save_slot"
        ),
        "bridge_snapshot_age_ms": max(0, int(age * 1000)),
    }


def capture_checkpoint(
    run: Path,
    checkpoint: str,
    assertions: Mapping[str, str],
    observations: Mapping[str, int | float],
    *,
    save_generation: int,
    live: bool,
    preset: str | None,
    mutation_acknowledged: bool,
    opengoal_log: Path | None = None,
    bridge_snapshot: Path | None = None,
    ap_state: Path | None = None,
    reuse_attached_target: bool = False,
) -> dict[str, Any]:
    path, state = load_state(run)
    if state["status"] != "started":
        raise SpikeError("Only a started run can capture checkpoints.")
    spike = str(state["spike"])
    if checkpoint not in SPIKES[spike]:
        raise SpikeError(f"Checkpoint {checkpoint!r} is not defined for {spike}.")
    required_assertions = set(SPIKES[spike][checkpoint])
    unknown_assertions = set(assertions) - required_assertions
    if unknown_assertions:
        raise SpikeError(
            "Assertions are not defined for "
            f"{spike}/{checkpoint}: {sorted(unknown_assertions)}"
        )
    if live and spike in {"task_30_shadow", "task_63_viewer"}:
        missing_assertions = required_assertions - assertions.keys()
        if missing_assertions:
            raise SpikeError(
                "Live shadow-state capture omitted required procedure assertions "
                f"before mutation: {sorted(missing_assertions)}"
            )
    checkpoints = state.get("checkpoints")
    if not isinstance(checkpoints, dict):
        raise SpikeError("Spike checkpoints are not mutable state.")
    if checkpoint in checkpoints:
        raise SpikeError(
            f"Checkpoint {checkpoint!r} is already captured; start a successor "
            "run with a new correlation ID instead of overwriting evidence."
        )
    if save_generation < 0:
        raise SpikeError("Save generation must be non-negative.")
    if reuse_attached_target and not live:
        raise SpikeError("Reusing an attached target requires --live.")
    if live and bridge_snapshot is None:
        raise SpikeError("Every live checkpoint requires --bridge-snapshot.")
    if preset is not None:
        if preset not in PRESET_FORMS:
            raise SpikeError(f"Unknown restricted preset: {preset}")
        expected_spike, expected_checkpoint, _ = PRESET_FORMS[preset]
        if (spike, checkpoint) != (expected_spike, expected_checkpoint):
            raise SpikeError("Restricted preset does not match this spike/checkpoint.")
        if preset in STAGE_ONLY_PRESETS:
            raise SpikeError(
                f"Restricted preset {preset} is stage-only and cannot capture "
                "a checkpoint."
            )
        if not live or not mutation_acknowledged:
            raise SpikeError(
                "A live preset requires --live and mutation acknowledgement."
            )
    if spike in AP_STATE_LIVE_SPIKES and live:
        if ap_state is None or bridge_snapshot is None:
            raise SpikeError(
                f"Live {spike.replace('_', '-')} capture requires --ap-state and "
                "--bridge-snapshot."
            )
        if spike == "native_reconstruction":
            derived_fields = AP_STATE_OBSERVATION_FIELDS
        elif spike == "orb_600":
            derived_fields = frozenset({"ap_orb_pack_count"})
        elif spike == "haven_task_35":
            derived_fields = frozenset({"ap_checked_mask", "ap_inventory_mask"})
        else:
            derived_fields = frozenset({"ap_checked_mask", "ap_relic_count"})
        supplied_ap_fields = derived_fields & observations.keys()
        if supplied_ap_fields:
            raise SpikeError(
                f"Live {spike.replace('_', '-')} AP observations are derived from the "
                "checksummed state file, not supplied manually: "
                f"{sorted(supplied_ap_fields)}"
            )
    elif ap_state is not None:
        raise SpikeError(
            "--ap-state is restricted to a live state-backed feasibility capture."
        )

    combined = dict(observations)
    snapshot_provenance: dict[str, object] = {}
    if live:
        preparations = state.get("preparations")
        last_preparation = (
            preparations[-1]
            if isinstance(preparations, list) and preparations
            else None
        )
        allow_pre_staged_permanent_item = (
            preset in JETBOARD_FEATURE_STAGE_PRESETS
            and isinstance(last_preparation, Mapping)
            and last_preparation.get("preset") == preset
            and last_preparation.get("checkpoint") == checkpoint
        )
        combined.update(
            asyncio.run(
                _live_capture(
                    preset,
                    opengoal_log,
                    bridge_snapshot,
                    reuse_attached_target=reuse_attached_target,
                    expected_native_save_slot=int(state["disposable_save_slot"]),
                    allow_pre_staged_permanent_item=(allow_pre_staged_permanent_item),
                    require_task63_scene_active=spike == "task_63_viewer",
                    require_side_marker_capture=(
                        preset in SIDE_MARKER_CAPTURE_PRESETS
                        if preset is not None
                        else False
                    ),
                    require_side_challenge_active_capture=(
                        preset in SIDE_CHALLENGE_ACTIVE_CAPTURE_PRESETS
                        if preset is not None
                        else False
                    ),
                    require_side_challenge_reload_capture=(
                        preset in SIDE_CHALLENGE_RELOAD_CAPTURE_PRESETS
                        if preset is not None
                        else False
                    ),
                    require_course_capture=(
                        preset in COURSE_CAPTURE_PRESETS
                        if preset is not None
                        else False
                    ),
                    used_snapshot_keys=_used_snapshot_keys(state),
                    snapshot_provenance=snapshot_provenance,
                )
            )
        )
        if not snapshot_provenance:
            raise SpikeError(
                "Live capture did not return validated bridge snapshot provenance."
            )
        if spike in AP_STATE_LIVE_SPIKES:
            assert ap_state is not None
            assert bridge_snapshot is not None
            state_observations = _ap_state_observations(
                ap_state,
                bridge_snapshot,
                expected_native_save_slot=int(state["disposable_save_slot"]),
            )
            if spike == "native_reconstruction":
                combined.update(state_observations)
            elif spike == "orb_600":
                combined["ap_orb_pack_count"] = state_observations["ap_orb_pack_count"]
            elif spike == "haven_task_35":
                combined.update(
                    {
                        "ap_checked_mask": state_observations["ap_checked_mask"],
                        "ap_inventory_mask": state_observations["ap_inventory_mask"],
                    }
                )
            else:
                combined.update(
                    {
                        "ap_checked_mask": state_observations["ap_checked_mask"],
                        "ap_relic_count": state_observations["ap_relic_count"],
                    }
                )
    if spike == "native_reconstruction":
        missing_observations = (
            NATIVE_RECONSTRUCTION_OBSERVATION_FIELDS - combined.keys()
        )
        if missing_observations:
            raise SpikeError(
                "Native-reconstruction checkpoint omitted required typed "
                f"observations: {sorted(missing_observations)}"
            )
    if live:
        _record_snapshot_use(
            state,
            snapshot_provenance,
            boundary=f"capture:{checkpoint}",
        )
    record = {
        "captured_utc": utc_now(),
        "save_generation": save_generation,
        "observations": combined,
        "assertions": dict(assertions),
    }
    if live:
        record["bridge_snapshot"] = dict(snapshot_provenance)
    checkpoints[checkpoint] = record
    automatic_reasons = _observation_reasons(state)
    record["automatic_validation"] = {
        "status": "blocked" if automatic_reasons else "pass",
        "reasons": automatic_reasons,
    }
    checkpoint_context: dict[str, object] = {
        "spike": spike,
        "checkpoint": checkpoint,
        "status": "blocked" if automatic_reasons else "captured",
        "save_generation": save_generation,
        **combined,
    }
    if automatic_reasons:
        checkpoint_context["reason"] = "; ".join(automatic_reasons)
    if live:
        checkpoint_context.update(snapshot_provenance)
    _record_event(state, "feasibility.spike.checkpoint", checkpoint_context)
    for name, status in assertions.items():
        _record_event(
            state,
            "feasibility.spike.assertion",
            {
                "spike": spike,
                "checkpoint": checkpoint,
                "assertion": name,
                "status": status,
                "expected": "pass",
                "actual": status,
                "save_generation": save_generation,
            },
        )
    save_state(path, state)
    if live and automatic_reasons:
        raise SpikeError(
            "Checkpoint was preserved as BLOCKED evidence and live testing must "
            "stop: " + "; ".join(automatic_reasons)
        )
    return record


def _observation_reasons(state: Mapping[str, Any]) -> list[str]:
    spike = str(state["spike"])
    checkpoints = state.get("checkpoints", {})
    reasons: list[str] = []
    if not isinstance(checkpoints, Mapping):
        return ["checkpoints are not a mapping"]

    for checkpoint in SPIKES[spike]:
        record = checkpoints.get(checkpoint)
        if not isinstance(record, Mapping):
            continue
        observations = record.get("observations", {})
        if not isinstance(observations, Mapping):
            reasons.append(f"{checkpoint}/observations=invalid")
            continue
        for field in REQUIRED_OBSERVATIONS.get(spike, ()):
            if field not in observations:
                reasons.append(f"{checkpoint}/{field}=missing")
        for field in REQUIRED_CHECKPOINT_OBSERVATIONS.get((spike, checkpoint), ()):
            if field not in observations:
                reasons.append(f"{checkpoint}/{field}=missing")
        for field, expected in EXPECTED_OBSERVATIONS.get(
            (spike, checkpoint), {}
        ).items():
            actual = observations.get(field)
            if actual is None:
                reasons.append(f"{checkpoint}/{field}=missing (expected {expected})")
            elif actual != expected:
                reasons.append(f"{checkpoint}/{field}={actual} (expected {expected})")

    if spike in {"task_30_shadow", "task_63_viewer"}:
        for field in ("ap_relic_count", "ap_checked_mask"):
            values = {
                record.get("observations", {}).get(field)
                for record in checkpoints.values()
                if isinstance(record, Mapping)
                and isinstance(record.get("observations"), Mapping)
                and field in record.get("observations", {})
            }
            if len(values) > 1:
                reasons.append(f"{field} changed across checkpoints: {sorted(values)}")
    if spike == "orb_600":
        record = checkpoints.get("at_600")
        observations = (
            record.get("observations", {}) if isinstance(record, Mapping) else {}
        )
        if isinstance(observations, Mapping):
            family_values: list[int] = []
            for field in ORB_SOURCE_FAMILY_FIELDS:
                value = observations.get(field)
                if value is None:
                    continue
                if isinstance(value, bool) or not isinstance(value, int):
                    reasons.append(f"at_600/{field}={value} (expected integer count)")
                    continue
                if value < 0 or value > 600:
                    reasons.append(f"at_600/{field}={value} (expected 0..600)")
                    continue
                family_values.append(value)
            if len(family_values) == len(ORB_SOURCE_FAMILY_FIELDS):
                local_total = observations.get("local_orb_earned_count")
                family_total = sum(family_values)
                if family_total != local_total:
                    reasons.append(
                        "at_600/source_family_total="
                        f"{family_total} (local_orb_earned_count={local_total})"
                    )
    if spike == "side_challenges":
        for field in (
            "ap_checked_mask",
            "ap_relic_count",
            "native_purchase_secrets",
        ):
            values = {
                record.get("observations", {}).get(field)
                for record in checkpoints.values()
                if isinstance(record, Mapping)
                and isinstance(record.get("observations"), Mapping)
                and field in record.get("observations", {})
            }
            if len(values) > 1:
                reasons.append(f"{field} changed across checkpoints: {sorted(values)}")
    return reasons


def _decision_blockers(state: Mapping[str, Any]) -> list[str]:
    if state.get("spike") != "native_reconstruction":
        return []
    checkpoints = state.get("checkpoints", {})
    if not isinstance(checkpoints, Mapping):
        return ["native reconstruction checkpoints are missing"]
    records = {
        name: checkpoints.get(name, {}) for name in SPIKES["native_reconstruction"]
    }
    if not all(isinstance(value, Mapping) for value in records.values()):
        return ["native reconstruction comparison is incomplete"]
    observations = {
        name: record.get("observations", {}) for name, record in records.items()
    }
    if not all(isinstance(value, Mapping) for value in observations.values()):
        return ["native reconstruction observations are incomplete"]

    blockers: list[str] = []
    before_obs = observations["before_save"]
    ledger_values = {
        checkpoint.get("ap_inventory_mask") for checkpoint in observations.values()
    }
    if None in ledger_values:
        blockers.append(
            "AP inventory target is missing from a reconstruction checkpoint"
        )
    elif len(ledger_values) > 1:
        blockers.append(
            f"AP inventory changed during reconstruction: {sorted(ledger_values)}"
        )

    baseline_checks = before_obs.get("ap_checked_mask")
    for name, checkpoint in observations.items():
        actual_checks = checkpoint.get("ap_checked_mask")
        if baseline_checks is not None and actual_checks != baseline_checks:
            blockers.append(
                f"{name}/ap_checked_mask leaked: before={baseline_checks}, "
                f"observed={actual_checks}"
            )

    stable_fields = (
        "native_items",
        "native_non_ap_feature_mask",
        "native_reward_mask",
        "native_task_mask",
        "native_mission_mask",
    )
    repaired_checkpoints = (
        "after_game_restart",
        "after_ap_reconcile",
        "after_item_replay",
    )
    expected_target = before_obs.get("ap_inventory_mask")
    for name in repaired_checkpoints:
        checkpoint = observations[name]
        for field in stable_fields:
            baseline = before_obs.get(field)
            actual = checkpoint.get(field)
            if baseline is not None and actual != baseline:
                blockers.append(
                    f"{name}/{field} leaked: before={baseline}, observed={actual}"
                )
        native_target = checkpoint.get("native_permanent_target_mask")
        if expected_target is not None and native_target != expected_target:
            blockers.append(
                f"{name}/native_permanent_target_mask={native_target} "
                f"(AP ledger target {expected_target})"
            )
    return blockers


def _haven_fallback_blockers(state: Mapping[str, Any]) -> list[str]:
    """Require a decisive no-DONE(34) failure before selecting the fallback."""

    checkpoints = state.get("checkpoints")
    if not isinstance(checkpoints, Mapping):
        return ["Haven fallback checkpoints are missing"]
    required = ("before_entry", "mission_start")
    records: dict[str, Mapping[str, Any]] = {}
    for name in required:
        record = checkpoints.get(name)
        if not isinstance(record, Mapping):
            return [
                "Haven fallback requires before_entry and mission_start checkpoints"
            ]
        records[name] = record
    observations = {
        name: record.get("observations", {}) for name, record in records.items()
    }
    assertions = {
        name: record.get("assertions", {}) for name, record in records.items()
    }
    if not all(isinstance(value, Mapping) for value in observations.values()):
        return ["Haven fallback observations are incomplete"]
    if not all(isinstance(value, Mapping) for value in assertions.values()):
        return ["Haven fallback assertions are incomplete"]

    blockers: list[str] = []
    before = observations["before_entry"]
    mission = observations["mission_start"]
    for name, checkpoint in observations.items():
        for field in ("native_task_mask", "native_mission_mask"):
            if checkpoint.get(field) != 0:
                blockers.append(
                    f"{name}/{field}={checkpoint.get(field)} "
                    "(independent candidate requires 0)"
                )
    loaded_levels = mission.get("native_loaded_level_mask")
    if not isinstance(loaded_levels, (int, float)) or int(loaded_levels) & 1 == 0:
        blockers.append(
            "mission_start did not prove the ctygenb candidate level active"
        )
    actor_mask = mission.get("native_actor_mask")
    if isinstance(actor_mask, (int, float)) and int(actor_mask) & 3 == 3:
        blockers.append(
            "required Haven actors were present; fallback failure not proven"
        )
    elif not isinstance(actor_mask, (int, float)):
        blockers.append("mission_start/native_actor_mask is missing")
    if assertions["mission_start"].get("geometry_playable") != "pass":
        blockers.append(
            "mission_start/geometry_playable must pass before actor absence "
            "can select the fallback"
        )
    if assertions["mission_start"].get("required_actors_present") not in {
        "fail",
        "blocked",
    }:
        blockers.append(
            "mission_start/required_actors_present must agree with the missing actor mask"
        )
    for field in (
        "ap_checked_mask",
        "ap_inventory_mask",
        "native_items",
        "native_reward_mask",
    ):
        baseline = before.get(field)
        observed = mission.get(field)
        if baseline is None or observed is None:
            blockers.append(f"Haven fallback control {field} is missing")
        elif observed != baseline:
            blockers.append(
                f"Haven fallback changed {field}: before={baseline}, mission={observed}"
            )
    return blockers


def _safe_fallback_blockers(state: Mapping[str, Any]) -> list[str]:
    spike = str(state.get("spike"))
    if spike == "haven_task_35":
        return _haven_fallback_blockers(state)
    return [
        f"{spike} has no implemented positive fallback-proof validator; "
        "finish the run BLOCKED instead"
    ]


def _acceptance_provenance_blockers(state: Mapping[str, Any]) -> list[str]:
    """Require one validated live snapshot for every recorded runtime boundary."""

    expected_slot = state.get("disposable_save_slot")
    if isinstance(expected_slot, bool) or not isinstance(expected_slot, int):
        return ["acceptance provenance omitted the disposable native save slot"]

    checkpoints = state.get("checkpoints")
    preparations = state.get("preparations", [])
    uses = state.get("bridge_snapshot_uses")
    blockers: list[str] = []
    if not isinstance(checkpoints, Mapping):
        return ["acceptance provenance checkpoints are not a mapping"]
    if not isinstance(preparations, list):
        blockers.append("acceptance provenance preparations are not a list")
        preparations = []
    if not isinstance(uses, list):
        blockers.append("acceptance provenance ledger is not a list")
        uses = []

    ledger: dict[str, Mapping[str, object]] = {}
    provenance_keys: set[str] = set()
    for index, use in enumerate(uses):
        if not isinstance(use, Mapping):
            blockers.append(f"acceptance provenance ledger entry {index} is malformed")
            continue
        boundary = use.get("boundary")
        if not isinstance(boundary, str) or not boundary:
            blockers.append(
                f"acceptance provenance ledger entry {index} omitted its boundary"
            )
            continue
        if boundary in ledger:
            blockers.append(f"acceptance provenance boundary {boundary} is duplicated")
        try:
            key = _snapshot_provenance_key(use)
        except SpikeError as exc:
            blockers.append(f"acceptance provenance {boundary}: {exc}")
            continue
        if key in provenance_keys:
            blockers.append(
                f"acceptance provenance snapshot {key} was consumed more than once"
            )
        provenance_keys.add(key)
        ledger[boundary] = use

    expected_boundaries: dict[str, Mapping[str, object]] = {}
    for checkpoint, record in checkpoints.items():
        boundary = f"capture:{checkpoint}"
        if not isinstance(record, Mapping):
            blockers.append(f"{boundary} record is malformed")
            continue
        provenance = record.get("bridge_snapshot")
        if not isinstance(provenance, Mapping):
            blockers.append(f"{boundary} lacks live bridge-snapshot provenance")
            continue
        expected_boundaries[boundary] = provenance

    for index, preparation in enumerate(preparations):
        if not isinstance(preparation, Mapping):
            blockers.append(f"stage preparation {index} is malformed")
            continue
        preset = preparation.get("preset")
        provenance = preparation.get("bridge_snapshot")
        if not isinstance(preset, str) or not preset:
            blockers.append(f"stage preparation {index} omitted its preset")
            continue
        boundary = f"stage:{preset}"
        if boundary in expected_boundaries:
            blockers.append(f"acceptance provenance boundary {boundary} is duplicated")
            continue
        if not isinstance(provenance, Mapping):
            blockers.append(f"{boundary} lacks live bridge-snapshot provenance")
            continue
        expected_boundaries[boundary] = provenance

    for boundary, provenance in expected_boundaries.items():
        use = ledger.get(boundary)
        if use is None:
            blockers.append(f"{boundary} is absent from the snapshot-use ledger")
            continue
        try:
            expected_key = _snapshot_provenance_key(provenance)
            actual_key = _snapshot_provenance_key(use)
        except SpikeError as exc:
            blockers.append(f"acceptance provenance {boundary}: {exc}")
            continue
        if actual_key != expected_key:
            blockers.append(f"{boundary} snapshot does not match its ledger entry")
        for field in (
            "bridge_snapshot_native_slot",
            "bridge_snapshot_age_ms",
        ):
            if use.get(field) != provenance.get(field):
                blockers.append(f"{boundary} {field} does not match its ledger entry")
        slot = provenance.get("bridge_snapshot_native_slot")
        if slot != expected_slot:
            blockers.append(
                f"{boundary} belongs to native save slot {slot}; expected {expected_slot}"
            )
        age_ms = provenance.get("bridge_snapshot_age_ms")
        if (
            isinstance(age_ms, bool)
            or not isinstance(age_ms, int)
            or age_ms < 0
            or age_ms > int(LIVE_SNAPSHOT_MAX_AGE_SECONDS * 1000)
        ):
            blockers.append(
                f"{boundary} bridge snapshot age {age_ms}ms is outside the live limit"
            )

    unexpected = sorted(set(ledger) - set(expected_boundaries))
    blockers.extend(
        f"acceptance provenance ledger has unexpected boundary {boundary}"
        for boundary in unexpected
    )
    if not expected_boundaries:
        blockers.append("acceptance evidence contains no live runtime boundaries")
    return blockers


def evaluate_run(state: Mapping[str, Any]) -> tuple[str, list[str]]:
    spike = str(state["spike"])
    checkpoints = state.get("checkpoints", {})
    reasons: list[str] = []
    for checkpoint, required_assertions in SPIKES[spike].items():
        record = checkpoints.get(checkpoint)
        if not isinstance(record, Mapping):
            reasons.append(f"missing checkpoint {checkpoint}")
            continue
        assertions = record.get("assertions", {})
        for assertion in required_assertions:
            status = (
                assertions.get(assertion) if isinstance(assertions, Mapping) else None
            )
            if status != "pass":
                reasons.append(f"{checkpoint}/{assertion}={status or 'missing'}")
    reasons.extend(_observation_reasons(state))
    return ("pass", []) if not reasons else ("blocked", reasons)


def finish_run(run: Path, decision: str | None = None) -> tuple[str, list[str]]:
    path, state = load_state(run)
    if state["status"] != "started":
        raise SpikeError("Only a started run can be finished.")
    evidence_status, reasons = evaluate_run(state)
    decision_blockers = _decision_blockers(state)
    positive_candidate = decision in {"pass", "safe_fallback"} or (
        decision is None and evidence_status == "pass" and not decision_blockers
    )
    provenance_blockers = (
        _acceptance_provenance_blockers(state) if positive_candidate else []
    )
    decision_blockers.extend(provenance_blockers)
    selected = decision or (
        "pass" if evidence_status == "pass" and not decision_blockers else "blocked"
    )
    if selected not in DECISIONS:
        raise SpikeError(f"Unknown feasibility decision: {selected}")
    if selected == "pass" and (evidence_status != "pass" or decision_blockers):
        detail = "; ".join([*reasons, *decision_blockers])
        raise SpikeError(
            "A PASS decision requires a complete, consistent matrix without "
            f"automatic decision blockers: {detail}"
        )
    if selected == "safe_fallback":
        if state["spike"] not in SAFE_FALLBACK_SPIKES:
            raise SpikeError("This spike has no predefined safe fallback.")
        fallback_blockers = _safe_fallback_blockers(state)
        fallback_blockers.extend(provenance_blockers)
        if fallback_blockers:
            raise SpikeError(
                "SAFE FALLBACK evidence is inconsistent: "
                + "; ".join(fallback_blockers)
            )
        state["fallback"] = {
            "name": "haven_done34_convergence",
            "production_gate": "Haven City Access + DONE(34) + Jetboard + RANGED",
            "implementation_milestones": [18, 19],
        }
    state["status"] = FINALIZED_PENDING_BUNDLE
    state["evidence_status"] = evidence_status
    state["decision"] = selected.upper()
    state["finished_utc"] = utc_now()
    state["blockers"] = [*reasons, *decision_blockers]
    event_name = (
        "feasibility.spike.completed"
        if selected in {"pass", "safe_fallback"}
        else "feasibility.spike.blocked"
    )
    context = {
        "spike": state["spike"],
        "status": FINALIZED_PENDING_BUNDLE,
        "decision": selected.upper(),
    }
    all_reasons = [*reasons, *decision_blockers]
    if all_reasons:
        context["reason"] = "; ".join(all_reasons)
    _record_event(state, event_name, context)
    save_state(path, state)
    return selected, all_reasons


def _diagnostic_session(state_path: Path, suffix: str):
    diagnostics_module = _load_project_agent_module("diagnostics")
    DiagnosticSession = diagnostics_module.DiagnosticSession

    state = json.loads(state_path.read_text("utf-8"))
    identifier = f"{state['experiment_id']}-{suffix}"
    return DiagnosticSession.create(state_path.parent / "diagnostics", identifier)


def bundle_run(run: Path) -> tuple[Path, str, str]:
    state_path, state = load_state(run)
    if state["status"] != FINALIZED_PENDING_BUNDLE:
        raise SpikeError(
            "Finalize the run exactly once before exporting its terminal bundle."
        )
    if "bundle" in state:
        raise SpikeError(
            "This finalized run is already bundled and immutable; create a "
            "successor correlation ID instead of replacing its bundle."
        )
    session = _diagnostic_session(state_path, "evidence")
    for provider in ("runtime", "persistence", "versions"):
        session.register_context_provider(provider, lambda: {})
    session.register_context_provider("commands", lambda: {"recent": []})
    for event in state["events"]:
        session.emit(
            event["event_name"],
            source_component="milestone11",
            correlation_id=state["experiment_id"],
            context=event["context"],
        )
    result = session.export_bundle()
    if result.path is None:
        state["status"] = BUNDLE_INCOMPLETE
        state["bundle"] = {"status": result.status, "error": result.error}
        save_state(state_path, state)
        session.close(clean=False)
        raise SpikeError(f"Diagnostic bundle export failed: {result.error}")
    digest = sha256_file(result.path)
    state["bundle"] = {
        "name": result.path.name,
        "sha256": digest,
        "status": result.status,
    }
    decision = str(state["decision"]).lower()
    state["status"] = decision if result.status == "complete" else BUNDLE_INCOMPLETE
    _record_event(
        state,
        (
            "feasibility.spike.completed"
            if decision in {"pass", "safe_fallback"}
            else "feasibility.spike.blocked"
        ),
        {
            "spike": state["spike"],
            "status": state["status"],
            "decision": state["decision"],
            "bundle_name": result.path.name,
            "bundle_sha256": digest,
        },
    )
    save_state(state_path, state)
    session.emit(
        "feasibility.spike.completed"
        if decision in {"pass", "safe_fallback"}
        else "feasibility.spike.blocked",
        source_component="milestone11",
        correlation_id=state["experiment_id"],
        context={
            "spike": state["spike"],
            "status": state["status"],
            "decision": state["decision"],
            "bundle_name": result.path.name,
            "bundle_sha256": digest,
        },
    )
    session.close(clean=True)
    return result.path, digest, result.status


def review_run(
    source_run: Path,
    artifact_root: Path,
    reason: str,
) -> tuple[Path, Path, str, str]:
    source_path, source_state = load_state(source_run)
    if reason not in REVIEW_REASONS:
        raise SpikeError(f"Unknown bounded review reason: {reason}")
    expected_spike, decision = REVIEW_REASONS[reason]
    if source_state["spike"] != expected_spike:
        raise SpikeError("Review reason does not match the source spike.")
    if source_state["status"] not in DECISIONS:
        raise SpikeError("Review requires a finalized source run.")
    source_bundle = source_state.get("bundle")
    if (
        not isinstance(source_bundle, Mapping)
        or source_bundle.get("status") != "complete"
    ):
        raise SpikeError("Review requires a complete source-run support bundle.")
    if reason == "jetboard_semantics_proven":
        review_blockers = _jetboard_semantics_review_blockers(source_state)
        if review_blockers:
            raise SpikeError(
                "Jetboard semantics review is inconsistent: "
                + "; ".join(review_blockers)
            )
    elif reason == "release_blocking_reconstruction_leak":
        review_blockers = _native_reconstruction_review_blockers(source_state)
        if review_blockers:
            raise SpikeError(
                "Native reconstruction review is incomplete: "
                + "; ".join(review_blockers)
            )
    elif reason == "predefined_haven_fallback":
        review_blockers = _haven_fallback_blockers(source_state)
        if review_blockers:
            raise SpikeError(
                "Haven fallback review is inconsistent: " + "; ".join(review_blockers)
            )
    if decision in {"pass", "safe_fallback"}:
        provenance_blockers = _acceptance_provenance_blockers(source_state)
        if provenance_blockers:
            raise SpikeError(
                "Positive review requires complete live acceptance provenance: "
                + "; ".join(provenance_blockers)
            )

    root = require_safe_artifact_path(artifact_root)
    experiment_id = (
        f"m11-{expected_spike.replace('_', '-')}-review-{secrets.token_hex(4)}"
    )
    run = root / experiment_id
    run.mkdir(parents=True, exist_ok=False)
    source_digest = sha256_file(source_path)
    state: dict[str, Any] = {
        "schema_version": STATE_SCHEMA_VERSION,
        "experiment_id": experiment_id,
        "spike": expected_spike,
        "disposable_save_slot": source_state["disposable_save_slot"],
        "disposable_slot_acknowledged": True,
        "started_utc": utc_now(),
        "finished_utc": utc_now(),
        "status": FINALIZED_PENDING_BUNDLE,
        "evidence_status": (
            "reviewed_consistent_matrix"
            if reason == "jetboard_semantics_proven"
            else "reviewed_superseded_run"
        ),
        "decision": decision.upper(),
        "reviewed_source": {
            "experiment_id": source_state["experiment_id"],
            "run_sha256": source_digest,
            "reason": reason,
        },
        "checkpoints": source_state.get("checkpoints", {}),
        "preparations": source_state.get("preparations", []),
        "bridge_snapshot_uses": source_state.get("bridge_snapshot_uses", []),
        "events": list(source_state.get("events", [])),
        "blockers": [] if decision == "pass" else [reason],
    }
    if reason == "jetboard_semantics_proven":
        state["decision_scope"] = "jetboard_launch"
    _record_event(
        state,
        "feasibility.spike.completed"
        if decision in {"pass", "safe_fallback"}
        else "feasibility.spike.blocked",
        {
            "spike": expected_spike,
            "status": decision,
            "review_reason": reason,
            "source_experiment_id": source_state["experiment_id"],
            "source_run_sha256": source_digest,
        },
    )
    state_path = run / "run.json"
    save_state(state_path, state)
    bundle_path, bundle_digest, bundle_status = bundle_run(run)
    return run, bundle_path, bundle_digest, bundle_status


def _jetboard_semantics_review_blockers(state: Mapping[str, Any]) -> list[str]:
    """Require the complete Jetboard matrix before recording a reviewed PASS."""

    checkpoints = state.get("checkpoints")
    if not isinstance(checkpoints, Mapping):
        return ["checkpoints are not a mapping"]

    blockers: list[str] = []
    for checkpoint in SPIKES["jetboard_launch"]:
        record = checkpoints.get(checkpoint)
        if not isinstance(record, Mapping):
            blockers.append(f"missing semantic checkpoint {checkpoint}")
            continue
        assertions = record.get("assertions")
        if not isinstance(assertions, Mapping):
            blockers.append(f"{checkpoint}/assertions=invalid")
        else:
            for assertion in SPIKES["jetboard_launch"][checkpoint]:
                status = assertions.get(assertion)
                if status != "pass":
                    blockers.append(f"{checkpoint}/{assertion}={status or 'missing'}")
        observations = record.get("observations")
        expected = EXPECTED_OBSERVATIONS[("jetboard_launch", checkpoint)][
            "native_jetboard_mask"
        ]
        if not isinstance(observations, Mapping):
            blockers.append(f"{checkpoint}/observations=invalid")
        else:
            actual = observations.get("native_jetboard_mask")
            if actual != expected:
                blockers.append(
                    f"{checkpoint}/native_jetboard_mask={actual} (expected {expected})"
                )

    return blockers


def _native_reconstruction_review_blockers(
    state: Mapping[str, Any],
) -> list[str]:
    """Require the full five-stage typed lifecycle before accepting the blocker."""

    checkpoints = state.get("checkpoints")
    if not isinstance(checkpoints, Mapping):
        return ["checkpoints are not a mapping"]

    blockers: list[str] = []
    if state.get("status") != "blocked":
        blockers.append("source decision is not terminal BLOCKED")
    for checkpoint, required_assertions in SPIKES["native_reconstruction"].items():
        record = checkpoints.get(checkpoint)
        if not isinstance(record, Mapping):
            blockers.append(f"missing lifecycle checkpoint {checkpoint}")
            continue
        assertions = record.get("assertions")
        if not isinstance(assertions, Mapping):
            blockers.append(f"{checkpoint}/assertions=invalid")
        else:
            for assertion in required_assertions:
                status = assertions.get(assertion)
                if status != "pass":
                    blockers.append(f"{checkpoint}/{assertion}={status or 'missing'}")
        observations = record.get("observations")
        if not isinstance(observations, Mapping):
            blockers.append(f"{checkpoint}/observations=invalid")
            continue
        for field in sorted(NATIVE_RECONSTRUCTION_OBSERVATION_FIELDS):
            value = observations.get(field)
            if not isinstance(value, (int, float)):
                blockers.append(f"{checkpoint}/{field}=missing")
    if not _decision_blockers(state):
        blockers.append(
            "typed lifecycle does not prove a native reconstruction or AP-check leak"
        )
    return blockers


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)

    audit = subparsers.add_parser("audit", help="verify pinned source anchors")
    audit.add_argument("--jak-project", type=Path, default=DEFAULT_JAK_PROJECT)
    audit.add_argument("--archipelago", type=Path, default=DEFAULT_ARCHIPELAGO)
    audit.add_argument("--decompile", type=Path, default=DEFAULT_DECOMPILE)

    start = subparsers.add_parser("start", help="start one disposable-save run")
    start.add_argument("--artifact-root", type=Path, required=True)
    start.add_argument("--spike", choices=sorted(SPIKES), required=True)
    start.add_argument("--save-slot", type=int, required=True)
    start.add_argument("--acknowledge-disposable-save-slot", action="store_true")

    capture = subparsers.add_parser("capture", help="capture one named checkpoint")
    capture.add_argument("--run", type=Path, required=True)
    capture.add_argument("--checkpoint", required=True)
    capture.add_argument("--save-generation", type=int, default=0)
    capture.add_argument("--assert", dest="assertions", action="append", default=[])
    capture.add_argument("--observe", action="append", default=[])
    capture.add_argument("--live", action="store_true")
    capture.add_argument("--preset", choices=sorted(PRESET_FORMS))
    capture.add_argument("--acknowledge-live-mutation", action="store_true")
    capture.add_argument("--opengoal-log", type=Path)
    capture.add_argument("--bridge-snapshot", type=Path)
    capture.add_argument("--ap-state", type=Path)
    capture.add_argument("--reuse-attached-target", action="store_true")

    probe = subparsers.add_parser(
        "probe", help="run one restricted read-only live-state probe"
    )
    probe.add_argument("--probe", choices=sorted(READ_ONLY_PROBE_FORMS), required=True)
    probe.add_argument("--opengoal-log", type=Path, required=True)
    probe.add_argument("--bridge-snapshot", type=Path, required=True)
    probe.add_argument("--save-slot", type=int, choices=range(4), required=True)
    probe.add_argument("--reuse-attached-target", action="store_true")

    stage = subparsers.add_parser(
        "stage", help="apply one restricted setup preset before operator input"
    )
    stage.add_argument("--run", type=Path, required=True)
    stage.add_argument(
        "--preset",
        choices=sorted(set(PRESET_FORMS) - CAPTURE_ONLY_PRESETS),
        required=True,
    )
    stage.add_argument("--acknowledge-live-mutation", action="store_true")
    stage.add_argument("--opengoal-log", type=Path)
    stage.add_argument("--bridge-snapshot", type=Path, required=True)
    stage.add_argument("--reuse-attached-target", action="store_true")

    finish = subparsers.add_parser("finish", help="evaluate the complete matrix")
    finish.add_argument("--run", type=Path, required=True)
    finish.add_argument("--decision", choices=sorted(DECISIONS))

    bundle = subparsers.add_parser("bundle", help="export a sanitized support bundle")
    bundle.add_argument("--run", type=Path, required=True)

    review = subparsers.add_parser(
        "review", help="bundle an immutable superseded run under a new decision ID"
    )
    review.add_argument("--source-run", type=Path, required=True)
    review.add_argument("--artifact-root", type=Path, required=True)
    review.add_argument("--reason", choices=sorted(REVIEW_REASONS), required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.action == "audit":
            print(
                json.dumps(
                    audit_sources(args.jak_project, args.archipelago, args.decompile),
                    indent=2,
                    sort_keys=True,
                )
            )
        elif args.action == "start":
            print(
                start_run(
                    args.artifact_root,
                    args.spike,
                    args.save_slot,
                    acknowledged=args.acknowledge_disposable_save_slot,
                )
            )
        elif args.action == "capture":
            record = capture_checkpoint(
                args.run,
                args.checkpoint,
                parse_assertions(args.assertions),
                parse_observations(args.observe),
                save_generation=args.save_generation,
                live=args.live,
                preset=args.preset,
                mutation_acknowledged=args.acknowledge_live_mutation,
                opengoal_log=args.opengoal_log,
                bridge_snapshot=args.bridge_snapshot,
                ap_state=args.ap_state,
                reuse_attached_target=args.reuse_attached_target,
            )
            print(json.dumps(record, indent=2, sort_keys=True))
        elif args.action == "probe":
            observations = asyncio.run(
                _live_probe(
                    args.probe,
                    args.bridge_snapshot,
                    args.opengoal_log,
                    reuse_attached_target=args.reuse_attached_target,
                    expected_native_save_slot=args.save_slot,
                )
            )
            print(json.dumps(observations, indent=2, sort_keys=True))
        elif args.action == "stage":
            stage_run(
                args.run,
                args.preset,
                mutation_acknowledged=args.acknowledge_live_mutation,
                opengoal_log=args.opengoal_log,
                bridge_snapshot=args.bridge_snapshot,
                reuse_attached_target=args.reuse_attached_target,
            )
            print(json.dumps({"status": "staged", "preset": args.preset}, indent=2))
        elif args.action == "finish":
            decision, reasons = finish_run(args.run, args.decision)
            print(
                json.dumps(
                    {
                        "status": FINALIZED_PENDING_BUNDLE,
                        "decision": decision,
                        "reasons": reasons,
                    },
                    indent=2,
                )
            )
            return 0 if decision in {"pass", "safe_fallback"} else 2
        elif args.action == "bundle":
            path, digest, status = bundle_run(args.run)
            print(
                json.dumps(
                    {"path": str(path), "sha256": digest, "status": status}, indent=2
                )
            )
            return 0 if status == "complete" else 2
        elif args.action == "review":
            run, path, digest, status = review_run(
                args.source_run,
                args.artifact_root,
                args.reason,
            )
            print(
                json.dumps(
                    {
                        "run": str(run),
                        "path": str(path),
                        "sha256": digest,
                        "status": status,
                    },
                    indent=2,
                )
            )
            return 0 if status == "complete" else 2
        return 0
    except (
        OSError,
        SpikeError,
        subprocess.CalledProcessError,
        json.JSONDecodeError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
