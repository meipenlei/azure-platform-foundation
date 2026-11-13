resource "azurerm_resource_group" "management" {
  name     = local.resource_names.resource_group
  location = var.location
  tags     = local.tags
}

resource "azurerm_log_analytics_workspace" "platform" {
  name                = local.resource_names.log_analytics
  location            = azurerm_resource_group.management.location
  resource_group_name = azurerm_resource_group.management.name

  sku               = "PerGB2018"
  retention_in_days = var.log_analytics_retention_days

  allow_resource_only_permissions = true
  local_authentication_enabled     = false
  internet_ingestion_enabled       = true
  internet_query_enabled           = true

  tags = local.tags
}

resource "azurerm_user_assigned_identity" "monitoring" {
  name                = local.resource_names.monitoring_identity
  location            = azurerm_resource_group.management.location
  resource_group_name = azurerm_resource_group.management.name
  tags                = local.tags
}
