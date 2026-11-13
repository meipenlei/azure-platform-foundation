resource "azurerm_role_assignment" "plan_reader" {
  scope                = azurerm_management_group.root.id
  role_definition_name = "Reader"
  principal_id         = var.plan_principal_id

  skip_service_principal_aad_check = true

  lifecycle {
    ignore_changes = [skip_service_principal_aad_check]
  }
}

resource "azurerm_role_assignment" "governance_management_group_contributor" {
  scope                = azurerm_management_group.root.id
  role_definition_name = "Management Group Contributor"
  principal_id         = var.governance_principal_id

  skip_service_principal_aad_check = true

  lifecycle {
    ignore_changes = [skip_service_principal_aad_check]
  }
}

resource "azurerm_role_assignment" "governance_policy_contributor" {
  scope                = azurerm_management_group.root.id
  role_definition_name = "Resource Policy Contributor"
  principal_id         = var.governance_principal_id

  skip_service_principal_aad_check = true

  lifecycle {
    ignore_changes = [skip_service_principal_aad_check]
  }
}

resource "azurerm_role_assignment" "governance_rbac_admin" {
  scope                = azurerm_management_group.root.id
  role_definition_name = "Role Based Access Control Administrator"
  principal_id         = var.governance_principal_id

  skip_service_principal_aad_check = true

  lifecycle {
    ignore_changes = [skip_service_principal_aad_check]
  }
}

resource "azurerm_role_assignment" "governance_management_resources_contributor" {
  scope                = azurerm_management_group.management.id
  role_definition_name = "Contributor"
  principal_id         = var.governance_principal_id

  skip_service_principal_aad_check = true

  lifecycle {
    ignore_changes = [skip_service_principal_aad_check]
  }
}
