from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
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
MG_IDS = {
    "root": ROOT_SCOPE,
    "platform": ROOT_SCOPE + "-platform",
    "landing_zones": ROOT_SCOPE + "-landing-zones",
    "sandboxes": ROOT_SCOPE + "-sandboxes",
    "decommissioned": ROOT_SCOPE + "-decommissioned",
    "management": ROOT_SCOPE + "-management",
    "connectivity": ROOT_SCOPE + "-connectivity",
    "identity": ROOT_SCOPE + "-identity",
    "corp": ROOT_SCOPE + "-corp",
    "online": ROOT_SCOPE + "-online",
}


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
        level1 = {
            "schema_version": "0.1",
            "source": "terraform-level1-management-groups",
            "management_groups": {
                "root_management_group_id": ROOT_SCOPE,
                "root_management_group_name": "lab",
                "management_group_ids": MG_IDS,
                "bootstrap_subscription_parent_management_group_id": MG_IDS["management"],
                "policy_deployment_root_scope": ROOT_SCOPE,
            },
        }

        (project / "config/customer.yaml").write_text(
            yaml.safe_dump(customer, sort_keys=False), encoding="utf-8"
        )
        (project / "config/platform.yaml").write_text(
            yaml.safe_dump(platform, sort_keys=False), encoding="utf-8"
        )
        (project / ".foundation/discovery.yaml").write_text(
            yaml.safe_dump(discovery, sort_keys=False), encoding="utf-8"
        )
        (project / configure.LEVEL1_SNAPSHOT).write_text(
            yaml.safe_dump(level1, sort_keys=False), encoding="utf-8"
        )
        (project / ".gitignore").write_text(
            "# Terraform\n.terraform/\n", encoding="utf-8"
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
        return json.loads(
            (
                Path(__file__).resolve().parents[2]
                / "foundation/policy/profiles/enterprise/audit-first-wave2.json"
            ).read_text(encoding="utf-8")
        )

    def test_wave2_generates_eight_scope_aware_assignments(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.make_project(Path(temp))
            customer, platform, discovery, level1 = configure.verify_project(project)
            profile = self.profile()

            configure.validate_inputs(
                customer=customer,
                platform=platform,
                discovery=discovery,
                level1=level1,
                versions=self.versions(),
                profile=profile,
            )

            files = configure.desired_files(
                project_dir=project,
                customer=customer,
                versions=self.versions(),
                profile=profile,
                discovery=discovery,
                level1=level1,
            )

            assignment_dir = project / "governance/policy/Definitions/policyAssignments"
            generated = {
                path.name: json.loads(content)
                for path, content in files.items()
                if path.parent == assignment_dir
            }

            self.assertEqual(len(generated), 8)

            expected = {
                "apf-audit-public-ip.assignment.jsonc": (1, "identity", "Default", "Audit"),
                "apf-deny-classic-resources.assignment.jsonc": (1, "root", "DoNotEnforce", "Deny"),
                "apf-deny-storage-http.assignment.jsonc": (1, "landing_zones", "DoNotEnforce", "Deny"),
                "apf-deny-hybrid-networking.assignment.jsonc": (1, "corp", "DoNotEnforce", "Deny"),
                "apf-audit-resource-rg-location.assignment.jsonc": (2, "root", "Default", None),
                "apf-audit-appgw-waf.assignment.jsonc": (2, "landing_zones", "Default", "Audit"),
                "apf-deny-priv-esc-aks.assignment.jsonc": (2, "landing_zones", "DoNotEnforce", "Deny"),
                "apf-deny-privileged-aks.assignment.jsonc": (2, "landing_zones", "DoNotEnforce", "Deny"),
            }

            for filename, (wave, scope_key, enforcement, effect) in expected.items():
                doc = generated[filename]
                self.assertEqual(doc["scope"][configure.PAC_SELECTOR], [MG_IDS[scope_key]])
                self.assertEqual(doc["enforcementMode"], enforcement)
                self.assertEqual(doc["parameters"].get("effect"), effect)
                self.assertEqual(doc["metadata"]["apfScopeKey"], scope_key)
                self.assertIn(f"/Wave{wave}/", doc["nodeName"])

            # Wave 1 Azure assignment payloads retain their original stage metadata.
            self.assertEqual(
                generated["apf-audit-public-ip.assignment.jsonc"]["metadata"]["apfStage"],
                "scope_aware_wave1",
            )
            self.assertEqual(
                generated["apf-audit-appgw-waf.assignment.jsonc"]["metadata"]["apfStage"],
                "scope_aware_wave2",
            )

            waf = next(
                item for item in profile["assignments"]
                if item["key"] == "audit_appgw_waf"
            )
            self.assertEqual(waf["legacy_redundant_archetypes"], ["es_online"])
            self.assertEqual(
                generated["apf-audit-appgw-waf.assignment.jsonc"]["scope"][configure.PAC_SELECTOR],
                [MG_IDS["landing_zones"]],
            )

            metadata = yaml.safe_load(files[project / ".foundation/policy.yaml"])
            self.assertEqual(metadata["profile"]["assignment_count"], 8)
            self.assertEqual(metadata["profile"]["wave"], 2)
            self.assertEqual(metadata["profile"]["stage"], "scope_aware_wave2")
            self.assertEqual(metadata["desired_state_strategy"], "ownedOnly")

    def test_unknown_scope_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.make_project(Path(temp))
            _, _, _, level1 = configure.verify_project(project)
            assignment = {"scope_key": "security"}

            with self.assertRaises(configure.ConfigureError):
                configure.assignment_scope(level1, assignment)

    def test_profile_rejects_duplicate_assignment_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.make_project(Path(temp))
            _, _, _, level1 = configure.verify_project(project)
            profile = self.profile()
            profile["assignments"][1]["file_name"] = profile["assignments"][0]["file_name"]

            with self.assertRaises(configure.ConfigureError):
                configure.validate_profile(profile, level1)

    def test_plan_and_apply_workflows_keep_identity_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.make_project(Path(temp))
            customer, _, discovery, level1 = configure.verify_project(project)
            files = configure.desired_files(
                project_dir=project,
                customer=customer,
                versions=self.versions(),
                profile=self.profile(),
                discovery=discovery,
                level1=level1,
            )

            plan = files[project / ".github/workflows/policy-plan.yml"]
            apply = files[project / ".github/workflows/policy-apply.yml"]
            metadata = yaml.safe_load(
                files[project / ".foundation/policy.yaml"]
            )
            guard = files[
                project / "governance/policy/tooling/verify_apply_plan.py"
            ]

            self.assertIn("AZURE_PLAN_CLIENT_ID", plan)
            self.assertIn("Build-DeploymentPlans", plan)
            self.assertNotIn("Deploy-PolicyPlan", plan)
            self.assertNotIn("Deploy-RolesPlan", plan)
            self.assertIn("policy-apply.yml", plan)
            self.assertIn("id: plan-output", plan)
            self.assertIn('echo "has_plan=true" >> "$GITHUB_OUTPUT"', plan)
            self.assertIn('echo "has_plan=false" >> "$GITHUB_OUTPUT"', plan)
            self.assertIn(
                "if: steps.plan-output.outputs.has_plan == 'true'",
                plan,
            )
            self.assertIn("if-no-files-found: error", plan)

            self.assertIn("workflow_dispatch", apply)
            self.assertIn("AZURE_GOVERNANCE_CLIENT_ID", apply)
            self.assertIn("environment:\n      name: apf-governance", apply)
            self.assertIn("Deploy-PolicyPlan", apply)
            self.assertIn("Deploy-RolesPlan", apply)
            self.assertIn("governance/policy/tooling/verify_apply_plan.py", apply)
            self.assertIn("--mode pre-apply", apply)
            self.assertIn("--mode post-apply", apply)
            self.assertIn('POST_APPLY_MAX_ATTEMPTS: "5"', apply)
            self.assertIn('POST_APPLY_RETRY_SECONDS: "30"', apply)
            self.assertIn("Start-Sleep -Seconds $retrySeconds", apply)
            self.assertIn("$verifyExit -ne 3", apply)
            self.assertNotIn("AZURE_PLAN_CLIENT_ID", apply)
            self.assertIn("Protected apply", guard)

            self.assertEqual(metadata["mode"], "protected_apply")
            self.assertEqual(
                metadata["ci_cd"]["apply_environment"],
                "apf-governance",
            )
            self.assertEqual(
                metadata["ci_cd"]["apply_guard"],
                "additive_assignments_only",
            )

    def test_profile_rejects_assignment_names_over_24_chars(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.make_project(Path(temp))
            _, _, _, level1 = configure.verify_project(project)
            profile = self.profile()
            profile["assignments"][0]["assignment"]["name"] = "x" * 25

            with self.assertRaises(configure.ConfigureError):
                configure.validate_profile(profile, level1)


if __name__ == "__main__":
    unittest.main()
