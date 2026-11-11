# Commit 12 — Level 1 Management Group Foundation

Suggested public commit:

    feat: establish level1 management group foundation

## Public repository validation

    pip install -r tooling/customer-level1/requirements.txt

    python -m py_compile \
      tooling/customer-level1/configure.py \
      tooling/customer-level1/bootstrap.py \
      tooling/customer-level1/test_configure.py

    python -m unittest discover \
      -s tooling/customer-level1 \
      -p "test_*.py"

    terraform fmt \
      -check \
      -recursive \
      foundation/modules/level1-management-groups

    terraform -chdir=foundation/modules/level1-management-groups init -backend=false
    terraform -chdir=foundation/modules/level1-management-groups validate

## Commit

    git add \
      foundation/modules/level1-management-groups \
      tooling/customer-level1 \
      docs/architecture/level1-management-groups.md \
      .github/workflows/level1-foundation-smoke.yml

    git commit -m "feat: establish level1 management group foundation"

    git push origin main

## lab04 generation

From the public APF repository:

    python tooling/customer-level1/configure.py \
      --project-dir ../lab04-apf-azure-platform

Then:

    python tooling/customer-level1/configure.py \
      --project-dir ../lab04-apf-azure-platform \
      --apply

Re-run dry-run and expect:

    [PASS] Level 1 management-group project is already generated.

## lab04 first plan

    python tooling/customer-level1/bootstrap.py \
      --project-dir ../lab04-apf-azure-platform

Expected Terraform changes on a fresh hierarchy:

- 10 management groups;
- 4 APF Root role assignments;
- 1 subscription association.

There must be no deletes.

## First apply

After reviewing the plan:

    python tooling/customer-level1/bootstrap.py \
      --project-dir ../lab04-apf-azure-platform \
      --apply

Expected durable hierarchy:

    Tenant Root
      └── lab04
          ├── lab04-platform
          │   ├── lab04-management
          │   ├── lab04-connectivity
          │   └── lab04-identity
          ├── lab04-landing-zones
          │   ├── lab04-corp
          │   └── lab04-online
          ├── lab04-sandboxes
          └── lab04-decommissioned

The bootstrap subscription is moved under:

    lab04-management

The generated snapshot is:

    .foundation/level1-management-groups.yaml

## lab04 commit after successful bootstrap

Commit the generated Level 1 root, workflows and snapshot in lab04.

Do not run EPAC apply in Commit 12.

Commit 11 policy desired state remains at subscription scope until the next
policy slice.
