output "resource_group_id" {
  value = azurerm_resource_group.management.id
}

output "resource_group_name" {
  value = azurerm_resource_group.management.name
}

output "log_analytics_workspace_id" {
  value = azurerm_log_analytics_workspace.platform.id
}

output "log_analytics_workspace_name" {
  value = azurerm_log_analytics_workspace.platform.name
}

output "log_analytics_workspace_customer_id" {
  value = azurerm_log_analytics_workspace.platform.workspace_id
}

output "monitoring_identity_id" {
  value = azurerm_user_assigned_identity.monitoring.id
}

output "monitoring_identity_client_id" {
  value = azurerm_user_assigned_identity.monitoring.client_id
}

output "monitoring_identity_principal_id" {
  value = azurerm_user_assigned_identity.monitoring.principal_id
}
