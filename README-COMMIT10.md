# Commit 10 — Legacy Policy Migration Analysis

Suggested commit message:

    feat: classify legacy governance policy assets

## Scope

Commit 10 is read-only with respect to Azure.

It adds:

- pinned ALZ/SLZ sparse-checkout preparation;
- reproducible legacy-vs-current policy comparison;
- curated migration aliases and decisions;
- semantic assignment delta detection;
- machine-readable JSON and human-readable Markdown reports;
- migration unit tests;
- a documented initial classification baseline.

## Initial baseline

Across 111 legacy assets:

    UPSTREAM    88
    APF_CUSTOM   6
    REVIEW      17
    OBSOLETE     0

For the 91 policy assignments:

    exact upstream names       63
    curated upstream aliases   11
    upstream total             74
    APF_CUSTOM                  4
    REVIEW                     13

## Local validation

From the APF repository root:

    python -m py_compile \
      tooling/policy/inventory.py \
      tooling/policy/migrate_legacy.py \
      tooling/policy/prepare_upstream.py \
      tooling/policy/validate.py \
      tooling/policy/test_inventory.py \
      tooling/policy/test_migrate_legacy.py

    python -m unittest discover \
      -s tooling/policy \
      -p "test_*.py"

    python tooling/policy/validate.py

## Real migration comparison

Prepare the pinned Microsoft libraries:

    python tooling/policy/prepare_upstream.py \
      --output-dir /tmp/apf-policy-upstream

Then compare the old HCI library:

    python tooling/policy/migrate_legacy.py \
      --legacy-library-dir ../hci-foundation01/configuration/level1/alz/es/lib \
      --alz-library-dir /tmp/apf-policy-upstream/alz/platform/alz \
      --slz-library-dir /tmp/apf-policy-upstream/slz/platform/slz \
      --mapping foundation/policy/migration/hci-foundation01-map.json \
      --output-json /tmp/apf-hci-policy-migration.json \
      --output-markdown /tmp/apf-hci-policy-migration.md \
      --strict-counts

Expected source counts:

    archetype_definitions       14
    policy_assignments          91
    policy_definitions           3
    policy_set_definitions       2
    role_definitions             1

The command does not log into Azure and does not invoke EPAC apply.

## Git

    git add \
      foundation/policy/migration \
      tooling/policy \
      docs/migration \
      .github/workflows/policy-foundation-smoke.yml

    git commit -m "feat: classify legacy governance policy assets"

    git push origin main
