from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("migrate_legacy.py")
SPEC = importlib.util.spec_from_file_location(
    "apf_policy_migrate_legacy",
    MODULE_PATH,
)
assert SPEC is not None
assert SPEC.loader is not None
migration = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(migration)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2),
        encoding="utf-8",
    )


class MigrationTests(unittest.TestCase):
    def make_layout(self, root: Path) -> tuple[Path, Path, Path]:
        legacy = root / "legacy"
        alz = root / "alz"
        slz = root / "slz"

        for asset_type in migration.ASSET_TYPES:
            (legacy / asset_type).mkdir(parents=True, exist_ok=True)
            (alz / asset_type).mkdir(parents=True, exist_ok=True)
            (slz / asset_type).mkdir(parents=True, exist_ok=True)

        return legacy, alz, slz

    def test_exact_assignment_preserves_parameter_delta(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            legacy, alz, slz = self.make_layout(root)

            write_json(
                legacy / "policy_assignments" / "old.json",
                {
                    "name": "Deny-Test",
                    "identity": {"type": "None"},
                    "properties": {
                        "policyDefinitionId": (
                            "/providers/Microsoft.Authorization/"
                            "policyDefinitions/abc"
                        ),
                        "enforcementMode": "DoNotEnforce",
                        "parameters": {
                            "effect": {"value": "Audit"}
                        },
                    },
                },
            )

            write_json(
                alz
                / "policy_assignments"
                / "Deny-Test.alz_policy_assignment.json",
                {
                    "name": "Deny-Test",
                    "identity": {"type": "None"},
                    "properties": {
                        "policyDefinitionId": (
                            "/providers/Microsoft.Authorization/"
                            "policyDefinitions/abc"
                        ),
                        "enforcementMode": "Default",
                        "parameters": {
                            "effect": {"value": "Deny"}
                        },
                    },
                },
            )

            mapping_path = root / "mapping.json"
            write_json(
                mapping_path,
                {
                    "source": {},
                    "upstream": {},
                    "aliases": {},
                    "manual_classifications": {},
                },
            )

            report = migration.build_report(
                legacy_library_dir=legacy,
                alz_library_dir=alz,
                slz_library_dir=slz,
                mapping_path=mapping_path,
                strict_counts=False,
            )

            item = next(
                x
                for x in report["assets"]
                if x["asset_type"] == "policy_assignments"
            )
            self.assertEqual(item["classification"], "UPSTREAM")
            self.assertEqual(item["match_kind"], "exact")
            self.assertTrue(item["delta"]["requires_overlay"])
            self.assertIn(
                "enforcement_mode",
                item["delta"]["preserve_legacy_fields"],
            )
            self.assertIn(
                "parameters",
                item["delta"]["preserve_legacy_fields"],
            )

    def test_alias_and_manual_classification(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            legacy, alz, slz = self.make_layout(root)

            write_json(
                legacy / "policy_assignments" / "alias.json",
                {
                    "name": "CAF-Deny-Test",
                    "properties": {
                        "policyDefinitionId": (
                            "/providers/Microsoft.Authorization/"
                            "policyDefinitions/abc"
                        )
                    },
                },
            )
            write_json(
                legacy / "policy_assignments" / "custom.json",
                {
                    "name": "APF-Custom",
                    "properties": {
                        "policyDefinitionId": (
                            "${root_scope_resource_id}/providers/"
                            "Microsoft.Authorization/policyDefinitions/Custom"
                        )
                    },
                },
            )

            write_json(
                alz
                / "policy_assignments"
                / "Deny-Test.alz_policy_assignment.json",
                {
                    "name": "Deny-Test",
                    "properties": {
                        "policyDefinitionId": (
                            "/providers/Microsoft.Authorization/"
                            "policyDefinitions/abc"
                        )
                    },
                },
            )

            mapping_path = root / "mapping.json"
            write_json(
                mapping_path,
                {
                    "source": {},
                    "upstream": {},
                    "aliases": {
                        "policy_assignments": {
                            "CAF-Deny-Test": {
                                "target": "Deny-Test",
                                "source": "alz",
                            }
                        }
                    },
                    "manual_classifications": {
                        "policy_assignments": {
                            "APF-Custom": {
                                "classification": "APF_CUSTOM",
                                "reason": "Test custom assignment.",
                            }
                        }
                    },
                },
            )

            report = migration.build_report(
                legacy_library_dir=legacy,
                alz_library_dir=alz,
                slz_library_dir=slz,
                mapping_path=mapping_path,
                strict_counts=False,
            )
            items = {
                x["legacy_name"]: x
                for x in report["assets"]
                if x["asset_type"] == "policy_assignments"
            }

            self.assertEqual(
                items["CAF-Deny-Test"]["classification"],
                "UPSTREAM",
            )
            self.assertEqual(
                items["CAF-Deny-Test"]["match_kind"],
                "alias",
            )
            self.assertEqual(
                items["APF-Custom"]["classification"],
                "APF_CUSTOM",
            )

    def test_archetype_alias_reports_membership_delta(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            legacy, alz, slz = self.make_layout(root)

            write_json(
                legacy / "archetype_definitions" / "root.json",
                {
                    "es_root": {
                        "policy_assignments": [
                            "CAF-Deny-Test",
                            "APF-Only",
                        ],
                        "policy_definitions": [],
                        "policy_set_definitions": [],
                        "role_definitions": [],
                    }
                },
            )

            write_json(
                alz
                / "archetype_definitions"
                / "root.alz_archetype_definition.json",
                {
                    "name": "root",
                    "policy_assignments": ["Deny-Test"],
                    "policy_definitions": [],
                    "policy_set_definitions": [],
                    "role_definitions": [],
                },
            )

            mapping_path = root / "mapping.json"
            write_json(
                mapping_path,
                {
                    "source": {},
                    "upstream": {},
                    "aliases": {
                        "archetype_definitions": {
                            "es_root": {
                                "target": "root",
                                "source": "alz",
                            }
                        },
                        "policy_assignments": {
                            "CAF-Deny-Test": {
                                "target": "Deny-Test",
                                "source": "alz",
                            }
                        },
                    },
                    "manual_classifications": {},
                },
            )

            report = migration.build_report(
                legacy_library_dir=legacy,
                alz_library_dir=alz,
                slz_library_dir=slz,
                mapping_path=mapping_path,
                strict_counts=False,
            )
            item = next(
                x
                for x in report["assets"]
                if x["asset_type"] == "archetype_definitions"
            )

            self.assertEqual(item["classification"], "UPSTREAM")
            self.assertTrue(item["delta"]["requires_overlay"])
            self.assertEqual(
                item["delta"]["membership_delta"]["policy_assignments"][
                    "legacy_only"
                ],
                ["APF-Only"],
            )


if __name__ == "__main__":
    unittest.main()
