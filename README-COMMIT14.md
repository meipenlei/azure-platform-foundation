# Commit 14 — Scope-aware Audit-First Wave 1

Suggested public commit:

    feat: add scope-aware policy audit-first wave1

## Public repository validation

    pip install -r tooling/customer-policy/requirements.txt

    python -m py_compile \
      tooling/customer-policy/configure.py \
      tooling/customer-policy/test_configure.py \
      tooling/policy/validate.py

    python -m unittest discover \
      -s tooling/customer-policy \
      -p "test_*.py"

    python tooling/policy/validate.py

## Public commit

    git add \
      foundation/policy \
      tooling/customer-policy \
      tooling/policy/validate.py \
      docs/architecture/policy-audit-first-wave1.md

    git commit -m "feat: add scope-aware policy audit-first wave1"

    git push origin main

## Generate lab04

Create a fresh lab04 branch from updated main first.

From the APF repository:

    python tooling/customer-policy/configure.py \
      --project-dir ../lab04-apf-azure-platform

Expected new/changed generated files include:

    .foundation/policy.yaml
    governance/policy/README.md
    governance/policy/Definitions/policyAssignments/apf-audit-public-ip.assignment.jsonc
    governance/policy/Definitions/policyAssignments/apf-deny-classic-resources.assignment.jsonc
    governance/policy/Definitions/policyAssignments/apf-deny-storage-http.assignment.jsonc
    governance/policy/Definitions/policyAssignments/apf-deny-hybrid-networking.assignment.jsonc

Then generate:

    python tooling/customer-policy/configure.py \
      --project-dir ../lab04-apf-azure-platform \
      --apply

Re-run dry-run and expect idempotency.

## Inspect assignment scopes

    grep -R -n 'managementGroups/lab04' \
      ../lab04-apf-azure-platform/governance/policy/Definitions/policyAssignments

Expected scope mapping:

    apf-audit-public-ip          -> lab04-identity
    apf-deny-classic-resources   -> lab04
    apf-deny-storage-http        -> lab04-landing-zones
    apf-deny-hybrid-networking   -> lab04-corp

## Validate through PR

Open a new lab04 PR. The Policy Desired State Plan should remain plan-only.

Expected EPAC plan on a clean environment:

    Policy Assignments Summary
      4 total changes
      4 new

    Role Assignments Summary
      No changes required

No deletes are expected.
