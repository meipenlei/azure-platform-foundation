output "governance_subscription_rbac_assignment_id" {
  value = azurerm_role_assignment.governance_subscription_rbac_admin.id
}

output "governance_state_assignment_id" {
  value = azurerm_role_assignment.governance_state.id
}