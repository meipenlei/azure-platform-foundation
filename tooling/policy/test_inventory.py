from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("inventory.py")
SPEC = importlib.util.spec_from_file_location("apf_policy_inventory", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)


class InventoryTests(unittest.TestCase):
    def test_inventory_reads_legacy_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            for name in inventory.ASSET_DIRS:
                (root / name).mkdir()

            (root / "archetype_definitions" / "root.json").write_text(
                json.dumps(
                    {
                        "root": {
                            "policy_assignments": ["Audit-One"],
                            "policy_definitions": [],
                            "policy_set_definitions": [],
                            "role_definitions": [],
                        }
                    }
                ),
                encoding="utf-8",
            )

            (root / "policy_assignments" / "assignment.json").write_text(
                json.dumps(
                    {
                        "name": "Audit-One",
                        "properties": {
                            "policyDefinitionId": (
                                "/providers/Microsoft.Authorization/"
                                "policyDefinitions/00000000-0000-0000-0000-000000000001"
                            ),
                            "enforcementMode": "Default",
                            "parameters": {
                                "effect": {"value": "Audit"}
                            },
                        },
                        "identity": {"type": "None"},
                    }
                ),
                encoding="utf-8",
            )

            (root / "policy_definitions" / "definition.json").write_text(
                json.dumps(
                    {
                        "name": "Custom-One",
                        "properties": {"displayName": "Custom One"},
                    }
                ),
                encoding="utf-8",
            )

            result = inventory.build_inventory(root)

            self.assertEqual(
                result["counts"]["archetype_definitions"],
                1,
            )
            self.assertEqual(
                result["counts"]["policy_assignments"],
                1,
            )
            self.assertEqual(
                result["assignments"][0]["reference_kind"],
                "built-in-policy",
            )
            self.assertEqual(
                result["archetypes"]["root"]["policy_assignments"],
                ["Audit-One"],
            )


if __name__ == "__main__":
    unittest.main()
