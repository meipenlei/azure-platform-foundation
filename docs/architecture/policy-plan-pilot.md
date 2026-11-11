# Policy Desired-State Plan Pilot

**Version:** 0.2  
**Status:** Commit 13  
**Azure mutation:** None

Commit 11 proved EPAC planning at subscription scope. Commit 12 established the Level 1 management-group hierarchy. Commit 13 moves the EPAC deployment root and pilot assignment scope to the APF root management group.

The deployment root comes from `.foundation/level1-management-groups.yaml`. The generator requires `management_groups.policy_deployment_root_scope` to equal `management_groups.management_group_ids.root` and to be a Management Group resource ID. There is no subscription fallback.

The PR workflow still uses the Plan UAMI and `Build-DeploymentPlans` only. The `pacOwnerId` remains unchanged.

The pilot keeps:

    desiredState.strategy = ownedOnly
    definitionVersion = 2.*.*
    effect = Audit
    enforcementMode = Default

After this management-group plan is proven, APF can begin expanding desired state from the migration baseline with selected ALZ/SLZ assignments and APF overlays.
