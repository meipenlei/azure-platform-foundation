variable "tenant_id" {
  description = "Microsoft Entra tenant ID. The tenant root management group uses the same ID."
  type        = string
}

variable "bootstrap_subscription_id" {
  description = "Subscription initially placed under the APF Management management group."
  type        = string
}

variable "name_prefix" {
  description = "Stable APF management-group root ID and prefix."
  type        = string
}

variable "root_display_name" {
  description = "Display name of the APF root management group."
  type        = string
}

variable "plan_principal_id" {
  description = "Principal ID of the APF plan managed identity."
  type        = string
}

variable "governance_principal_id" {
  description = "Principal ID of the APF governance managed identity."
  type        = string
}
