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

The pinned versions for EPAC and the upstream libraries are stored in:

    foundation/policy/versions.json

## Desired-state strategy

APF uses two explicit desired-state modes:

- Brownfield adoption starts with `ownedOnly`.
- Greenfield targets `full` after the intended policy baseline has been
  populated and reviewed.

A portal change is not a durable configuration change. A change that must
remain has to be represented in source control.

## Commit 9 boundary

Commit 9 establishes the Governance-as-Code foundation. It does not deploy
Azure Policy resources yet.

The first policy deployment will be introduced only after:

1. the legacy HCI policy library has been classified;
2. the APF policy baseline is populated;
3. customer-specific EPAC configuration generation exists;
4. the first EPAC deployment plan has been reviewed.
