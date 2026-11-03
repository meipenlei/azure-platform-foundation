provider "azurerm" {
  features {}

  subscription_id = var.subscription_id
  tenant_id       = var.tenant_id

  storage_use_azuread = true
}

data "azurerm_client_config" "current" {}

data "azurerm_subscription" "current" {
  subscription_id = var.subscription_id
}