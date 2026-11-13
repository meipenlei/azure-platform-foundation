variable "name_prefix" {
  description = "Stable APF naming prefix."
  type        = string
}

variable "location" {
  description = "Azure region for Level 1 management resources."
  type        = string
}

variable "log_analytics_retention_days" {
  description = "Default analytics retention for the central Log Analytics workspace."
  type        = number
  default     = 30

  validation {
    condition = (
      var.log_analytics_retention_days >= 30
      && var.log_analytics_retention_days <= 730
    )
    error_message = "log_analytics_retention_days must be between 30 and 730."
  }
}

variable "tags" {
  description = "Additional tags for Level 1 management resources."
  type        = map(string)
  default     = {}
}
