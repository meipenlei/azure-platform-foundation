# Commit 13 — Move EPAC Planning to the APF Root Management Group

Suggested public commit:

    feat: move policy planning to level1 management group root

## Validate public repository

    pip install -r tooling/customer-policy/requirements.txt

    python -m py_compile \
      tooling/customer-policy/configure.py \
      tooling/customer-policy/test_configure.py \
      tooling/policy/validate.py

    python -m unittest discover \
      -s tooling/customer-policy \
      -p "test_*.py"

    python tooling/policy/validate.py

## Commit

    git add \
      foundation/policy \
      tooling/customer-policy \
      tooling/policy/validate.py \
      docs/architecture/policy-plan-pilot.md

    git commit -m "feat: move policy planning to level1 management group root"

    git push origin main

## Generate lab04

The Level 1 bootstrap must already have generated:

    .foundation/level1-management-groups.yaml

Dry-run:

    python tooling/customer-policy/configure.py \
      --project-dir ../lab04-apf-azure-platform

Generate:

    python tooling/customer-policy/configure.py \
      --project-dir ../lab04-apf-azure-platform \
      --apply

Run dry-run again and expect:

    [PASS] Customer policy desired state is already generated.

## Inspect lab04

`governance/policy/Definitions/global-settings.jsonc` must contain:

    "deploymentRootScope": "/providers/Microsoft.Management/managementGroups/lab04"

The assignment file must use the same scope and contain:

    "definitionVersion": "2.*.*"
    "effect": "Audit"
    "enforcementMode": "Default"

`.foundation/policy.yaml` must identify:

    deployment_root_source: .foundation/level1-management-groups.yaml

## Validate via PR

Create a new branch in lab04, commit the regenerated policy files and open a PR.

Expected EPAC result:

- deployment root is the APF root management group;
- EPAC discovers the child management-group hierarchy;
- exactly one APF audit assignment is proposed;
- no deletes are proposed;
- no role changes are required for this assignment;
- no Policy Apply step exists.
