"""Generate the disposable two-slot Milestone 10 acceptance fixture.

The checked-in canonical YAML remains the single option-default source.  This
tool changes only player identity, description, and standard Archipelago item
plando blocks, then writes two ordinary player YAML files.
"""

from __future__ import annotations

import argparse
from pathlib import Path


RUNNER_NAME = "M10 Runner"
HELPER_NAME = "M10 Helper"
HELPER_ITEM_NAMES = (
    "Scatter Gun",
    "Wave Concussor",
    "Plasmite RPG",
    "Beam Reflexor",
    "Gyro Burster",
)
_NAME_MARKER = "name: Player{number}"
_DESCRIPTION_MARKER = (
    "  Recommended full-accessibility Jak 3 seed with a tiered open mission board,\n"
    "  5-of-7 relic finale, selected finite sanity checks, and safe mission bootstrap."
)
_PLANDO_MARKER = "  plando_items: []"

RUNNER_PLANDO = """  plando_items:
    - item: Jetboard
      location: "Complete Mission: Complete Arena Training"
      world: "M10 Runner"
      from_pool: true
      force: true
    - item: Blaster
      location: "Complete Mission: Earn 1st War Amulet"
      world: "M10 Runner"
      from_pool: true
      force: true
    - item: Progressive Armor
      location: "Reward: First Armor Upgrade"
      world: "M10 Runner"
      from_pool: true
      force: true"""

HELPER_PLANDO = """  plando_items:
    - items:
        "Scatter Gun": 1
        "Wave Concussor": 1
        "Plasmite RPG": 1
        "Beam Reflexor": 1
        "Gyro Burster": 1
      locations:
        - "Complete Mission: Catch Kanga-Rats"
        - "Complete Mission: Unlock Satellite"
        - "Complete Mission: Learn to Drive a Vehicle"
        - "Complete Mission: Beat Kleiver in Desert Race"
        - "Complete Mission: Race for Artifacts"
      world: "M10 Runner"
      count: 5
      from_pool: true
      force: true"""


def _player_document(template: str, *, name: str, plando: str) -> str:
    if template.count(_NAME_MARKER) != 1:
        raise ValueError("Canonical YAML name marker changed; fixture not generated.")
    if template.count(_DESCRIPTION_MARKER) != 1:
        raise ValueError(
            "Canonical YAML description marker changed; fixture not generated."
        )
    if template.count(_PLANDO_MARKER) != 1:
        raise ValueError("Canonical YAML plando marker changed; fixture not generated.")
    description = (
        "  Disposable Milestone 10 vertical-slice fixture. Do not reuse its native\n"
        "  save or AP sidecar with an ordinary task-72 seed."
    )
    return (
        template.replace(_NAME_MARKER, f"name: {name}", 1)
        .replace(_DESCRIPTION_MARKER, description, 1)
        .replace(_PLANDO_MARKER, plando, 1)
    )


def build_fixture_documents(template: str) -> dict[str, str]:
    """Return the exact two canonical-derived player documents."""

    return {
        "M10-Runner.yaml": _player_document(
            template, name=RUNNER_NAME, plando=RUNNER_PLANDO
        ),
        "M10-Helper.yaml": _player_document(
            template, name=HELPER_NAME, plando=HELPER_PLANDO
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--template",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "config"
        / "templates"
        / "Jak3.yaml",
    )
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()

    template = args.template.read_text(encoding="utf-8")
    documents = build_fixture_documents(template)
    args.output_directory.mkdir(parents=True, exist_ok=True)
    for name, payload in documents.items():
        destination = args.output_directory / name
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(payload, encoding="utf-8", newline="\n")
        temporary.replace(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
