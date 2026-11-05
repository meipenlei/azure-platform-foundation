#!/usr/bin/env python3

"""
Azure Platform Foundation Greenfield end-to-end validation.

This validation harness creates a fresh private GitHub customer repository,
generates a new APF customer implementation from an existing validated source
configuration, executes the Level 0 bootstrap/governance lifecycle, configures
GitHub, and validates the four generated GitHub Actions workflows.

It is intentionally a validation tool, not a normal customer deployment CLI.
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Sequence

import yaml


class GreenfieldValidationError(RuntimeError):
    """Raised when the APF Greenfield E2E validation fails."""


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an APF Level 0 Greenfield end-to-end validation."
    )

    parser.add_argument(
        "--source-config-dir",
        type=Path,
        required=True,
        help=(
            "Existing validated APF config directory used as the Azure "
            "tenant/subscription/region baseline."
        ),
    )

    parser.add_argument(
        "--customer-id",
        default="lab02",
        help="Validation customer ID. Default: lab02.",
    )

    parser.add_argument(
        "--display-name",
        default="APF Greenfield Validation",
        help="Validation customer display name.",
    )

    parser.add_argument(
        "--github-owner",
        required=True,
        help="GitHub owner for the private validation repository.",
    )

    parser.add_argument(
        "--github-repository",
        default=None,
        help=(
            "Private GitHub repository name. "
            "Defaults to <customer-id>-apf-azure-platform."
        ),
    )

    parser.add_argument(
        "--name-prefix",
        default=None,
        help="Azure naming prefix. Defaults to --customer-id.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Local directory for the generated validation customer repo.",
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Create the private repository and real Azure/GitHub validation "
            "resources. Without this flag the tool performs preflight only."
        ),
    )

    parser.add_argument(
        "--skip-workflows",
        action="store_true",
        help="Stop after Azure and GitHub configuration validation.",
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Resume an interrupted validation using an existing private "
            "GitHub repository and generated local customer repository."
        ),
    )

    return parser.parse_args()


def run_command(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    capture_output: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    printable = " ".join(command)
    print(f"+ {printable}")

    result = subprocess.run(
        list(command),
        cwd=str(cwd) if cwd else None,
        check=False,
        capture_output=capture_output,
        text=True,
    )

    if check and result.returncode != 0:
        stdout = result.stdout.strip() if result.stdout else ""
        stderr = result.stderr.strip() if result.stderr else ""

        details = "\n".join(
            part
            for part in (
                stdout,
                stderr,
            )
            if part
        )

        if details:
            raise GreenfieldValidationError(
                f"Command failed ({result.returncode}): "
                f"{printable}\n{details}"
            )

        raise GreenfieldValidationError(
            f"Command failed ({result.returncode}): {printable}"
        )

    return result


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise GreenfieldValidationError(
            f"Required command '{name}' was not found in PATH."
        )


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            data = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError) as exc:
        raise GreenfieldValidationError(
            f"Unable to read YAML file '{path}': {exc}"
        ) from exc

    if not isinstance(
        data,
        dict,
    ):
        raise GreenfieldValidationError(
            f"YAML file '{path}' must contain an object."
        )

    return data


def build_greenfield_configuration(
    *,
    source_config_dir: Path,
    customer_id: str,
    display_name: str,
    github_owner: str,
    github_repository: str,
    name_prefix: str,
) -> dict[str, dict[str, Any]]:
    foundation = copy.deepcopy(
        load_yaml(
            source_config_dir
            / "foundation.yaml"
        )
    )

    customer = copy.deepcopy(
        load_yaml(
            source_config_dir
            / "customer.yaml"
        )
    )

    platform = copy.deepcopy(
        load_yaml(
            source_config_dir
            / "platform.yaml"
        )
    )

    try:
        customer["customer"]["id"] = customer_id
        customer["customer"]["display_name"] = display_name

        platform["deployment"]["mode"] = "greenfield"
        platform["execution"]["provider"] = "github"
        platform["execution"]["github"]["owner"] = github_owner
        platform["execution"]["github"]["repository"] = github_repository
        platform["naming"]["prefix"] = name_prefix
    except (KeyError, TypeError) as exc:
        raise GreenfieldValidationError(
            "The source APF configuration does not contain the expected "
            "customer/platform structure."
        ) from exc

    return {
        "foundation.yaml": foundation,
        "customer.yaml": customer,
        "platform.yaml": platform,
    }


def write_configuration(
    target_dir: Path,
    config: dict[str, dict[str, Any]],
) -> None:
    target_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for filename, payload in config.items():
        with (
            target_dir
            / filename
        ).open(
            "w",
            encoding="utf-8",
        ) as handle:
            yaml.safe_dump(
                payload,
                handle,
                sort_keys=False,
            )


def github_repository_exists(
    repo_slug: str,
) -> bool:
    result = run_command(
        [
            "gh",
            "repo",
            "view",
            repo_slug,
            "--json",
            "name",
        ],
        capture_output=True,
        check=False,
    )

    return result.returncode == 0


def create_private_repository(
    repo_slug: str,
) -> None:
    run_command(
        [
            "gh",
            "repo",
            "create",
            repo_slug,
            "--private",
            "--description",
            "Azure Platform Foundation Greenfield E2E validation",
        ]
    )


def repository_https_url(
    repo_slug: str,
) -> str:
    result = run_command(
        [
            "gh",
            "repo",
            "view",
            repo_slug,
            "--json",
            "url",
            "--jq",
            ".url",
        ],
        capture_output=True,
    )

    value = result.stdout.strip()

    if not value:
        raise GreenfieldValidationError(
            "GitHub did not return the repository HTTPS URL."
        )

    return value


def configure_git_authentication() -> None:
    run_command(
        [
            "gh",
            "auth",
            "setup-git",
        ]
    )




def git_commit_all(
    project_dir: Path,
    message: str,
) -> bool:
    run_command(
        [
            "git",
            "add",
            "-A",
        ],
        cwd=project_dir,
    )

    status = run_command(
        [
            "git",
            "status",
            "--porcelain",
        ],
        cwd=project_dir,
        capture_output=True,
    )

    if not status.stdout.strip():
        print(
            "[PASS] No repository changes require a commit."
        )
        return False

    run_command(
        [
            "git",
            "commit",
            "-m",
            message,
        ],
        cwd=project_dir,
    )

    return True


def initialize_customer_repository(
    *,
    project_dir: Path,
    repo_slug: str,
) -> None:
    configure_git_authentication()

    https_url = repository_https_url(
        repo_slug
    )

    run_command(
        [
            "git",
            "init",
            "-b",
            "main",
        ],
        cwd=project_dir,
    )

    run_command(
        [
            "git",
            "remote",
            "add",
            "origin",
            https_url,
        ],
        cwd=project_dir,
    )

    git_commit_all(
        project_dir,
        "chore: initialize APF Greenfield validation",
    )

    run_command(
        [
            "git",
            "push",
            "-u",
            "origin",
            "main",
        ],
        cwd=project_dir,
    )


def recover_interrupted_local_state_migration(
    project_dir: Path,
) -> None:
    """
    Recover only the specific state where bootstrap resources were created
    using local Terraform state, backend files were generated, but AzureRM
    migration never completed.

    A generated bootstrap snapshot proves that migration completed
    successfully. In that case remote state is authoritative and recovery must
    not touch backend files.
    """

    snapshot = (
        project_dir
        / ".foundation"
        / "level0-bootstrap.yaml"
    )

    if snapshot.is_file():
        print(
            "[PASS] Bootstrap metadata snapshot confirms completed "
            "remote-state migration."
        )
        return

    bootstrap_dir = (
        project_dir
        / "levels"
        / "level0"
        / "bootstrap"
    )

    governance_dir = (
        project_dir
        / "levels"
        / "level0"
        / "governance"
    )

    local_state = (
        bootstrap_dir
        / "terraform.tfstate"
    )

    bootstrap_backend_tf = (
        bootstrap_dir
        / "backend.tf"
    )

    bootstrap_backend_hcl = (
        bootstrap_dir
        / "backend.hcl"
    )

    if not local_state.is_file():
        return

    if not (
        bootstrap_backend_tf.is_file()
        or bootstrap_backend_hcl.is_file()
    ):
        return

    print(
        "[INFO] Local bootstrap state and generated backend files are both "
        "present. Treating this as an interrupted pre-migration Greenfield "
        "bootstrap."
    )

    for path in (
        bootstrap_backend_tf,
        bootstrap_backend_hcl,
        governance_dir / "backend.hcl",
    ):
        if path.exists():
            path.unlink()

    for terraform_dir in (
        bootstrap_dir / ".terraform",
        governance_dir / ".terraform",
    ):
        if terraform_dir.exists():
            shutil.rmtree(
                terraform_dir
            )

    print(
        "[PASS] Restored local bootstrap state mode for safe migration resume."
    )


def resume_customer_repository(
    *,
    project_dir: Path,
    repo_slug: str,
) -> None:
    if not (
        project_dir
        / ".git"
    ).is_dir():
        raise GreenfieldValidationError(
            f"Cannot resume because {project_dir} is not a Git repository."
        )

    configure_git_authentication()

    https_url = repository_https_url(
        repo_slug
    )

    remote = run_command(
        [
            "git",
            "remote",
            "get-url",
            "origin",
        ],
        cwd=project_dir,
        capture_output=True,
        check=False,
    )

    if remote.returncode == 0:
        run_command(
            [
                "git",
                "remote",
                "set-url",
                "origin",
                https_url,
            ],
            cwd=project_dir,
        )
    else:
        run_command(
            [
                "git",
                "remote",
                "add",
                "origin",
                https_url,
            ],
            cwd=project_dir,
        )

    print(
        "[PASS] Existing customer repository prepared for HTTPS GitHub access."
    )

    run_command(
        [
            "git",
            "push",
            "-u",
            "origin",
            "main",
        ],
        cwd=project_dir,
    )




def latest_workflow_run_id(
    repo_slug: str,
    workflow: str,
) -> int | None:
    result = run_command(
        [
            "gh",
            "run",
            "list",
            "--repo",
            repo_slug,
            "--workflow",
            workflow,
            "--event",
            "workflow_dispatch",
            "--limit",
            "1",
            "--json",
            "databaseId",
        ],
        capture_output=True,
    )

    try:
        payload = json.loads(
            result.stdout
        )
    except json.JSONDecodeError as exc:
        raise GreenfieldValidationError(
            "GitHub CLI returned invalid workflow run JSON."
        ) from exc

    if not payload:
        return None

    return int(
        payload[0]["databaseId"]
    )


def trigger_and_watch_workflow(
    *,
    repo_slug: str,
    workflow: str,
) -> int:
    previous = latest_workflow_run_id(
        repo_slug,
        workflow,
    )

    run_command(
        [
            "gh",
            "workflow",
            "run",
            workflow,
            "--repo",
            repo_slug,
            "--ref",
            "main",
        ]
    )

    run_id: int | None = None

    for _ in range(30):
        time.sleep(2)

        candidate = latest_workflow_run_id(
            repo_slug,
            workflow,
        )

        if (
            candidate is not None
            and candidate != previous
        ):
            run_id = candidate
            break

    if run_id is None:
        raise GreenfieldValidationError(
            f"Unable to locate new workflow run for {workflow}."
        )

    run_command(
        [
            "gh",
            "run",
            "watch",
            str(run_id),
            "--repo",
            repo_slug,
            "--exit-status",
        ]
    )

    print(
        f"[PASS] {workflow} run {run_id}"
    )

    return run_id


def validate_pull_request_plan(
    *,
    project_dir: Path,
    repo_slug: str,
) -> None:
    branch = "test/apf-greenfield-plan"
    main_tf = (
        project_dir
        / "levels"
        / "level0"
        / "bootstrap"
        / "main.tf"
    )

    run_command(
        [
            "git",
            "checkout",
            "-b",
            branch,
        ],
        cwd=project_dir,
    )

    original = main_tf.read_text(
        encoding="utf-8"
    )

    main_tf.write_text(
        original
        + "\n# APF Greenfield E2E plan validation\n",
        encoding="utf-8",
    )

    git_commit_all(
        project_dir,
        "test: validate APF Greenfield plan workflow",
    )

    run_command(
        [
            "git",
            "push",
            "-u",
            "origin",
            branch,
        ],
        cwd=project_dir,
    )

    result = run_command(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            repo_slug,
            "--base",
            "main",
            "--head",
            branch,
            "--title",
            "test: validate APF Greenfield plan workflow",
            "--body",
            "Temporary E2E validation PR created by APF.",
        ],
        capture_output=True,
    )

    pr_url = result.stdout.strip()

    if not pr_url:
        raise GreenfieldValidationError(
            "GitHub did not return the validation PR URL."
        )

    try:
        print(
            "Waiting for the pull-request Terraform Plan workflow "
            "to be registered..."
        )

        run_id: int | None = None

        for _ in range(60):
            result = run_command(
                [
                    "gh",
                    "run",
                    "list",
                    "--repo",
                    repo_slug,
                    "--workflow",
                    "terraform-plan.yml",
                    "--event",
                    "pull_request",
                    "--branch",
                    branch,
                    "--limit",
                    "1",
                    "--json",
                    "databaseId",
                ],
                capture_output=True,
            )

            try:
                payload = json.loads(
                    result.stdout
                )
            except json.JSONDecodeError as exc:
                raise GreenfieldValidationError(
                    "GitHub CLI returned invalid pull-request "
                    "workflow run JSON."
                ) from exc

            if payload:
                run_id = int(
                    payload[0]["databaseId"]
                )
                break

            time.sleep(2)

        if run_id is None:
            raise GreenfieldValidationError(
                "The pull-request Terraform Plan workflow was not "
                "registered by GitHub."
            )

        print(
            f"[PASS] Pull-request Terraform Plan workflow registered "
            f"as run {run_id}."
        )

        run_command(
            [
                "gh",
                "run",
                "watch",
                str(run_id),
                "--repo",
                repo_slug,
                "--exit-status",
            ]
        )
    finally:
        run_command(
            [
                "gh",
                "pr",
                "close",
                pr_url,
                "--repo",
                repo_slug,
                "--delete-branch",
            ],
            check=False,
        )

        run_command(
            [
                "git",
                "checkout",
                "main",
            ],
            cwd=project_dir,
            check=False,
        )

        run_command(
            [
                "git",
                "branch",
                "-D",
                branch,
            ],
            cwd=project_dir,
            check=False,
        )

    print(
        "[PASS] terraform-plan.yml pull-request validation."
    )


def main() -> int:
    args = parse_arguments()

    public_repo = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    source_config_dir = (
        args.source_config_dir
        .resolve()
    )

    output_dir = (
        args.output_dir
        .resolve()
    )

    github_repository = (
        args.github_repository
        or f"{args.customer_id}-apf-azure-platform"
    )

    name_prefix = (
        args.name_prefix
        or args.customer_id
    )

    repo_slug = (
        f"{args.github_owner}/"
        f"{github_repository}"
    )

    config_work_dir = (
        output_dir.parent
        / f".{args.customer_id}-apf-e2e-config"
    )

    print(
        "Azure Platform Foundation Greenfield E2E Validation"
    )
    print(
        "--------------------------------------------------"
    )
    print(f"Customer ID: {args.customer_id}")
    print(f"GitHub:      {repo_slug}")
    print(f"Output:      {output_dir}")
    print()

    try:
        for command in (
            "az",
            "gh",
            "git",
            "terraform",
        ):
            require_command(
                command
            )

        if not source_config_dir.is_dir():
            raise GreenfieldValidationError(
                f"Source config directory does not exist: "
                f"{source_config_dir}"
            )

        output_exists = output_dir.exists()
        repository_exists = github_repository_exists(
            repo_slug
        )

        if args.resume:
            if not output_exists:
                raise GreenfieldValidationError(
                    f"Cannot resume because the output directory does not "
                    f"exist: {output_dir}"
                )

            if not repository_exists:
                raise GreenfieldValidationError(
                    f"Cannot resume because the GitHub repository does not "
                    f"exist: {repo_slug}"
                )
        else:
            if output_exists:
                raise GreenfieldValidationError(
                    f"Output directory already exists: {output_dir}. "
                    "Use --resume only for an interrupted validation."
                )

            if repository_exists:
                raise GreenfieldValidationError(
                    f"GitHub repository already exists: {repo_slug}. "
                    "A true Greenfield validation requires a fresh repository, "
                    "or use --resume for an interrupted validation."
                )

        config = build_greenfield_configuration(
            source_config_dir=source_config_dir,
            customer_id=args.customer_id,
            display_name=args.display_name,
            github_owner=args.github_owner,
            github_repository=github_repository,
            name_prefix=name_prefix,
        )

        print(
            "[PASS] Greenfield validation configuration can be derived."
        )

        if args.resume:
            print(
                "[PASS] Existing interrupted validation target is available."
            )
        else:
            print(
                "[PASS] Target GitHub repository name is currently unused."
            )

        if not args.apply:
            print()
            print(
                "Preflight completed successfully."
            )
            if args.resume:
                print(
                    "No existing validation resources were changed."
                )
            else:
                print(
                    "No GitHub repository or Azure resources were created."
                )
            print()
            print(
                "Run the same command with --apply to execute the "
                "Greenfield E2E validation."
            )
            return 0

        if args.resume:
            print()
            print("Resuming existing Greenfield validation repository...")

            recover_interrupted_local_state_migration(
                output_dir
            )

            resume_customer_repository(
                project_dir=output_dir,
                repo_slug=repo_slug,
            )

        else:
            print()
            print("Creating private GitHub validation repository...")
            create_private_repository(
                repo_slug
            )

            write_configuration(
                config_work_dir,
                config,
            )

            print()
            print("Generating APF customer repository...")
            run_command(
                [
                    sys.executable,
                    str(
                        public_repo
                        / "tooling"
                        / "customer-init"
                        / "init.py"
                    ),
                    "--config-dir",
                    str(
                        config_work_dir
                    ),
                    "--output-dir",
                    str(
                        output_dir
                    ),
                ]
            )

            initialize_customer_repository(
                project_dir=output_dir,
                repo_slug=repo_slug,
            )

        print()
        print(
            "Executing Level 0 bootstrap and governance lifecycle..."
        )
        run_command(
            [
                sys.executable,
                str(
                    public_repo
                    / "tooling"
                    / "customer-bootstrap"
                    / "bootstrap.py"
                ),
                "--project-dir",
                str(
                    output_dir
                ),
                "--governance",
                "--apply",
            ]
        )

        if git_commit_all(
            output_dir,
            "chore: complete APF Level 0 bootstrap",
        ):
            run_command(
                [
                    "git",
                    "push",
                    "origin",
                    "main",
                ],
                cwd=output_dir,
            )

        print()
        print("Configuring GitHub execution plane...")
        run_command(
            [
                sys.executable,
                str(
                    public_repo
                    / "tooling"
                    / "customer-github"
                    / "configure.py"
                ),
                "--project-dir",
                str(
                    output_dir
                ),
                "--apply",
            ]
        )

        print()
        print("Verifying GitHub configuration idempotency...")
        verify = run_command(
            [
                sys.executable,
                str(
                    public_repo
                    / "tooling"
                    / "customer-github"
                    / "configure.py"
                ),
                "--project-dir",
                str(
                    output_dir
                ),
            ],
            capture_output=True,
        )

        if (
            "No changes. GitHub configuration matches APF desired state."
            not in verify.stdout
        ):
            raise GreenfieldValidationError(
                "customer-github did not converge to a no-change state."
            )

        print(
            "[PASS] GitHub configuration is idempotent."
        )

        if args.skip_workflows:
            print()
            print(
                "Greenfield Azure/GitHub lifecycle validation completed."
            )
            print(
                "Workflow validation was skipped by request."
            )
            return 0

        print()
        print("Validating GitHub pull-request plan workflow...")
        validate_pull_request_plan(
            project_dir=output_dir,
            repo_slug=repo_slug,
        )

        print()
        print("Validating GitHub workflow_dispatch workflows...")

        for workflow in (
            "terraform-apply.yml",
            "terraform-governance-plan.yml",
            "terraform-governance-apply.yml",
        ):
            trigger_and_watch_workflow(
                repo_slug=repo_slug,
                workflow=workflow,
            )

        print()
        print(
            "APF Greenfield Level 0 E2E validation completed successfully."
        )
        print()
        print(
            "Validated:"
        )
        print(
            "  customer-init"
        )
        print(
            "  bootstrap local state -> AzureRM state migration"
        )
        print(
            "  governance handover and separate state"
        )
        print(
            "  GitHub environments, variables and deployment protection"
        )
        print(
            "  PR plan workflow"
        )
        print(
            "  apply workflow"
        )
        print(
            "  governance plan workflow"
        )
        print(
            "  governance apply workflow"
        )
        print()
        print(
            "The validation environment is intentionally retained for "
            "inspection. Automated destruction is not part of Commit 8."
        )

        return 0

    except GreenfieldValidationError as exc:
        print()
        print(
            f"[ERROR] {exc}",
            file=sys.stderr,
        )
        print()
        print(
            "The validation environment is retained for inspection. "
            "Do not delete state or Azure resources manually until the "
            "failure has been understood.",
            file=sys.stderr,
        )
        return 2

    except KeyboardInterrupt:
        print()
        print(
            "[ERROR] Greenfield validation interrupted. "
            "The environment is retained for inspection.",
            file=sys.stderr,
        )
        return 130

    finally:
        if config_work_dir.exists():
            shutil.rmtree(
                config_work_dir,
                ignore_errors=True,
            )


if __name__ == "__main__":
    sys.exit(main())
