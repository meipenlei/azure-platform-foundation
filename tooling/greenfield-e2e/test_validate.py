#!/usr/bin/env python3

import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml


MODULE_PATH = (
    Path(__file__).resolve().parent / "validate.py"
)

spec = importlib.util.spec_from_file_location(
    "apf_greenfield_e2e",
    MODULE_PATH,
)

assert spec is not None
assert spec.loader is not None

validate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate)


class GreenfieldConfigurationTests(unittest.TestCase):
    def test_build_greenfield_configuration_overrides_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            foundation = {
                "schema_version": "0.1",
                "foundation": {
                    "version": "main",
                },
            }

            customer = {
                "schema_version": "0.1",
                "customer": {
                    "id": "source",
                    "display_name": "Source",
                },
                "azure": {
                    "tenant_id": "tenant",
                    "bootstrap_subscription_id": "subscription",
                    "cloud": "AzureCloud",
                    "primary_region": "germanywestcentral",
                },
            }

            platform = {
                "schema_version": "0.1",
                "deployment": {
                    "mode": "brownfield",
                },
                "execution": {
                    "provider": "github",
                    "github": {
                        "owner": "old-owner",
                        "repository": "old-repository",
                    },
                },
                "naming": {
                    "prefix": "old",
                },
            }

            for name, payload in (
                ("foundation.yaml", foundation),
                ("customer.yaml", customer),
                ("platform.yaml", platform),
            ):
                with (root / name).open("w", encoding="utf-8") as handle:
                    yaml.safe_dump(payload, handle, sort_keys=False)

            result = validate.build_greenfield_configuration(
                source_config_dir=root,
                customer_id="lab02",
                display_name="APF Greenfield Validation",
                github_owner="example",
                github_repository="lab02-apf-azure-platform",
                name_prefix="lab02",
            )

            self.assertEqual(
                result["customer.yaml"]["customer"]["id"],
                "lab02",
            )

            self.assertEqual(
                result["platform.yaml"]["deployment"]["mode"],
                "greenfield",
            )

            self.assertEqual(
                result["platform.yaml"]["execution"]["github"]["owner"],
                "example",
            )

            self.assertEqual(
                result["platform.yaml"]["execution"]["github"]["repository"],
                "lab02-apf-azure-platform",
            )

            self.assertEqual(
                result["platform.yaml"]["naming"]["prefix"],
                "lab02",
            )

            self.assertEqual(
                result["customer.yaml"]["azure"]["tenant_id"],
                "tenant",
            )



    def test_completed_migration_snapshot_prevents_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            bootstrap = (
                root
                / "levels"
                / "level0"
                / "bootstrap"
            )
            governance = (
                root
                / "levels"
                / "level0"
                / "governance"
            )
            foundation = (
                root
                / ".foundation"
            )

            bootstrap.mkdir(parents=True)
            governance.mkdir(parents=True)
            foundation.mkdir(parents=True)

            (bootstrap / "terraform.tfstate").write_text(
                "{}",
                encoding="utf-8",
            )
            (bootstrap / "backend.tf").write_text(
                'terraform { backend "azurerm" {} }',
                encoding="utf-8",
            )
            (bootstrap / "backend.hcl").write_text(
                'key = "level0.bootstrap.tfstate"',
                encoding="utf-8",
            )
            (governance / "backend.hcl").write_text(
                'key = "level0.governance.tfstate"',
                encoding="utf-8",
            )
            (foundation / "level0-bootstrap.yaml").write_text(
                "schema_version: '0.1'\\n",
                encoding="utf-8",
            )

            validate.recover_interrupted_local_state_migration(
                root
            )

            self.assertTrue(
                (bootstrap / "backend.tf").is_file()
            )
            self.assertTrue(
                (bootstrap / "backend.hcl").is_file()
            )
            self.assertTrue(
                (governance / "backend.hcl").is_file()
            )


if __name__ == "__main__":
    unittest.main()
