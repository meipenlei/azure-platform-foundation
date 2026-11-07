# HCI Foundation Policy Library — Initial Inventory

**Source repository:** `meipenlei/hci-foundation01`  
**Branch:** `feature_mj`  
**Source path:** `configuration/level1/alz/es/lib`  
**Status:** inventory only; no policy asset has been migrated by Commit 9.

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

These assets must be resolved against the pinned current ALZ/SLZ releases
before migration.

## Valuable design knowledge

The most important reusable information is not only the JSON definitions.

The library contains deliberate governance decisions such as:

- `Audit` instead of `Deny`;
- `DoNotEnforce` for Brownfield adoption;
- selected `DeployIfNotExists` controls;
- service-specific guardrail parameterization;
- custom `security`, `public`, `confidential-corp` and
  `confidential-online` archetypes.

These decisions will be preserved even when the underlying Microsoft policy
asset is replaced by a newer upstream version.

## Migration classes

Every legacy asset will eventually receive one of these classifications:

    UPSTREAM
    APF_CUSTOM
    REVIEW
    OBSOLETE

Commit 9 intentionally does not bulk-copy the legacy library.
