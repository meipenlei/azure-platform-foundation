# APF Customer Bootstrap

`customer-bootstrap` performs the privileged local Level 0 lifecycle for a
generated or existing Azure Platform Foundation customer repository.

It is deliberately separate from `customer-init`.

- `customer-init` is deterministic repository generation.
- `customer-bootstrap` performs privileged Azure lifecycle operations.

## Current scope

The tool supports two lifecycle stages.

### Bootstrap

The bootstrap stage:

1. validates the APF customer repository
2. checks Terraform and Azure CLI
3. verifies Azure tenant/subscription context
4. initializes and validates the Level 0 bootstrap root
5. creates a bootstrap Terraform plan
6. applies the bootstrap only when `--apply` is supplied
7. reads bootstrap outputs
8. creates backend configuration for a new Greenfield bootstrap
9. migrates local bootstrap state to Azure when required
10. verifies the remote bootstrap state

### Governance handover

With `--governance`, the tool additionally:

1. reads `governance_identity_principal_id` and `state_container_id` from the
   bootstrap Terraform outputs
2. derives the governance Terraform variables in memory
3. preserves an existing governance backend or generates `backend.hcl` during
   an apply lifecycle when it does not yet exist
4. initializes the independent governance Terraform state
5. validates and plans governance
6. applies governance only when `--apply` is also supplied
7. verifies that the governance remote state is readable

The governance Terraform root remains responsible for the privileged role
assignments. The bootstrap state does not take ownership of those assignments.

## Prerequisites

The operator must have:

- Terraform 1.17.x
- Azure CLI
- an authenticated Azure CLI session (`az login`)
- sufficient Azure permissions for the bootstrap
- sufficient RBAC permissions for the governance role assignments
- state-container data access for local Terraform backend operations

`requirements.txt` contains the Python dependency used to read APF YAML
configuration.

## Bootstrap plan only

    python tooling/customer-bootstrap/bootstrap.py \
      --project-dir ../lab01-apf-azure-platform

This runs the bootstrap preflight and Terraform plan only.

## Bootstrap apply

    python tooling/customer-bootstrap/bootstrap.py \
      --project-dir ../lab01-apf-azure-platform \
      --apply

This executes the bootstrap lifecycle. On a new Greenfield environment it also
performs backend creation/state migration. On an already remote environment it
preserves the existing backend files.

## Bootstrap + governance plan

    python tooling/customer-bootstrap/bootstrap.py \
      --project-dir ../lab01-apf-azure-platform \
      --governance

This performs a bootstrap plan and then a governance plan against the current
bootstrap state. It does not apply Azure changes.

For a brand-new Greenfield environment, governance cannot be planned until the
bootstrap has created the required identities and state backend.

## Bootstrap + governance apply

    python tooling/customer-bootstrap/bootstrap.py \
      --project-dir ../lab01-apf-azure-platform \
      --governance \
      --apply

This performs the complete current Level 0 local lifecycle:

    bootstrap plan
      -> bootstrap apply
      -> bootstrap state/backend verification
      -> derive governance inputs from bootstrap outputs
      -> governance init
      -> governance plan
      -> governance apply
      -> governance state verification

## State separation

The lifecycle uses deterministic AzureRM backend keys:

    level0.bootstrap.tfstate
    level0.governance.tfstate

This preserves the APF security boundary:

- bootstrap state owns Level 0 infrastructure and execution identities
- governance state owns privileged governance RBAC

## Governance inputs

The tool does not maintain a customer-authored governance tfvars file.

These values are derived from the current bootstrap state and passed to
Terraform through process environment variables:

    TF_VAR_tenant_id
    TF_VAR_subscription_id
    TF_VAR_governance_principal_id
    TF_VAR_state_container_id

This keeps the bootstrap state authoritative for generated identity/resource
identifiers while avoiding long-lived credentials.

## Existing APF repositories

Repositories created before the current `customer-init` format are supported.

If `generated.auto.tfvars.json` is not present, Azure tenant and bootstrap
subscription identifiers are read from `config/customer.yaml`.

Existing backend files are preserved.

## Security

`customer-bootstrap` does not require client secrets or storage account keys.

Terraform state access uses Microsoft Entra authentication.

When a Greenfield state migration requires temporary local data-plane access,
the tool grants the signed-in bootstrap user `Storage Blob Data Contributor`
at state-container scope and removes the temporary assignment by default.

## Next lifecycle stage

A later stage can automate GitHub configuration:

- GitHub environments
- repository/environment variables or secrets containing non-secret client IDs
- validation of OIDC federation subjects
- transition from local privileged bootstrap execution to normal GitHub
  plan/apply/governance pipelines
