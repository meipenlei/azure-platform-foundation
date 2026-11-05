resource "azurerm_user_assigned_identity" "plan" {
  name                = local.plan_identity_name
  resource_group_name = azurerm_resource_group.bootstrap.name
  location            = azurerm_resource_group.bootstrap.location

  tags = local.tags
}

resource "azurerm_user_assigned_identity" "apply" {
  name                = local.apply_identity_name
  resource_group_name = azurerm_resource_group.bootstrap.name
  location            = azurerm_resource_group.bootstrap.location

  tags = local.tags
}

resource "azurerm_user_assigned_identity" "governance" {
  name                = "${var.name_prefix}-id-l0-governance"
  location            = azurerm_resource_group.bootstrap.location
  resource_group_name = azurerm_resource_group.bootstrap.name

  tags = local.tags
}