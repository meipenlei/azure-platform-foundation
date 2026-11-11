# APF Customer Level 1

This tooling creates and bootstraps the first APF Level 1 resource hierarchy.

Commit 12 scope is limited to Azure Management Groups, subscription placement
and the identity delegation required for future OIDC management.

## Generated hierarchy

    Tenant Root
      └── <prefix>                         APF Root
          ├── Platform
          │   ├── Management
          │   ├── Connectivity
          │   └── Identity
          ├── Landing Zones
          │   ├── Corp
          │   └── Online
          ├── Sandboxes
          └── Decommissioned

The existing APF bootstrap subscription is initially placed under `Management`.

## Identity delegation

At the APF Root scope:

- Plan UAMI -> `Reader`
- Governance UAMI -> `Management Group Contributor`
- Governance UAMI -> `Resource Policy Contributor`
- Governance UAMI -> `Role Based Access Control Administrator`

No APF identity receives a permanent role on the Tenant Root management group.

## Generate customer files

Dry-run:

    python tooling/customer-level1/configure.py \
      --project-dir ../lab04-apf-azure-platform

Write:

    python tooling/customer-level1/configure.py \
      --project-dir ../lab04-apf-azure-platform \
      --apply

## Bootstrap

The first plan/apply is executed with the locally signed-in Azure operator:

    python tooling/customer-level1/bootstrap.py \
      --project-dir ../lab04-apf-azure-platform

Then, after reviewing the plan:

    python tooling/customer-level1/bootstrap.py \
      --project-dir ../lab04-apf-azure-platform \
      --apply

The bootstrap tool temporarily grants the signed-in user
`Storage Blob Data Contributor` on the APF state container if required and
removes that temporary assignment before exiting. Cleanup failure fails the
operation.

## Required operator capability

The bootstrap operator must be able to create the APF root management group,
assign roles on it and move the bootstrap subscription.

APF does not create a permanent Tenant Root role assignment.

After the first successful apply, normal CI/CD uses:

- PR plan -> Plan UAMI
- protected apply -> Governance UAMI (`apf-governance` environment)

## Policy

Commit 12 does not rescope or apply the Commit 11 EPAC pilot.

The Level 1 output `policy_deployment_root_scope` is the input for the next
policy slice.
