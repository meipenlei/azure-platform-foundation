# APF Level 1 Management Platform

Terraform-owned anchor resources for the APF management and observability layer.

Commit 18 creates only stable shared resources:

- management resource group;
- central Log Analytics workspace;
- monitoring user-assigned managed identity.

Azure Policy assignments, DCRs, Defender plans, diagnostic settings,
remediation tasks, and alert rules are intentionally not owned by this module.

The Log Analytics workspace disables local authentication. Public ingestion
and query endpoints remain enabled at this stage because Level 2 connectivity
and private-link architecture do not exist yet.
