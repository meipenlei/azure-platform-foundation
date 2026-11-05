variable "subscription_id" {
  description = "Azure subscription ID containing the APF foundation."
  type        = string
}

variable "governance_principal_id" {
  description = "Principal ID of the APF Level 0 governance managed identity."
  type        = string
}

variable "state_container_id" {
  description = "Azure resource ID of the APF Terraform state container."
  type        = string
}