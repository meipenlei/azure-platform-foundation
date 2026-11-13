from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import yaml


MODULE_PATH = Path(__file__).with_name("configure.py")
SPEC = importlib.util.spec_from_file_location(
    "apf_customer_level1_management_configure",
    MODULE_PATH,
)
assert SPEC is not None
assert SPEC.loader is not None
configure = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(configure)


BOOTSTRAP_SUB = "22222222-2222-2222-2222-222222222222"
MANAGEMENT_SUB = "33333333-3333-3333-3333-333333333333"


class ConfigureTests(unittest.TestCase):
    def make_project(
        self,
        root: Path,
        *,
        management_subscription_id: str | None = None,
        retention_days: int = 30,
    ) -> Path:
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
                "bootstrap_subscription_id": BOOTSTRAP_SUB,
                "cloud": "public",
                "primary_region": "germanywestcentral",
            },
        }
        if management_subscription_id:
            customer["azure"]["management_subscription_id"] = (
                management_subscription_id
            )

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
            "management": {
                "monitoring": {
                    "log_analytics": {
                        "retention_days": retention_days,
                    }
                }
            },
        }

        bootstrap = {
            "schema_version": "0.1",
            "source": "terraform-bootstrap",
            "azure": {
                "tenant_id": customer["azure"]["tenant_id"],
                "subscription_id": BOOTSTRAP_SUB,
            },
            "bootstrap": {
                "resource_group_name": "lab04-rg-l0-bootstrap",
                "storage_account_name": "lab04state",
                "state_container_name": "tfstate",
                "state_container_id": "/subscriptions/x/containers/tfstate",
                "backend_configuration": {
                    "resource_group_name": "lab04-rg-l0-bootstrap",
                    "storage_account_name": "lab04state",
                    "container_name": "tfstate",
                },
            },
        }

        level1 = {
            "schema_version": "0.1",
            "source": "terraform-level1-management-groups",
            "management_groups": {
                "root_management_group_id": (
                    "/providers/Microsoft.Management/managementGroups/lab04"
                ),
                "root_management_group_name": "lab04",
                "management_group_ids": {
                    "root": (
                        "/providers/Microsoft.Management/"
                        "managementGroups/lab04"
                    ),
                    "management": (
                        "/providers/Microsoft.Management/"
                        "managementGroups/lab04-management"
                    ),
                },
                "bootstrap_subscription_parent_management_group_id": (
                    "/providers/Microsoft.Management/"
                    "managementGroups/lab04-management"
                ),
                "policy_deployment_root_scope": (
                    "/providers/Microsoft.Management/"
                    "managementGroups/lab04"
                ),
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
        (project / ".foundation/level1-management-groups.yaml").write_text(
            yaml.safe_dump(level1, sort_keys=False),
            encoding="utf-8",
        )
        return project

    def load_inputs(self, project: Path):
        data = configure.require_project(project)
        configure.validate_inputs(
            foundation=data[0],
            customer=data[1],
            platform=data[2],
            bootstrap=data[3],
            level1=data[4],
        )
        return data

    def test_lab_falls_back_to_bootstrap_subscription(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.make_project(Path(temp))
            foundation, customer, platform, bootstrap, level1 = (
                self.load_inputs(project)
            )
            files = configure.desired_files(
                project_dir=project,
                foundation=foundation,
                customer=customer,
                platform=platform,
                bootstrap=bootstrap,
                level1=level1,
            )

            root = project / "levels/level1/management-platform"
            tfvars = json.loads(
                files[root / "generated.auto.tfvars.json"]
            )
            self.assertEqual(
                tfvars["management_subscription_id"],
                BOOTSTRAP_SUB,
            )
            self.assertEqual(
                tfvars["log_analytics_retention_days"],
                30,
            )

    def test_dedicated_management_subscription_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.make_project(
                Path(temp),
                management_subscription_id=MANAGEMENT_SUB,
                retention_days=60,
            )
            foundation, customer, platform, bootstrap, level1 = (
                self.load_inputs(project)
            )
            files = configure.desired_files(
                project_dir=project,
                foundation=foundation,
                customer=customer,
                platform=platform,
                bootstrap=bootstrap,
                level1=level1,
            )

            snapshot = yaml.safe_load(
                files[project / configure.MANAGEMENT_SNAPSHOT]
            )
            self.assertEqual(
                snapshot["azure"]["subscription_id"],
                MANAGEMENT_SUB,
            )
            self.assertEqual(
                snapshot["management"]["log_analytics_workspace"][
                    "retention_days"
                ],
                60,
            )
            self.assertIn(
                f"/subscriptions/{MANAGEMENT_SUB}/resourceGroups/"
                "lab04-rg-l1-management/providers/"
                "Microsoft.OperationalInsights/workspaces/"
                "lab04-law-l1-platform",
                snapshot["management"]["log_analytics_workspace"]["id"],
            )

    def test_identity_boundary_and_state_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.make_project(Path(temp))
            foundation, customer, platform, bootstrap, level1 = (
                self.load_inputs(project)
            )
            files = configure.desired_files(
                project_dir=project,
                foundation=foundation,
                customer=customer,
                platform=platform,
                bootstrap=bootstrap,
                level1=level1,
            )

            root = project / "levels/level1/management-platform"
            plan = files[
                project
                / ".github/workflows/"
                "terraform-level1-management-platform-plan.yml"
            ]
            apply = files[
                project
                / ".github/workflows/"
                "terraform-level1-management-platform-apply.yml"
            ]
            backend = files[root / "backend.hcl"]
            provider = files[root / "providers.tf"]

            self.assertIn("AZURE_PLAN_CLIENT_ID", plan)
            self.assertNotIn("AZURE_GOVERNANCE_CLIENT_ID", plan)
            self.assertIn("AZURE_GOVERNANCE_CLIENT_ID", apply)
            self.assertIn(
                "environment:\n      name: apf-governance",
                apply,
            )
            self.assertIn(
                "github.ref == 'refs/heads/main'",
                apply,
            )
            self.assertIn(
                'key                  = "level1.management-platform.tfstate"',
                backend,
            )
            self.assertIn(
                "subscription_id = var.management_subscription_id",
                provider,
            )

    def test_invalid_retention_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.make_project(
                Path(temp),
                retention_days=29,
            )
            data = configure.require_project(project)
            with self.assertRaises(configure.ConfigureError):
                configure.validate_inputs(
                    foundation=data[0],
                    customer=data[1],
                    platform=data[2],
                    bootstrap=data[3],
                    level1=data[4],
                )

    def test_render_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.make_project(Path(temp))
            foundation, customer, platform, bootstrap, level1 = (
                self.load_inputs(project)
            )
            files = configure.desired_files(
                project_dir=project,
                foundation=foundation,
                customer=customer,
                platform=platform,
                bootstrap=bootstrap,
                level1=level1,
            )
            configure.write_files(files)
            self.assertEqual(configure.changed_files(files), [])


if __name__ == "__main__":
    unittest.main()
