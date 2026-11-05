variable "tenant_id" {
  description = "Microsoft Entra tenant ID."
  type        = string

  validation {
    condition = can(regex(
      "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
      var.tenant_id
    ))

    error_message = "tenant_id must be a valid UUID."
  }
}

variable "subscription_id" {
  description = "Azure subscription used for APF Level 0."
  type        = string

  validation {
    condition = can(regex(
      "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
      var.subscription_id
    ))

    error_message = "subscription_id must be a valid UUID."
  }
}

variable "location" {
  description = "Azure region for Level 0 bootstrap resources."
  type        = string
  default     = "germanywestcentral"
}

variable "name_prefix" {
  description = "Short lowercase prefix used for APF resource naming."
  type        = string

  validation {
    condition = can(regex(
      "^[a-z][a-z0-9-]{1,9}$",
      var.name_prefix
    ))

    error_message = "name_prefix must contain 2-10 lowercase letters, numbers, or hyphens and start with a letter."
  }
}

variable "github_owner" {
  description = "GitHub repository owner or organization name."
  type        = string
}

variable "github_owner_id" {
  description = "Immutable numeric GitHub owner ID used for OIDC subject claims."
  type        = string

  validation {
    condition     = can(regex("^[0-9]+$", var.github_owner_id))
    error_message = "github_owner_id must be numeric."
  }
}

variable "github_repository" {
  description = "GitHub customer implementation repository name."
  type        = string
}

variable "github_repository_id" {
  description = "Immutable numeric GitHub repository ID used for OIDC subject claims."
  type        = string

  validation {
    condition     = can(regex("^[0-9]+$", var.github_repository_id))
    error_message = "github_repository_id must be numeric."
  }
}

variable "github_apply_environment" {
  description = "GitHub Environment used for protected Terraform apply jobs."
  type        = string
  default     = "apf-level0"

  validation {
    condition = can(regex(
      "^[A-Za-z0-9_-]+$",
      var.github_apply_environment
    ))

    error_message = "github_apply_environment may contain letters, numbers, hyphens and underscores."
  }
}

variable "tags" {
  description = "Additional tags applied to Level 0 resources."
  type        = map(string)
  default     = {}
}

variable "github_governance_environment" {
  type    = string
  default = "apf-governance"
}