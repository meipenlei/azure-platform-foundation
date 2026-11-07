# APF Policy Tooling

This directory contains Governance-as-Code tooling for the APF policy layer.

Commit 9 provides:

- legacy policy-library inventory;
- APF policy-foundation validation;
- pinned EPAC installation verification;
- thin EPAC plan/apply wrappers for later customer lifecycle integration.

Commit 9 does **not** wire the apply wrapper into a customer GitHub workflow.

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

Example:

    python tooling/policy/inventory.py       --library-dir ../hci-foundation01/configuration/level1/alz/es/lib       --output-json /tmp/hci-policy-inventory.json

The inventory command is read-only.
