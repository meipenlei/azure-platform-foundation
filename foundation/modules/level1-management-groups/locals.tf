locals {
  tenant_root_management_group_id = "/providers/Microsoft.Management/managementGroups/${var.tenant_id}"

  management_group_names = {
    root           = var.name_prefix
    platform       = "${var.name_prefix}-platform"
    landing_zones  = "${var.name_prefix}-landing-zones"
    sandboxes      = "${var.name_prefix}-sandboxes"
    decommissioned = "${var.name_prefix}-decommissioned"
    management     = "${var.name_prefix}-management"
    connectivity   = "${var.name_prefix}-connectivity"
    identity       = "${var.name_prefix}-identity"
    corp           = "${var.name_prefix}-corp"
    online         = "${var.name_prefix}-online"
  }
}
