# HCI Foundation Policy Library — Initial Inventory

**Source repository:** `meipenlei/hci-foundation01`  
**Branch:** `feature_mj`  
**Source path:** `configuration/level1/alz/es/lib`  
**Status:** migration source; no legacy policy asset is deployed by Commit 10.

## Inventory

The legacy library contains, excluding README files:

| Asset type | Count |
| --- | ---: |
| Archetype definitions | 14 |
| Policy assignments | 91 |
| Custom policy definitions | 3 |
| Custom policy set definitions | 2 |
| Custom role definitions | 1 |

The root archetype references:

- 27 policy assignments;
- 163 policy definitions;
- 49 policy set definitions.

The landing-zones archetype contains 49 assignments and the platform archetype
contains 41 assignments.

## Important finding

The legacy library is an overlay on the Azure Landing Zones policy library,
not a self-contained policy catalog.

Many assignments reference:

- Microsoft built-in policies and initiatives; or
- ALZ custom definitions / initiatives that are not stored in the local
  `policy_definitions` and `policy_set_definitions` folders.

Examples include:

- `Enforce-Guardrails-OpenAI`
- `Enforce-Guardrails-Storage`
- `Enforce-Guardrails-Kubernetes`
- `Audit-ResourceRGLocation`
- `Deny-Subnet-Without-Nsg`

Commit 10 resolves those assets against the pinned current ALZ/SLZ releases.

## Valuable design knowledge

The most important reusable information is not only the JSON definitions.

The library contains deliberate governance decisions such as:

- `Audit` instead of `Deny`;
- `DoNotEnforce` for Brownfield adoption;
- selected `DeployIfNotExists` controls;
- service-specific guardrail parameterization;
- custom `security`, `public`, `confidential-corp` and
  `confidential-online` archetypes.

The Commit 10 migration tool compares assignment semantics so these decisions
remain visible even when Microsoft now supplies the underlying policy asset.

## Migration classes

Every legacy asset is classified into:

    UPSTREAM
    APF_CUSTOM
    REVIEW
    OBSOLETE

The curated migration map lives at:

    foundation/policy/migration/hci-foundation01-map.json

No legacy asset is bulk-copied into the APF library.
