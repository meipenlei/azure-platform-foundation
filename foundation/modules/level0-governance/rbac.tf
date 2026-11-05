resource "azurerm_role_assignment" "governance_subscription_rbac_admin" {
  scope                = local.subscription_scope
  role_definition_name = "Role Based Access Control Administrator"
  principal_id         = var.governance_principal_id

  skip_service_principal_aad_check = true

  lifecycle {
    ignore_changes = [
      skip_service_principal_aad_check
    ]
  }
}

resource "azurerm_role_assignment" "governance_state" {
  scope                = var.state_container_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.governance_principal_id

  skip_service_principal_aad_check = true

  lifecycle {
    ignore_changes = [
      skip_service_principal_aad_check
    ]
  }
}