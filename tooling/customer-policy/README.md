# APF Customer Policy Configurator

This tool generates the first EPAC desired-state configuration in an existing
APF customer repository.

Commit 11 is deliberately **plan-only**.

## Safety model

The generated policy workflow:

- runs on pull requests only;
- authenticates with `AZURE_PLAN_CLIENT_ID`;
- uses OIDC;
- uses the existing subscription `Reader` permission;
- invokes `Build-DeploymentPlans`;
- never invokes `Deploy-PolicyPlan`;
- never invokes `Deploy-RolesPlan`.

The privileged Governance UAMI is not used by Commit 11.

## Dry run

    python tooling/customer-policy/configure.py \
      --project-dir ../lab04-apf-azure-platform

## Generate

    python tooling/customer-policy/configure.py \
      --project-dir ../lab04-apf-azure-platform \
      --apply

The command is deterministic and idempotent.

## Generated customer files

    .foundation/policy.yaml
    .github/workflows/policy-plan.yml
    governance/policy/README.md
    governance/policy/Definitions/global-settings.jsonc
    governance/policy/Definitions/policyAssignments/
        apf-audit-public-ip.assignment.jsonc

The tool also ensures that `governance/policy/Output/` is ignored by Git.

## First pilot assignment

The pilot preserves the legacy `CAF-Deny-Public-IP` behavior:

- Microsoft built-in "Not allowed resource types";
- resource type `Microsoft.Network/publicIPAddresses`;
- `effect=Audit`;
- `enforcementMode=Default`.

It is scoped to the bootstrap subscription.

Full ALZ/SLZ archetype synchronization starts only after the Level 1
management-group hierarchy exists.
