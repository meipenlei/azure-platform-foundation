resource "azurerm_management_group" "root" {
  name                       = local.management_group_names.root
  display_name               = var.root_display_name
  parent_management_group_id = local.tenant_root_management_group_id
}

resource "azurerm_management_group" "platform" {
  name                       = local.management_group_names.platform
  display_name               = "Platform"
  parent_management_group_id = azurerm_management_group.root.id
}

resource "azurerm_management_group" "landing_zones" {
  name                       = local.management_group_names.landing_zones
  display_name               = "Landing Zones"
  parent_management_group_id = azurerm_management_group.root.id
}

resource "azurerm_management_group" "sandboxes" {
  name                       = local.management_group_names.sandboxes
  display_name               = "Sandboxes"
  parent_management_group_id = azurerm_management_group.root.id
}

resource "azurerm_management_group" "decommissioned" {
  name                       = local.management_group_names.decommissioned
  display_name               = "Decommissioned"
  parent_management_group_id = azurerm_management_group.root.id
}

resource "azurerm_management_group" "management" {
  name                       = local.management_group_names.management
  display_name               = "Management"
  parent_management_group_id = azurerm_management_group.platform.id
}

resource "azurerm_management_group" "connectivity" {
  name                       = local.management_group_names.connectivity
  display_name               = "Connectivity"
  parent_management_group_id = azurerm_management_group.platform.id
}

resource "azurerm_management_group" "identity" {
  name                       = local.management_group_names.identity
  display_name               = "Identity"
  parent_management_group_id = azurerm_management_group.platform.id
}

resource "azurerm_management_group" "corp" {
  name                       = local.management_group_names.corp
  display_name               = "Corp"
  parent_management_group_id = azurerm_management_group.landing_zones.id
}

resource "azurerm_management_group" "online" {
  name                       = local.management_group_names.online
  display_name               = "Online"
  parent_management_group_id = azurerm_management_group.landing_zones.id
}
