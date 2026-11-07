# Governance as Code

**Version:** 0.1  
**Status:** Draft  
**Project:** Azure Platform Foundation

## Purpose

Azure Platform Foundation treats governance as desired state.

The repository is the durable source of truth. Manual portal changes are
considered drift unless the corresponding source configuration is changed.

## Core principle

> Portal changes are not configuration changes.

A durable governance change follows this lifecycle:

    intent
      -> source change
      -> pull request
      -> desired-state plan
      -> approval
      -> deployment
      -> continuous drift detection

Emergency changes made directly in Azure must be back-ported to source or they
remain drift.

## Technology boundary

APF does not use one tool for every governance concern.

    Terraform / APF
        -> management groups
        -> platform identities
        -> platform RBAC
        -> governance execution foundation

    EPAC
        -> policy definitions
        -> policy set definitions
        -> policy assignments
        -> policy exemptions
        -> policy assignment role requirements
        -> desired-state reconciliation

This prevents two declarative engines from owning the same Azure resource.

## EPAC

Enterprise Policy as Code (EPAC) is the APF desired-state engine for Azure
Policy.

The EPAC PowerShell module is pinned in
`foundation/policy/versions.json`.

Commit 9 pins:

    EnterprisePolicyAsCode 11.5.11

The Azure Landing Zones Library is also pinned rather than consumed from an
unversioned branch.

Commit 9 pins:

    platform/alz/2026.11.0
    platform/slz/2026.11.0

Upstream upgrades are explicit product changes and require a reviewed diff.

## Desired-state modes

### Brownfield

Brownfield starts with:

    desiredState.strategy = ownedOnly

APF therefore manages only policy resources that it owns while existing
customer policy resources remain untouched during discovery and adoption.

The intended lifecycle is:

    discover
      -> classify
      -> import/adopt
      -> validate
      -> remediate
      -> optionally transition to full ownership

### Greenfield

Greenfield targets:

    desiredState.strategy = full

This is enabled only after the APF policy baseline has been populated and the
deployment plan has been reviewed.

In full mode, policy resources in the managed scope that do not belong to the
desired state may be removed. APF must therefore never enable full ownership
implicitly.

## Drift detection

Governance drift is evaluated independently from normal infrastructure drift.

The intended operating model is:

    pull request
      -> EPAC plan

    merge
      -> EPAC apply

    scheduled reconciliation
      -> EPAC plan
      -> drift report

Initial APF autonomy reports drift and requires an explicit apply.

Future autonomy levels may automatically reconcile approved low-risk drift.

## Policy source model

APF does not copy the complete Microsoft ALZ library into the product.

Instead:

    Microsoft ALZ Library (pinned)
                |
                v
        APF policy overlay
                |
                v
      Customer policy extensions
                |
                v
              EPAC

This keeps Microsoft-maintained policy assets upstream while preserving APF
parameterization, enforcement decisions, custom definitions and customer
extensions.

## Legacy HCI framework

The previous `hci-foundation01` policy library is a migration source, not a new
runtime dependency.

Its assets are classified into:

- `UPSTREAM`: equivalent or successor exists in the current ALZ/SLZ library;
- `APF_CUSTOM`: APF-specific asset that should be migrated;
- `REVIEW`: asset requiring semantic/version review;
- `OBSOLETE`: asset that should not be migrated.

The audit-first and `DoNotEnforce` decisions in the legacy assignments are
treated as governance design knowledge and must be preserved during
classification even when the underlying policy definition is replaced by a
newer upstream version.
