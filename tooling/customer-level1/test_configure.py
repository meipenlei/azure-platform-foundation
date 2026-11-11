from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml


MODULE_PATH = Path(__file__).with_name("configure.py")
SPEC = importlib.util.spec_from_file_location(
    "apf_customer_level1_configure",
    MODULE_PATH,
)
assert SPEC is not None
assert SPEC.loader is not None
configure = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(configure)


class ConfigureTests(unittest.TestCase):
    def make_project(self, root: Path) -> Path:
        project = root / "customer"
        (project / "config").mkdir(parents=True)
        (project / ".foundation").mkdir(parents=True)

        foundation = {
            "schema_version": "0.1",
            "foundation": {"version": "main"},
        }
        customer = {
            "schema_version": "0.1",
            "customer": {
                "id": "lab04",
                "display_name": "APF Reference Environment",
            },
            "azure": {
                "tenant_id": "11111111-1111-1111-1111-111111111111",
                "bootstrap_subscription_id": "22222222-2222-2222-2222-222222222222",
                "cloud": "public",
                "primary_region": "germanywestcentral",
            },
        }
        platform = {
            "schema_version": "0.1",
            "deployment": {"mode": "greenfield"},
            "iac": {"engine": "terraform"},
            "execution": {
                "provider": "github",
                "github": {
                    "owner": "example",
                    "repository": "lab04-apf-azure-platform",
                },
            },
            "naming": {"prefix": "lab04"},
            "security": {
                "authentication": "workload-identity-federation",
                "allow_long_lived_credentials": False,
            },
        }
        bootstrap = {
            "schema_version": "0.1",
            "source": "terraform-bootstrap",
            "azure": {
                "tenant_id": customer["azure"]["tenant_id"],
                "subscription_id": customer["azure"]["bootstrap_subscription_id"],
            },
            "bootstrap": {
                "resource_group_name": "lab04-rg-l0-bootstrap",
                "storage_account_name": "lab04state",
                "state_container_name": "tfstate",
                "state_container_id": "/subscriptions/x/resourceGroups/y/providers/Microsoft.Storage/storageAccounts/z/blobServices/default/containers/tfstate",
                "backend_configuration": {
                    "resource_group_name": "lab04-rg-l0-bootstrap",
                    "storage_account_name": "lab04state",
                    "container_name": "tfstate",
                },
            },
        }

        for filename, data in (
            ("foundation.yaml", foundation),
            ("customer.yaml", customer),
            ("platform.yaml", platform),
        ):
            (project / "config" / filename).write_text(
                yaml.safe_dump(data, sort_keys=False),
                encoding="utf-8",
            )

        (project / ".foundation/level0-bootstrap.yaml").write_text(
            yaml.safe_dump(bootstrap, sort_keys=False),
            encoding="utf-8",
        )

        return project

    def test_generated_root_and_workflows(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.make_project(Path(temp))
            foundation, customer, platform, bootstrap = configure.require_project(project)

            files = configure.desired_files(
                project_dir=project,
                foundation=foundation,
                customer=customer,
                platform=platform,
                bootstrap=bootstrap,
            )

            root = project / "levels/level1/management-groups"
            main = files[root / "main.tf"]
            backend = files[root / "backend.hcl"]
            tfvars = files[root / "generated.auto.tfvars.json"]
            plan = files[
                project
                / ".github/workflows/terraform-level1-management-groups-plan.yml"
            ]
            apply = files[
                project
                / ".github/workflows/terraform-level1-management-groups-apply.yml"
            ]

            self.assertIn("?ref=main", main)
            self.assertIn(
                'key                  = "level1.management-groups.tfstate"',
                backend,
            )
            self.assertIn('"name_prefix": "lab04"', tfvars)
            self.assertIn("AZURE_PLAN_CLIENT_ID", plan)
            self.assertNotIn("environment:\n      name: apf-governance", plan)
            self.assertIn("AZURE_GOVERNANCE_CLIENT_ID", apply)
            self.assertIn("environment:\n      name: apf-governance", apply)

    def test_render_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.make_project(Path(temp))
            foundation, customer, platform, bootstrap = configure.require_project(project)
            files = configure.desired_files(
                project_dir=project,
                foundation=foundation,
                customer=customer,
                platform=platform,
                bootstrap=bootstrap,
            )
            configure.write_files(files)
            self.assertEqual(configure.changed_files(files), [])


if __name__ == "__main__":
    unittest.main()
