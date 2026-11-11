output "root_management_group_id" {
  value = azurerm_management_group.root.id
}

output "root_management_group_name" {
  value = azurerm_management_group.root.name
}

output "management_group_ids" {
  value = {
    root           = azurerm_management_group.root.id
    platform       = azurerm_management_group.platform.id
    landing_zones  = azurerm_management_group.landing_zones.id
    sandboxes      = azurerm_management_group.sandboxes.id
    decommissioned = azurerm_management_group.decommissioned.id
    management     = azurerm_management_group.management.id
    connectivity   = azurerm_management_group.connectivity.id
    identity       = azurerm_management_group.identity.id
    corp           = azurerm_management_group.corp.id
    online         = azurerm_management_group.online.id
  }
}

output "bootstrap_subscription_parent_management_group_id" {
  value = azurerm_management_group.management.id
}

output "policy_deployment_root_scope" {
  value = azurerm_management_group.root.id
}
