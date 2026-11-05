# APF Customer Bootstrap

`customer-bootstrap` performs the privileged local bootstrap lifecycle for a
generated Azure Platform Foundation customer repository.

It is deliberately separate from `customer-init`.

- `customer-init` is deterministic repository generation.
- `customer-bootstrap` performs privileged Azure lifecycle operations.

## Commit 4 scope

The current implementation:

1. validates the generated customer repository
2. checks Terraform and Azure CLI
3. verifies the configured Azure tenant and subscription
4. initializes the Level 0 bootstrap root
5. runs `terraform fmt`, `terraform validate`, and `terraform plan`
6. applies the bootstrap only when `--apply` is supplied
7. reads the bootstrap Terraform outputs
8. generates:
   - `levels/level0/bootstrap/backend.tf`
   - `levels/level0/bootstrap/backend.hcl`
   - `levels/level0/governance/backend.hcl`
9. temporarily grants the signed-in bootstrap user
   `Storage Blob Data Contributor` on the Terraform state container when needed
10. migrates the bootstrap state from local state to Azure
11. verifies that the remote state is readable
12. removes temporary state-container access by default

Governance plan/apply and GitHub environment configuration are intentionally
deferred to the next lifecycle stage.

## Prerequisites

The operator must have:

- Terraform 1.17.x
- Azure CLI
- an authenticated Azure CLI session (`az login`)
- sufficient Azure permissions to deploy the Level 0 bootstrap
- sufficient RBAC permissions to create a temporary state-container role
  assignment during migration

The generated customer repository must already exist.


## Existing APF repositories

`customer-bootstrap` also supports APF customer repositories that were created
before `customer-init` generated `.foundation/discovery.yaml` and
`generated.auto.tfvars.json`.

In that compatibility mode, Azure tenant and bootstrap subscription identifiers
are read from `config/customer.yaml`. Existing Terraform input files remain
authoritative for the Terraform root; the bootstrap tool does not silently
rewrite them.

## Safe first run

From the public APF repository:

    python tooling/customer-bootstrap/bootstrap.py \
      --project-dir ../lab01-apf-azure-platform

Without `--apply`, the tool performs preflight checks, initialization,
validation, and a Terraform plan only.

No Azure changes are applied.

## Execute the bootstrap lifecycle

    python tooling/customer-bootstrap/bootstrap.py \
      --project-dir ../lab01-apf-azure-platform \
      --apply

This performs the Level 0 bootstrap and remote-state migration.

## State files

The lifecycle uses these deterministic AzureRM backend keys:

    level0.bootstrap.tfstate
    level0.governance.tfstate

`backend.hcl` contains Azure identifiers and backend settings. It does not
contain passwords, access keys, client secrets, or tokens.

## Temporary state access

Because the APF state storage account uses Microsoft Entra authentication and
shared-key access is disabled, the local bootstrap user may require temporary
data-plane access to migrate the Terraform state.

If the signed-in user does not already have it, `customer-bootstrap` creates:

    Storage Blob Data Contributor

at the Terraform state-container scope.

The role assignment is removed after successful migration or after a migration
failure.

For troubleshooting only, it can be retained with:

    --keep-temporary-state-access

The secure default is to remove it.

## Idempotent reruns

If both `bootstrap/backend.tf` and `bootstrap/backend.hcl` already exist, the
tool treats the bootstrap as remote-state enabled. It preserves the existing
backend files, reinitializes the AzureRM backend, and continues with plan/apply
without attempting another state migration.

If only one of those two files exists, the tool stops rather than guessing
about an incomplete lifecycle state.

## Next stage

The next APF lifecycle stage will perform the governance handover:

- derive governance inputs from bootstrap outputs
- initialize the governance state
- run governance plan/apply
- prepare GitHub environments and workload-identity configuration
