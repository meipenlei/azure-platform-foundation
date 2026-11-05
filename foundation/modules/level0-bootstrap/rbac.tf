resource "azurerm_role_assignment" "plan_state" {
  scope = azurerm_storage_container.tfstate.id

  role_definition_name = "Storage Blob Data Contributor"

  principal_id = azurerm_user_assigned_identity.plan.principal_id
}

resource "azurerm_role_assignment" "apply_state" {
  scope = azurerm_storage_container.tfstate.id

  role_definition_name = "Storage Blob Data Contributor"

  principal_id = azurerm_user_assigned_identity.apply.principal_id
}

resource "azurerm_role_assignment" "plan_subscription_reader" {
  scope = data.azurerm_subscription.current.id

  role_definition_name = "Reader"

  principal_id = azurerm_user_assigned_identity.plan.principal_id
}

resource "azurerm_role_assignment" "apply_subscription_contributor" {
  scope = data.azurerm_subscription.current.id

  role_definition_name = "Contributor"

  principal_id = azurerm_user_assigned_identity.apply.principal_id
}

