import importlib
import json
import unittest
from pathlib import Path
from zipfile import ZipFile

from worlds import AutoWorldRegister
from worlds.LauncherComponents import Type, components, icon_paths
from worlds.jak3 import Jak3World, launch_client
from worlds.jak3.data import GAME_NAME


class PackagedWorldRegistrationTest(unittest.TestCase):
    def test_apworld_imports_and_registers_the_expected_game(self) -> None:
        module = importlib.import_module("worlds.jak3")

        self.assertIs(module.Jak3World, Jak3World)
        self.assertIs(AutoWorldRegister.world_types[GAME_NAME], Jak3World)
        self.assertEqual("Jak 3", Jak3World.game)
        self.assertIsNotNone(Jak3World.zip_path)
        self.assertIn(".apworld", str(Jak3World.__file__))
        self.assertEqual(".apworld", Path(Jak3World.zip_path).suffix)

    def test_packaged_manifest_and_payload_are_complete(self) -> None:
        self.assertIsNotNone(Jak3World.zip_path)
        with ZipFile(Path(Jak3World.zip_path)) as archive:
            manifest = json.loads(archive.read("jak3/archipelago.json"))
            entries = set(archive.namelist())

        self.assertEqual("Jak 3", manifest["game"])
        self.assertEqual("0.1.0", manifest["world_version"])
        self.assertEqual("0.6.7", manifest["minimum_ap_version"])
        self.assertEqual(["Jak3-AP Contributors"], manifest["authors"])
        self.assertEqual(7, manifest["version"])
        self.assertEqual(7, manifest["compatible_version"])
        self.assertTrue(
            {
                "jak3/__init__.py",
                "jak3/client.py",
                "jak3/agents/launcher.py",
                "jak3/agents/protocol.py",
                "jak3/assets/opengoal/archipelago.gc",
                "jak3/assets/opengoal/archipelago-startup.gc",
                "jak3/icons/jak3-logo.png",
            }.issubset(entries)
        )
        self.assertFalse(any("__pycache__" in entry for entry in entries))
        self.assertFalse(any(entry.endswith((".pyc", ".pyo")) for entry in entries))

    def test_world_metadata_matches_the_loaded_manifest(self) -> None:
        self.assertEqual("0.1.0", Jak3World.world_version.as_simple_string())
        self.assertEqual("Jak 3", Jak3World.manifest["game"])
        self.assertEqual("0.1.0", Jak3World.manifest["world_version"])
        self.assertEqual("0.6.7", Jak3World.manifest["minimum_ap_version"])

    def test_client_component_and_icon_are_registered_once(self) -> None:
        matches = [
            component
            for component in components
            if component.display_name == "Jak 3 Client"
        ]

        self.assertEqual(1, len(matches))
        component = matches[0]
        self.assertIs(component.func, launch_client)
        self.assertEqual(Type.CLIENT, component.type)
        self.assertEqual("Jak 3", component.game_name)
        self.assertTrue(component.supports_uri)
        self.assertEqual("jak3-logo", component.icon)
        self.assertEqual("ap:worlds.jak3/icons/jak3-logo.png", icon_paths["jak3-logo"])


if __name__ == "__main__":
    unittest.main()
