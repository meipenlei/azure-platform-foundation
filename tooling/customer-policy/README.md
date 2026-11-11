# APF Customer Policy Configurator

This tool generates the EPAC desired-state configuration in an existing APF
customer repository.

Commit 14 introduces the first **scope-aware Audit-First Wave 1**.

## Required Level 1 input

The configurator requires:

    .foundation/level1-management-groups.yaml

The EPAC deployment root remains the APF root management group, while each
policy assignment resolves its target management group from
`management_group_ids` in that snapshot.

There is no scope fallback and no inferred `security` mapping.

## Wave 1 assignments

| Upstream assignment | Legacy archetype | APF scope | Preserved behavior |
| --- | --- | --- | --- |
| `Deny-Public-IP` | `es_identity` | `identity` | `Default`, `effect=Audit` |
| `Deny-Classic-Resources` | `es_root` | `root` | `DoNotEnforce`, `effect=Deny` |
| `Deny-Storage-http` | `es_landing_zones` | `landing_zones` | `DoNotEnforce`, `effect=Deny` |
| `Deny-HybridNetworking` | `es_corp` | `corp` | `DoNotEnforce`, `effect=Deny` |

These assignments use built-in policy definitions and require no managed
identity or policy-assignment RBAC.

## Safety model

The generated policy workflow:

- runs on pull requests only;
- authenticates with `AZURE_PLAN_CLIENT_ID`;
- uses OIDC;
- invokes `Build-DeploymentPlans`;
- never invokes `Deploy-PolicyPlan`;
- never invokes `Deploy-RolesPlan`.

The Governance UAMI is still not used by the policy-plan workflow.

## Dry run

    python tooling/customer-policy/configure.py \
      --project-dir ../lab04-apf-azure-platform

## Generate

    python tooling/customer-policy/configure.py \
      --project-dir ../lab04-apf-azure-platform \
      --apply

The command is deterministic and idempotent.

## Deliberately deferred

Legacy assignments from the `security` archetype are not included in Wave 1.
APF does not yet have an explicit target scope for that horizontal archetype,
so the generator refuses to guess one.
