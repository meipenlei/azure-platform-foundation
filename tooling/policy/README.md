# APF Policy Tooling

This directory contains Governance-as-Code tooling for the APF policy layer.

## Commit 9 foundation

Commit 9 introduced:

- legacy policy-library inventory;
- APF policy-foundation validation;
- pinned EPAC installation verification;
- thin EPAC plan/apply wrappers for later customer lifecycle integration.

## Commit 10 migration analysis

Commit 10 adds a reproducible, read-only migration comparison between the
legacy HCI policy library and the pinned current ALZ/SLZ releases.

The comparison classifies assets as:

- `UPSTREAM` — current ALZ/SLZ asset exists and should be consumed upstream;
- `APF_CUSTOM` — APF-specific behavior should remain an APF overlay;
- `REVIEW` — a semantic/current-service review is required;
- `OBSOLETE` — deliberately retired after review.

`OBSOLETE` is never inferred merely because an upstream name is missing.

### 1. Prepare pinned upstream libraries

    python tooling/policy/prepare_upstream.py \
      --output-dir /tmp/apf-policy-upstream

The command reads the pinned tags from:

    foundation/policy/versions.json

and creates sparse checkouts for exactly those ALZ and SLZ releases.

### 2. Run the legacy comparison

Assuming `hci-foundation01` is checked out beside the APF repository at the
`feature_mj` content used for the migration baseline:

    python tooling/policy/migrate_legacy.py \
      --legacy-library-dir ../hci-foundation01/configuration/level1/alz/es/lib \
      --alz-library-dir /tmp/apf-policy-upstream/alz/platform/alz \
      --slz-library-dir /tmp/apf-policy-upstream/slz/platform/slz \
      --mapping foundation/policy/migration/hci-foundation01-map.json \
      --output-json /tmp/apf-hci-policy-migration.json \
      --output-markdown /tmp/apf-hci-policy-migration.md \
      --strict-counts

This command does not authenticate to Azure and does not deploy resources.

For upstream assignment matches it compares:

- policy/initiative target;
- `enforcementMode`;
- assignment identity type;
- parameters;
- definition version metadata.

The report therefore retains legacy audit-first and Brownfield behavior even
when the underlying policy asset is now provided by Microsoft.

## EPAC version

The version is pinned in:

    foundation/policy/versions.json

Do not install an unpinned EPAC version in APF CI/CD.

## Plan wrapper

`Invoke-PolicyPlan.ps1` calls EPAC `Build-DeploymentPlans`.

It requires an already rendered customer `Definitions/global-settings.jsonc`.

## Apply wrapper

`Invoke-PolicyApply.ps1` calls:

    Deploy-PolicyPlan
    Deploy-RolesPlan

It requires `-ConfirmApply`.

This guard is intentional. A future generated customer workflow will provide
the policy deployment approval boundary.

## Legacy inventory

The simple inventory remains available:

    python tooling/policy/inventory.py \
      --library-dir ../hci-foundation01/configuration/level1/alz/es/lib \
      --output-json /tmp/hci-policy-inventory.json

All migration and inventory commands are read-only.
