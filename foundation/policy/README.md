# Azure Platform Foundation Policy Layer

The APF Policy Layer implements Governance as Code for Azure Policy.

## Ownership boundary

APF deliberately separates infrastructure ownership from policy ownership.

| Capability | Declarative owner |
| --- | --- |
| Management groups | Terraform / APF |
| Platform managed identities | Terraform / APF |
| Platform RBAC | Terraform / APF |
| Azure Policy definitions | EPAC |
| Azure Policy set definitions | EPAC |
| Azure Policy assignments | EPAC |
| Azure Policy exemptions | EPAC |
| Policy-assignment role requirements | EPAC |

Terraform must not manage policy resources that are owned by EPAC.

## Source of truth

Policy content remains Azure-native JSON/JSONC wherever practical.

APF consumes the Microsoft Azure Landing Zones Library as an upstream,
versioned dependency and layers APF-specific policy configuration on top.

Pinned versions live in:

    foundation/policy/versions.json

## Desired-state strategy

APF uses two explicit desired-state modes:

- Brownfield adoption starts with `ownedOnly`.
- Greenfield targets `full` only after the intended policy baseline has been
  populated and reviewed.

A portal change is not a durable configuration change. A durable change must be
represented in source control.

## Migration baseline

The legacy HCI policy library is classified against the pinned ALZ/SLZ
releases. Legacy effects, enforcement modes and archetype placement are
migration inputs and must not be normalized away.

## Commit 14 — Scope-aware Audit-First Wave 1

The Wave 1 profile is:

    foundation/policy/profiles/enterprise/audit-first-wave1.json

It established four curated assignments:

    CAF-Deny-Public-IP      -> identity
    Deny-Classic-Resources  -> root
    Deny-Storage-http       -> landing_zones
    Deny-HybridNetworking   -> corp

At the Commit 14 boundary the lifecycle was still plan-only.

## Commit 15 — Protected Policy Apply

Commit 15 introduced the first Azure mutation path for the reviewed desired
state without adding policy content.

The generated customer workflow is:

    .github/workflows/policy-apply.yml

It is manual-only, restricted to `main`, uses the `apf-governance` GitHub
environment and authenticates with the Governance UAMI through OIDC.

Before deployment, EPAC rebuilds the plan from the current `main` branch. APF
then verifies that the plan contains only additive Policy Assignments already
represented in the generated Definitions tree. Deletes, replacements, updates,
Policy Definition/Set changes, exemptions and Role Assignment changes remain
blocked.

Post-apply convergence uses bounded retry so Azure Policy read-after-write
propagation does not create a false-negative deployment result. A non-retryable
drift shape still fails immediately.

## Commit 16 — Scope-aware Audit-First Wave 2

The active cumulative profile is:

    foundation/policy/profiles/enterprise/audit-first-wave2.json

Wave 2 keeps the four Wave 1 assignment payloads unchanged and adds four more
built-in, identity-free controls:

    Audit-ResourceRGLocation -> root
    Audit-AppGW-WAF           -> landing_zones
    Deny-Priv-Esc-AKS         -> landing_zones
    Deny-Privileged-AKS       -> landing_zones

`Audit-AppGW-WAF` was duplicated in the legacy Landing Zones and Online
archetypes. APF assigns it once at Landing Zones because Online is a child and
inherits the assignment. The migration rationale is recorded in the profile.

Desired state remains:

    desiredState.strategy = ownedOnly

The protected apply boundary remains additive Policy Assignments only. DINE,
Modify, assignment identities, role reconciliation, custom definitions/sets,
sovereignty controls and REVIEW-classified migration assets remain deferred.
## Commit 17 — Policy Version Governance

APF treats Azure Policy definition versions as part of policy intent. The machine-readable contract is `foundation/policy/version-governance.json`. The default strategy is `pinned_major`: built-in assignments use `#.*.*`, auto-ingesting minor/patch changes inside a major while requiring explicit review for a new major. Commit 17 records the first review for the AKS privilege-escalation policy and keeps `7.*.*`; it performs no customer or Azure mutation.

