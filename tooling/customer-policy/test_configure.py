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


class ConfigureTests(unittest.TestCase):
    def make_project(self, root: Path) -> Path:
        project = root / "customer"
        (project / "config").mkdir(parents=True)
        (project / ".foundation").mkdir(parents=True)

        customer = {
            "schema_version": "0.1",
            "customer": {"id": "lab", "display_name": "Lab"},
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

        (project / "config" / "customer.yaml").write_text(
            yaml.safe_dump(customer, sort_keys=False),
            encoding="utf-8",
        )
        (project / "config" / "platform.yaml").write_text(
            yaml.safe_dump(platform, sort_keys=False),
            encoding="utf-8",
        )
        (project / ".foundation" / "discovery.yaml").write_text(
            yaml.safe_dump(discovery, sort_keys=False),
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
            "stage": "subscription_pilot",
            "desired_state_strategy": "ownedOnly",
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
                        "id": "/providers/Microsoft.Authorization/policyDefinitions/test",
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

    def test_generated_plan_is_owned_only_and_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.make_project(Path(temp))
            customer, platform, discovery = configure.verify_project(project)

            configure.validate_inputs(
                customer=customer,
                platform=platform,
                discovery=discovery,
                versions=self.versions(),
                profile=self.profile(),
            )

            files = configure.desired_files(
                project_dir=project,
                customer=customer,
                versions=self.versions(),
                profile=self.profile(),
                discovery=discovery,
            )

            global_settings = json.loads(
                files[
                    project
                    / "governance/policy/Definitions/global-settings.jsonc"
                ]
            )
            assignment = json.loads(
                files[
                    project
                    / "governance/policy/Definitions/policyAssignments/"
                    "apf-audit-public-ip.assignment.jsonc"
                ]
            )
            workflow = files[
                project / ".github/workflows/policy-plan.yml"
            ]

            env = global_settings["pacEnvironments"][0]
            self.assertEqual(
                env["deploymentRootScope"],
                "/subscriptions/22222222-2222-2222-2222-222222222222",
            )
            self.assertEqual(
                env["desiredState"]["strategy"],
                "ownedOnly",
            )
            self.assertEqual(
                assignment["parameters"]["effect"],
                "Audit",
            )
            self.assertIn("AZURE_PLAN_CLIENT_ID", workflow)
            self.assertIn("Build-DeploymentPlans", workflow)
            self.assertNotIn("Deploy-PolicyPlan", workflow)
            self.assertNotIn("Deploy-RolesPlan", workflow)
            self.assertNotIn("apf-governance\n", workflow)

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

    def test_gitignore_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.make_project(Path(temp))
            path, content = configure.ensure_gitignore(project)
            path.write_text(content, encoding="utf-8")
            _, second = configure.ensure_gitignore(project)
            self.assertEqual(content, second)
            self.assertEqual(
                content.count("governance/policy/Output/"),
                1,
            )


if __name__ == "__main__":
    unittest.main()
