#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parent / "configure.py"
)

spec = importlib.util.spec_from_file_location(
    "apf_customer_github_configure",
    MODULE_PATH,
)

assert spec is not None
assert spec.loader is not None

configure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(configure)


class CustomerGitHubPolicyTests(unittest.TestCase):
    def test_environment_custom_policy_mode(self) -> None:
        self.assertTrue(
            configure.environment_has_custom_branch_policy_mode(
                {
                    "deployment_branch_policy": {
                        "protected_branches": False,
                        "custom_branch_policies": True,
                    }
                }
            )
        )

    def test_environment_all_branches_is_not_custom_mode(self) -> None:
        self.assertFalse(
            configure.environment_has_custom_branch_policy_mode(
                {
                    "deployment_branch_policy": None,
                }
            )
        )

    def test_expected_oidc_subjects(self) -> None:
        subjects = configure.expected_oidc_subjects(
            {
                "owner": "example",
                "owner_id": "100",
                "repository": "platform",
                "repository_id": "200",
            }
        )

        self.assertEqual(
            subjects["github_plan_subject"],
            "repo:example@100/platform@200:pull_request",
        )

        self.assertEqual(
            subjects["github_apply_subject"],
            "repo:example@100/platform@200:environment:apf-level0",
        )

        self.assertEqual(
            subjects["github_governance_subject"],
            "repo:example@100/platform@200:environment:apf-governance",
        )


if __name__ == "__main__":
    unittest.main()
