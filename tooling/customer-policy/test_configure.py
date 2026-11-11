from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import uuid
from pathlib import Path

import yaml


MODULE_PATH = Path(__file__).with_name("configure.py")
SPEC = importlib.util.spec_from_file_location(
    "apf_customer_policy_configure",
    MODULE_PATH,
)
assert SPEC is not None
assert SPEC.loader is not None
configure = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(configure)


ROOT_SCOPE = "/providers/Microsoft.Management/managementGroups/lab"


class ConfigureTests(unittest.TestCase):
    def make_project(
        self,
        root: Path,
        *,
        include_level1: bool = True,
    ) -> Path:
        project = root / "customer"
        (project / "config").mkdir(parents=True)
        (project / ".foundation").mkdir(parents=True)

        customer = {
            "schema_version": "0.1",
            "customer": {
                "id": "lab",
                "display_name": "Lab",
            },
            "azure": {
                "tenant_id": "11111111-1111-1111-1111-111111111111",
                "bootstrap_subscription_id": (
                    "22222222-2222-2222-2222-222222222222"
                ),
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
                    "repository": "example-platform",
                },
            },
            "naming": {"prefix": "lab"},
            "security": {
                "authentication": "workload-identity-federation",
                "allow_long_lived_credentials": False,
            },
        }
        discovery = {
            "schema_version": "0.1",
            "github": {
                "owner": "example",
                "owner_id": "123",
                "repository": "example-platform",
                "repository_id": "456",
            },
        }
        level1 = {
            "schema_version": "0.1",
            "source": "terraform-level1-management-groups",
            "management_groups": {
                "root_management_group_id": ROOT_SCOPE,
                "root_management_group_name": "lab",
                "management_group_ids": {
                    "root": ROOT_SCOPE,
                    "platform": ROOT_SCOPE + "-platform",
                },
                "bootstrap_subscription_parent_management_group_id": (
                    ROOT_SCOPE + "-management"
                ),
                "policy_deployment_root_scope": ROOT_SCOPE,
            },
        }

        (project / "config/customer.yaml").write_text(
            yaml.safe_dump(customer, sort_keys=False),
            encoding="utf-8",
        )
        (project / "config/platform.yaml").write_text(
            yaml.safe_dump(platform, sort_keys=False),
            encoding="utf-8",
        )
        (project / ".foundation/discovery.yaml").write_text(
            yaml.safe_dump(discovery, sort_keys=False),
            encoding="utf-8",
        )

        if include_level1:
            (project / configure.LEVEL1_SNAPSHOT).write_text(
                yaml.safe_dump(level1, sort_keys=False),
                encoding="utf-8",
            )

        (project / ".gitignore").write_text(
            "# Terraform\n.terraform/\n",
            encoding="utf-8",
        )

        return project

    def versions(self) -> dict:
        return {
            "epac": {"version": "11.5.11"},
            "azure_landing_zones_library": {
                "alz_tag": "platform/alz/2026.11.0",
                "slz_tag": "platform/slz/2026.11.0",
            },
        }

    def profile(self) -> dict:
        return {
            "name": "enterprise",
            "adoption_mode": "audit_first",
            "stage": "management_group_pilot",
            "desired_state_strategy": "ownedOnly",
            "scope_source": configure.LEVEL1_SNAPSHOT,
            "upstream": {
                "alz_tag": "platform/alz/2026.11.0",
                "assignment": "Deny-Public-IP",
            },
            "migration_provenance": {
                "legacy_assignment": "CAF-Deny-Public-IP",
            },
            "assignments": [
                {
                    "definition": {
                        "id": (
                            "/providers/Microsoft.Authorization/"
                            "policyDefinitions/test"
                        ),
                        "definition_version": "2.*.*",
                        "display_name": "Test policy",
                    },
                    "assignment": {
                        "name": "apf-audit-public-ip",
                        "display_name": "APF - Audit public IP creation",
                        "description": "Test",
                    },
                    "enforcement_mode": "Default",
                    "parameters": {
                        "effect": "Audit",
                        "listOfResourceTypesNotAllowed": [
                            "Microsoft.Network/publicIPAddresses"
                        ],
                    },
                }
            ],
        }

    def test_generated_plan_uses_level1_management_group(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.make_project(Path(temp))
            (
                customer,
                platform,
                discovery,
                level1,
            ) = configure.verify_project(project)

            configure.validate_inputs(
                customer=customer,
                platform=platform,
                discovery=discovery,
                level1=level1,
                versions=self.versions(),
                profile=self.profile(),
            )

            files = configure.desired_files(
                project_dir=project,
                customer=customer,
                versions=self.versions(),
                profile=self.profile(),
                discovery=discovery,
                level1=level1,
            )

            global_settings = json.loads(
                files[
                    project
                    / "governance/policy/Definitions/"
                    "global-settings.jsonc"
                ]
            )
            assignment = json.loads(
                files[
                    project
                    / "governance/policy/Definitions/policyAssignments/"
                    "apf-audit-public-ip.assignment.jsonc"
                ]
            )
            metadata = yaml.safe_load(
                files[project / ".foundation/policy.yaml"]
            )
            workflow = files[
                project / ".github/workflows/policy-plan.yml"
            ]

            env = global_settings["pacEnvironments"][0]

            self.assertEqual(
                env["deploymentRootScope"],
                ROOT_SCOPE,
            )
            self.assertEqual(
                env["desiredState"]["strategy"],
                "ownedOnly",
            )
            self.assertEqual(
                assignment["scope"][configure.PAC_SELECTOR],
                [ROOT_SCOPE],
            )
            self.assertEqual(
                assignment["parameters"]["effect"],
                "Audit",
            )
            self.assertEqual(
                assignment["definitionEntry"]["definitionVersion"],
                "2.*.*",
            )
            self.assertEqual(
                metadata["deployment_root_scope"],
                ROOT_SCOPE,
            )
            self.assertEqual(
                metadata["deployment_root_source"],
                configure.LEVEL1_SNAPSHOT,
            )

            self.assertIn("AZURE_PLAN_CLIENT_ID", workflow)
            self.assertIn("Build-DeploymentPlans", workflow)
            self.assertNotIn("Deploy-PolicyPlan", workflow)
            self.assertNotIn("Deploy-RolesPlan", workflow)

    def test_level1_snapshot_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.make_project(
                Path(temp),
                include_level1=False,
            )

            with self.assertRaises(configure.ConfigureError):
                configure.verify_project(project)

    def test_subscription_scope_is_rejected(self) -> None:
        level1 = {
            "management_groups": {
                "management_group_ids": {
                    "root": "/subscriptions/example"
                },
                "policy_deployment_root_scope": (
                    "/subscriptions/example"
                ),
            }
        }

        with self.assertRaises(configure.ConfigureError):
            configure.deployment_root_scope(level1)

    def test_pac_owner_id_is_deterministic(self) -> None:
        discovery = {
            "github": {
                "owner_id": "123",
                "repository_id": "456",
            }
        }
        first = configure.pac_owner_id(discovery)
        second = configure.pac_owner_id(discovery)

        self.assertEqual(first, second)
        uuid.UUID(first)


if __name__ == "__main__":
    unittest.main()
