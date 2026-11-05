output "resource_group_name" {
  value = azurerm_resource_group.bootstrap.name
}

output "storage_account_name" {
  value = azurerm_storage_account.state.name
}

output "state_container_name" {
  value = azurerm_storage_container.tfstate.name
}

output "plan_identity_name" {
  value = azurerm_user_assigned_identity.plan.name
}

output "plan_identity_client_id" {
  value = azurerm_user_assigned_identity.plan.client_id
}

output "apply_identity_name" {
  value = azurerm_user_assigned_identity.apply.name
}

output "apply_identity_client_id" {
  value = azurerm_user_assigned_identity.apply.client_id
}

output "github_plan_subject" {
  value = local.github_plan_subject
}

output "github_apply_subject" {
  value = local.github_apply_subject
}

output "backend_configuration" {
  value = {
    resource_group_name  = azurerm_resource_group.bootstrap.name
    storage_account_name = azurerm_storage_account.state.name
    container_name       = azurerm_storage_container.tfstate.name
    key                  = "level0.bootstrap.tfstate"
    use_azuread_auth     = true
  }
}

output "governance_identity_client_id" {
  value = azurerm_user_assigned_identity.governance.client_id
}