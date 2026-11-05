# APF Greenfield E2E Validation

This tool validates the complete Azure Platform Foundation Level 0 Greenfield
lifecycle against a real Azure subscription and a fresh private GitHub
repository.

It is a product validation harness. It is not intended to replace the normal
customer lifecycle tools.

## What it proves

A successful run proves that APF can move from customer intent to an operational
Level 0 execution plane without manual Terraform imports, RBAC repair, backend
file authoring, or GitHub secret configuration.

The sequence is:

    source customer config
      -> fresh private GitHub repository
      -> customer-init
      -> initial customer commit
      -> customer-bootstrap --governance --apply
      -> local bootstrap state migrated to Azure
      -> governance state created
      -> generated bootstrap metadata snapshot
      -> generated backend files committed
      -> customer-github --apply
      -> GitHub configuration idempotency check
      -> pull-request plan workflow
      -> apply workflow
      -> governance plan workflow
      -> governance apply workflow

## Safety

Without `--apply`, the tool performs preflight only.

With `--apply`, it creates real Azure resources and a real private GitHub
repository.

Commit 8 deliberately does not automate destruction. If the test fails, the
environment is retained for inspection.

## Recommended lab02 run

From the public APF repository:

    python tooling/greenfield-e2e/validate.py \
      --source-config-dir ../lab01-apf-azure-platform/config \
      --customer-id lab02 \
      --display-name "APF Greenfield Validation" \
      --github-owner meipenlei \
      --github-repository lab02-apf-azure-platform \
      --name-prefix lab02 \
      --output-dir ../lab02-apf-azure-platform

Run this first without `--apply`.

If preflight is clean, add:

    --apply

## Why an existing source config is used

The validation needs a real Azure tenant ID, bootstrap subscription ID, cloud
selection and region.

Rather than duplicate those identifiers in a special test format, the harness
copies an already valid APF configuration and changes only the Greenfield test
identity:

- customer ID
- display name
- deployment mode
- GitHub owner/repository
- naming prefix

The normal APF schema validation still runs inside `customer-init`.

## Expected result

A successful run ends with:

    APF Greenfield Level 0 E2E validation completed successfully.

and confirms all four GitHub workflows.

## Cleanup

Automated teardown is intentionally deferred to a later commit because safe
destruction must respect the independent governance and bootstrap states.

Do not simply delete the state container before the Azure resources have been
destroyed in the correct order.


## Non-interactive Git authentication

The E2E harness uses the GitHub CLI credential helper and an HTTPS Git remote.

It deliberately does not use the repository SSH URL. This avoids an
interactive SSH host-key confirmation on machines that have never connected to
GitHub over SSH.

## Resume an interrupted validation

If a run was interrupted after the GitHub repository and local generated
customer repository were created, rerun the same command with:

    --apply \
    --resume

The tool reuses the existing private repository, changes the local Git remote
to authenticated HTTPS, pushes the existing `main` commit if necessary, and
continues with bootstrap, governance, GitHub configuration and workflow tests.


## Interrupted state-migration recovery

If bootstrap resources were successfully created in local state but the first
AzureRM backend migration failed, `--resume` detects the combination of:

- local `terraform.tfstate`
- generated bootstrap backend files

It removes only the generated backend files and `.terraform` backend cache,
never the local Terraform state. The lifecycle then re-plans against the local
state and retries the migration after Azure Storage data-plane authorization is
confirmed.


## Pull-request workflow registration

GitHub can briefly report no PR checks immediately after pull-request creation,
even though the workflow will be registered moments later.

The Greenfield harness therefore does not call `gh pr checks --watch`
immediately. It first polls GitHub Actions for the matching
`terraform-plan.yml` pull-request run and then watches that concrete run ID.

## Resume after successful state migration

`.foundation/level0-bootstrap.yaml` is treated as the completion marker for the
bootstrap state migration. If this snapshot exists, `--resume` will preserve
the generated backend files and remote-state configuration.
