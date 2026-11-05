# APF Customer GitHub Configuration

`customer-github` configures the GitHub side of an Azure Platform Foundation
customer repository after the Level 0 bootstrap/governance lifecycle exists.

It is intentionally separate from:

- `customer-init`: deterministic repository generation
- `customer-bootstrap`: privileged Azure/Terraform lifecycle
- `customer-github`: GitHub environment, variable and OIDC validation

## Design

APF uses GitHub Actions **variables**, not Actions secrets, for Azure identifiers.

The following values are identifiers and are not credentials:

- Azure tenant ID
- Azure subscription ID
- managed identity client IDs

No password, client secret, storage key, private key, PAT, or other long-lived
Azure credential is stored by this tool.

## Deployment protection baseline

APF restricts both privileged GitHub environments to the repository's current
default branch.

For a repository whose default branch is `main`, the desired state is:

    apf-level0:
      deployment branches: main only

    apf-governance:
      deployment branches: main only

The default branch is discovered from GitHub; it is not hard-coded.

Commit 7 intentionally does not configure required reviewers or wait timers.
Those controls vary by GitHub plan for private repositories and should become
explicit organization/customer policy later.

## Desired GitHub configuration


Repository Actions variables:

    AZURE_TENANT_ID
    AZURE_SUBSCRIPTION_ID
    AZURE_PLAN_CLIENT_ID

Environment:

    apf-level0

Environment Actions variable:

    AZURE_APPLY_CLIENT_ID

Environment:

    apf-governance

Environment Actions variable:

    AZURE_GOVERNANCE_CLIENT_ID

The repository-level tenant/subscription variables are available to all APF
workflows. The privileged identity client IDs remain scoped to their deployment
environments.

## OIDC subject validation

Before changing GitHub, the tool discovers the current immutable GitHub owner
and repository IDs and validates the three subjects stored in the Azure
bootstrap state:

    plan:
      repo:<owner>@<owner-id>/<repo>@<repo-id>:pull_request

    apply:
      repo:<owner>@<owner-id>/<repo>@<repo-id>:environment:apf-level0

    governance:
      repo:<owner>@<owner-id>/<repo>@<repo-id>:environment:apf-governance

If any subject differs, the tool stops instead of configuring a repository
whose Azure federation no longer matches its GitHub identity.

## Prerequisites

- Terraform 1.17.x
- GitHub CLI (`gh`)
- authenticated GitHub CLI session
- sufficient GitHub repository permissions
- completed Level 0 bootstrap lifecycle
- bootstrap remote backend (`backend.hcl`)
- current APF GitHub workflows using `vars.AZURE_*`

Install Python dependencies:

    python -m pip install \
      -r tooling/customer-github/requirements.txt

## Read-only plan

    python tooling/customer-github/configure.py \
      --project-dir ../lab01-apf-azure-platform

The tool:

1. validates the APF workflow contract
2. validates GitHub authentication
3. discovers immutable owner/repository IDs
4. reads bootstrap outputs
5. validates all OIDC subjects
6. compares environments and variable values
7. compares privileged environment deployment branch policies
8. prints the planned GitHub changes

No GitHub configuration is changed.

## Apply

    python tooling/customer-github/configure.py \
      --project-dir ../lab01-apf-azure-platform \
      --apply

This creates missing environments, creates/updates variables, restricts both
privileged environments to the repository default branch, and verifies the
final desired state.

## Existing repositories

Commit 6 changes the generated APF workflows from:

    secrets.AZURE_*

to:

    vars.AZURE_*

Existing customer repositories must update their four Level 0 workflow files
before running `customer-github`.

The safest migration is to regenerate the customer project into a temporary
directory with the current `customer-init` and copy only `.github/workflows/`
into the existing customer repository.

## What Commit 6 does not configure yet

Commit 6 does not impose organization-specific deployment protection policy.

For example, it does not yet choose:

- required reviewers
- wait timers
- branch/tag deployment policies
- organization rulesets

Those controls should become policy-driven configuration rather than hard-coded
defaults.
