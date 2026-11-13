resource "azurerm_management_group_subscription_association" "bootstrap" {
  management_group_id = azurerm_management_group.management.id
  subscription_id     = "/subscriptions/${var.bootstrap_subscription_id}"

  depends_on = [
    azurerm_role_assignment.governance_management_group_contributor,
    azurerm_role_assignment.governance_rbac_admin,
  ]
}

resource "azurerm_management_group_subscription_association" "management" {
  count = (
    var.management_subscription_id != null
    && var.management_subscription_id != var.bootstrap_subscription_id
  ) ? 1 : 0

  management_group_id = azurerm_management_group.management.id
  subscription_id     = "/subscriptions/${var.management_subscription_id}"

  depends_on = [
    azurerm_role_assignment.governance_management_group_contributor,
    azurerm_role_assignment.governance_rbac_admin,
  ]
}
