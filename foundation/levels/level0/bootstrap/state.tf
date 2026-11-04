resource "azurerm_resource_group" "bootstrap" {
  name     = local.resource_group_name
  location = var.location

  tags = local.tags
}

resource "azurerm_storage_account" "state" {
  name                = local.storage_account_name
  resource_group_name = azurerm_resource_group.bootstrap.name
  location            = azurerm_resource_group.bootstrap.location

  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  min_tls_version            = "TLS1_2"
  https_traffic_only_enabled = true

  allow_nested_items_to_be_public = false

  shared_access_key_enabled       = false
  default_to_oauth_authentication = true
  local_user_enabled              = false

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 14
    }

    container_delete_retention_policy {
      days = 14
    }
  }

  tags = local.tags
}

resource "azurerm_storage_container" "tfstate" {
  name                  = local.state_container_name
  storage_account_id    = azurerm_storage_account.state.id
  container_access_type = "private"
}