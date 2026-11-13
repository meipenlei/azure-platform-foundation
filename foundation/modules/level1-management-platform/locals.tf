locals {
  resource_names = {
    resource_group      = "${var.name_prefix}-rg-l1-management"
    log_analytics       = "${var.name_prefix}-law-l1-platform"
    monitoring_identity = "${var.name_prefix}-id-l1-monitoring"
  }

  tags = merge(
    {
      "apf-level"     = "1"
      "apf-component" = "management-platform"
      "managed-by"    = "terraform"
    },
    var.tags,
  )
}
