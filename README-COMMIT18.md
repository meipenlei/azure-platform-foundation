# Commit 18 — Level 1 Management & Security Substrate

Overlay this package on the public `azure-platform-foundation` repository.

## Scope

Commit 18 adds Terraform-owned Level 1 management anchors:

- optional dedicated Management subscription support;
- central management resource group;
- central Log Analytics workspace;
- monitoring UAMI;
- scoped Governance-UAMI Contributor delegation at the Management MG;
- separate customer Terraform state and workflows.

It does **not** add DINE/Modify policies yet.

## Public APF validation

After copying this package over the repository:

    python -m pip install       -r tooling/customer-level1/requirements.txt       -r tooling/customer-level1-management/requirements.txt       -r tooling/validate-config/requirements.txt

    python -m py_compile       tooling/customer-level1/configure.py       tooling/customer-level1/test_configure.py       tooling/customer-level1-management/configure.py       tooling/customer-level1-management/test_configure.py

    python -m unittest discover       -s tooling/customer-level1       -p "test_*.py"

    python -m unittest discover       -s tooling/customer-level1-management       -p "test_*.py"

    python tooling/validate-config/validate.py       --config-dir config/examples/greenfield-minimal       --schema-dir config/schema

Then inspect:

    git status
    git diff

Commit:

    git add       config       foundation/modules/level1-management-groups       foundation/modules/level1-management-platform       tooling/customer-level1       tooling/customer-level1-management       docs/architecture/level1-management-platform.md       .github/workflows/level1-foundation-smoke.yml

    git commit -m "feat: add level1 management platform"
    git push origin main

## lab04 — generate Commit 18

Create one customer branch:

    cd ~/GIT/Repos/lab04-apf-azure-platform
    git switch main
    git pull
    git switch -c apf/commit18-level1-management-platform

Regenerate the existing Management Groups root:

    cd ~/GIT/Repos/azure-platform-foundation

    python tooling/customer-level1/configure.py       --project-dir ../lab04-apf-azure-platform       --apply

    python tooling/customer-level1/configure.py       --project-dir ../lab04-apf-azure-platform

Expected second result:

    [PASS] Level 1 management-group project is already generated.

Generate the Management platform root:

    python tooling/customer-level1-management/configure.py       --project-dir ../lab04-apf-azure-platform

Review the dry-run, then:

    python tooling/customer-level1-management/configure.py       --project-dir ../lab04-apf-azure-platform       --apply

    python tooling/customer-level1-management/configure.py       --project-dir ../lab04-apf-azure-platform

Expected second result:

    [PASS] Level 1 Management platform is already generated.

## Expected customer changes

Existing Level 1 root changes should be limited to generated inputs/module
contract needed for `management_subscription_id`.

New files include:

    levels/level1/management-platform/
    .foundation/level1-management-platform.yaml
    .github/workflows/terraform-level1-management-platform-plan.yml
    .github/workflows/terraform-level1-management-platform-apply.yml

## Customer PR

    cd ~/GIT/Repos/lab04-apf-azure-platform

    git status
    git diff

    git add       levels/level1/management-groups       levels/level1/management-platform       .foundation/level1-management-platform.yaml       .github/workflows/terraform-level1-management-groups-plan.yml       .github/workflows/terraform-level1-management-groups-apply.yml       .github/workflows/terraform-level1-management-platform-plan.yml       .github/workflows/terraform-level1-management-platform-apply.yml

    git commit -m "feat: add level1 management platform"
    git push -u origin apf/commit18-level1-management-platform

    gh pr create       --base main       --head apf/commit18-level1-management-platform       --title "feat: add level1 management platform"       --body "Add the Terraform-owned Level 1 management substrate: central Log Analytics and monitoring identity, with Management-scope governance delegation."

## Expected PR plans for lab04

Because lab04 has no dedicated `management_subscription_id`, it falls back to
the existing bootstrap subscription.

Management Groups plan:

    1 to add
    0 to change
    0 to destroy

The add is the scoped Governance-UAMI `Contributor` role at the Management
management group.

Management Platform plan:

    3 to add
    0 to change
    0 to destroy

The three resources are:

- Resource Group;
- Log Analytics Workspace;
- Monitoring UAMI.

Do not merge if either plan contains a destroy.

## After merge

Apply Management Groups **first**:

    gh workflow run terraform-level1-management-groups-apply.yml --ref main

Only after that succeeds, run:

    gh workflow run terraform-level1-management-platform-apply.yml       --ref main       -f confirm_apply=true

This ordering ensures the Governance UAMI has Management-scope Contributor
before it creates the Management platform resources.
