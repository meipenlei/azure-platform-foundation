from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


MODULE_PATH = Path(__file__).with_name("verify_apply_plan.py")
SPEC = importlib.util.spec_from_file_location(
    "apf_verify_apply_plan",
    MODULE_PATH,
)
assert SPEC is not None
assert SPEC.loader is not None
verify_apply_plan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify_apply_plan)


OWNER = "11111111-2222-3333-4444-555555555555"
ROOT_SCOPE = "/providers/Microsoft.Management/managementGroups/lab"
ASSIGNMENT_NAME = "apf-audit-public-ip"
ASSIGNMENT_ID = (
    ROOT_SCOPE
    + "/providers/Microsoft.Authorization/policyAssignments/"
    + ASSIGNMENT_NAME
)


class VerifyApplyPlanTests(unittest.TestCase):
    def make_definitions(self, root: Path) -> Path:
        definitions = root / "Definitions"
        assignment_dir = definitions / "policyAssignments"
        assignment_dir.mkdir(parents=True)

        (definitions / "global-settings.jsonc").write_text(
            json.dumps(
                {
                    "pacOwnerId": OWNER,
                    "pacEnvironments": [],
                }
            ),
            encoding="utf-8",
        )

        (assignment_dir / "test.assignment.jsonc").write_text(
            json.dumps(
                {
                    "assignment": {
                        "name": ASSIGNMENT_NAME,
                        "displayName": "Test",
                    },
                    "scope": {
                        "apf-governance": [ROOT_SCOPE],
                    },
                }
            ),
            encoding="utf-8",
        )

        return definitions

    def write_policy_plan(
        self,
        path: Path,
        *,
        new: dict | None = None,
        update: dict | None = None,
        replace: dict | None = None,
        delete: dict | None = None,
        policy_definitions: dict | None = None,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "pacOwnerId": OWNER,
                    "policyDefinitions": policy_definitions
                    or {
                        "new": {},
                        "update": {},
                        "replace": {},
                        "delete": {},
                    },
                    "policySetDefinitions": {
                        "new": {},
                        "update": {},
                        "replace": {},
                        "delete": {},
                    },
                    "assignments": {
                        "new": new or {},
                        "update": update or {},
                        "replace": replace or {},
                        "delete": delete or {},
                    },
                    "exemptions": {
                        "new": {},
                        "update": {},
                        "replace": {},
                        "delete": {},
                    },
                    "enrollments": {
                        "new": {},
                        "update": {},
                        "replace": {},
                        "delete": {},
                    },
                }
            ),
            encoding="utf-8",
        )

    def write_roles_plan(
        self,
        path: Path,
        *,
        added: list | None = None,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "pacOwnerId": OWNER,
                    "roleAssignments": {
                        "added": added or [],
                        "updated": [],
                        "removed": [],
                    },
                }
            ),
            encoding="utf-8",
        )

    def args(
        self,
        *,
        definitions: Path,
        policy_plan: Path,
        roles_plan: Path,
        mode: str,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            mode=mode,
            definitions_root=definitions,
            pac_selector="apf-governance",
            policy_plan=policy_plan,
            roles_plan=roles_plan,
        )

    def test_pre_apply_allows_known_additive_assignment(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            definitions = self.make_definitions(root)
            policy_plan = root / "Output/policy-plan.json"
            roles_plan = root / "Output/roles-plan.json"

            self.write_policy_plan(
                policy_plan,
                new={ASSIGNMENT_ID: {"displayName": "Test"}},
            )

            result = verify_apply_plan.verify(
                self.args(
                    definitions=definitions,
                    policy_plan=policy_plan,
                    roles_plan=roles_plan,
                    mode="pre-apply",
                )
            )

            self.assertEqual(result, (1, 0))

    def test_pre_apply_rejects_assignment_delete(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            definitions = self.make_definitions(root)
            policy_plan = root / "Output/policy-plan.json"
            roles_plan = root / "Output/roles-plan.json"

            self.write_policy_plan(
                policy_plan,
                delete={ASSIGNMENT_ID: {"displayName": "Test"}},
            )

            with self.assertRaises(
                verify_apply_plan.PlanVerificationError
            ):
                verify_apply_plan.verify(
                    self.args(
                        definitions=definitions,
                        policy_plan=policy_plan,
                        roles_plan=roles_plan,
                        mode="pre-apply",
                    )
                )

    def test_pre_apply_rejects_unknown_assignment(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            definitions = self.make_definitions(root)
            policy_plan = root / "Output/policy-plan.json"
            roles_plan = root / "Output/roles-plan.json"

            unknown = (
                ROOT_SCOPE
                + "/providers/Microsoft.Authorization/policyAssignments/"
                + "not-generated"
            )
            self.write_policy_plan(
                policy_plan,
                new={unknown: {"displayName": "Unexpected"}},
            )

            with self.assertRaises(
                verify_apply_plan.PlanVerificationError
            ):
                verify_apply_plan.verify(
                    self.args(
                        definitions=definitions,
                        policy_plan=policy_plan,
                        roles_plan=roles_plan,
                        mode="pre-apply",
                    )
                )

    def test_pre_apply_rejects_role_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            definitions = self.make_definitions(root)
            policy_plan = root / "Output/policy-plan.json"
            roles_plan = root / "Output/roles-plan.json"

            self.write_policy_plan(
                policy_plan,
                new={ASSIGNMENT_ID: {"displayName": "Test"}},
            )
            self.write_roles_plan(
                roles_plan,
                added=[{"scope": ROOT_SCOPE}],
            )

            with self.assertRaises(
                verify_apply_plan.PlanVerificationError
            ):
                verify_apply_plan.verify(
                    self.args(
                        definitions=definitions,
                        policy_plan=policy_plan,
                        roles_plan=roles_plan,
                        mode="pre-apply",
                    )
                )

    def test_post_apply_accepts_missing_plan_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            definitions = self.make_definitions(root)

            result = verify_apply_plan.verify(
                self.args(
                    definitions=definitions,
                    policy_plan=root / "missing-policy-plan.json",
                    roles_plan=root / "missing-roles-plan.json",
                    mode="post-apply",
                )
            )

            self.assertEqual(result, (0, 0))

    def test_post_apply_marks_remaining_expected_assignment_retryable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            definitions = self.make_definitions(root)
            policy_plan = root / "Output/policy-plan.json"
            roles_plan = root / "Output/roles-plan.json"

            self.write_policy_plan(
                policy_plan,
                new={ASSIGNMENT_ID: {"displayName": "Test"}},
            )

            with self.assertRaises(
                verify_apply_plan.RetryableConvergenceError
            ):
                verify_apply_plan.verify(
                    self.args(
                        definitions=definitions,
                        policy_plan=policy_plan,
                        roles_plan=roles_plan,
                        mode="post-apply",
                    )
                )


    def test_main_returns_retry_exit_code_for_expected_post_apply_new(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            definitions = self.make_definitions(root)
            policy_plan = root / "Output/policy-plan.json"
            roles_plan = root / "Output/roles-plan.json"

            self.write_policy_plan(
                policy_plan,
                new={ASSIGNMENT_ID: {"displayName": "Test"}},
            )

            original_parse_args = verify_apply_plan.parse_args
            try:
                verify_apply_plan.parse_args = lambda: self.args(
                    definitions=definitions,
                    policy_plan=policy_plan,
                    roles_plan=roles_plan,
                    mode="post-apply",
                )
                self.assertEqual(verify_apply_plan.main(), 3)
            finally:
                verify_apply_plan.parse_args = original_parse_args


if __name__ == "__main__":
    unittest.main()
