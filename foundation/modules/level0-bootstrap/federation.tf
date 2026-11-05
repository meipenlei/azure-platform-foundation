resource "azurerm_federated_identity_credential" "github_plan" {
  name = "github-plan"

  user_assigned_identity_id = azurerm_user_assigned_identity.plan.id

  issuer = "https://token.actions.githubusercontent.com"

  audience = [
    "api://AzureADTokenExchange"
  ]

  subject = local.github_plan_subject
}

resource "azurerm_federated_identity_credential" "github_apply" {
  name = "github-apply"

  user_assigned_identity_id = azurerm_user_assigned_identity.apply.id

  issuer = "https://token.actions.githubusercontent.com"

  audience = [
    "api://AzureADTokenExchange"
  ]

  subject = local.github_apply_subject
}

resource "azurerm_federated_identity_credential" "github_governance" {
  name = "github-governance"

  user_assigned_identity_id = azurerm_user_assigned_identity.governance.id

  issuer   = "https://token.actions.githubusercontent.com"
  audience = ["api://AzureADTokenExchange"]

  subject = "${local.github_subject_prefix}:environment:${var.github_governance_environment}"
}