# APF Customer Policy Configurator

Commit 13 moves the plan-only EPAC pilot from the bootstrap subscription to the Level 1 APF root management group.

The configurator now requires `.foundation/level1-management-groups.yaml` and refuses to fall back to subscription scope. The generated workflow remains PR-only, uses `AZURE_PLAN_CLIENT_ID`, calls `Build-DeploymentPlans`, and never calls `Deploy-PolicyPlan` or `Deploy-RolesPlan`.

The pilot keeps `ownedOnly`, `effect=Audit`, `enforcementMode=Default`, and pins the built-in policy to `definitionVersion=2.*.*`.
